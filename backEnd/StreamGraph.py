from collections import namedtuple
from GDALData import GDALData, RESTRICTED_CODES
import matplotlib.pyplot as plt
import random

#constants for neighbor relationships
UNKNOWN = 0
UPSTREAM = 1
UPSTREAMTRIB = 2
DOWNSTREAM = 3


#tuples used
NeighborRelationship = namedtuple('NeighborRelationship', 'segment relationship')
#a stream node 
class StreamNode (object):
    def __init__(self, position):
        #streamNodes get 1 appended on the FID to ensure uniqueness
        self.neighbors = []
        self.position = position

    def addNeighbor (self, segment, relationship = UNKNOWN):
        self.neighbors.append(NeighborRelationship(segment=segment, relationship=relationship))

    def getCodedNeighbors (self, neighborCode):
        results = []
        for neighbor in self.neighbors:
            if neighbor.relationship == neighborCode:
                results.append(neighbor.segment)
        return results
    
    #removes the neighbor with neighborID if it exists. Return true if removed successfully
    def removeNeighbor (self, segmentID):
        for i, neighbor in enumerate(self.neighbors):
            if neighbor.segment.segmentID == segmentID:
                self.neighbors.pop(i)
                return True
        return False

    def numNeighbors(self):
        return len(self.neighbors)

#a segment connecting two points
class StreamSegment (object):
    def __init__(self, upStreamNode, downStreamNode, ID, length):
        #streamSegments get 0 appended on the FID to ensure uniqueness
        self.upStreamNode = upStreamNode
        self.downStreamNode = downStreamNode
        self.segmentID = ID
        self.gages = []
        self.length = length

class StreamGraph (object):

    def __init__(self):
        self.segments = {}
        self.nodes = []

        self.removedSegments = set()#cleaned segments. keep track to prevent duplicates
    
    #check if two points are relatively equal. [FUTURE] This shouldn't be in this class
    def pointsEqual (self, p1, p2):
        treshold = 1
        if abs(p1[0]-p2[0]) + abs(p1[1] - p2[1]) < treshold:
            return True
        else:
            return False

    #visualize the graph using matplotlib
    def visualize(self):
        for streamSeg in self.segments.values():
            startPt = streamSeg.downStreamNode.position
            endPt = streamSeg.upStreamNode.position

            x = [startPt[0], endPt[0]]
            y = [startPt[1], endPt[1]]
            plt.plot(x, y, linewidth=1, color='blue')
        
        x = []
        y = []
        for streamNode in self.nodes:
            x.append(streamNode.position[0])
            y.append(streamNode.position[1])
        plt.scatter(x,y, color='green')

        x = []
        y = []
        for streamNode in self.nodes:
            if streamNode.numNeighbors() != 2:
                continue
            x.append(streamNode.position[0])
            y.append(streamNode.position[1])
        plt.scatter(x,y, color='red')

        plt.show()


    #calculate what branches are tributaries, etc 
    def calculateStreamStructure (self):
        pass

    #safely remove a segment from the graph
    def removeSegment (self, segmentID):
        if segmentID in self.segments:
            del self.segments[segmentID]
            self.removedSegments.add(segmentID)
    
    #add a segment to the graph
    def addSegment (self, upstreamNode, downstreamNode, segmentID, length):
        newSegment = StreamSegment(upstreamNode, downstreamNode, segmentID, length)    
        #add the new segment to the dictionary
        self.segments[segmentID] = newSegment
        #from the perspective of the upstream node, this segment is downstream and vice versa
        upstreamNode.addNeighbor(newSegment, DOWNSTREAM)
        downstreamNode.addNeighbor(newSegment, UPSTREAM)

    #has this graph ever contained this segment?
    #used when adding new segments
    def hasContainedSegment (self, segmentID):
        if segmentID in self.segments or segmentID in self.removedSegments:
            return True
        else:
            return False


    #remove loops, and collapse nodes with only two neighbors
    def cleanGraph (self):
        queue = []

        # ---------------- add something here that checks to see if nodes are near 
        # the edge of the collected data. These nodes cannot be cleaned reliably! 
        for node in self.nodes:
            hasUpstream = len(node.getCodedNeighbors(UPSTREAM)) > 0
            hasDownstream = len(node.getCodedNeighbors(DOWNSTREAM)) > 0
            if node.numNeighbors() == 2 and hasUpstream and hasDownstream:
                queue.append(node)  
        
        while len(queue) > 0:
            node = queue.pop()
            #getCodedNeighbors returns an array since you can have multiple tributaries
            #but in this case, there are only two, so it must only be a single upstream and downstream
            upstreamSegment = node.getCodedNeighbors(UPSTREAM)[0]
            downstreamSegment = node.getCodedNeighbors(DOWNSTREAM)[0]

            newSegmentUpstreamNode = upstreamSegment.upStreamNode
            newSegmentDownstreamNode = downstreamSegment.downStreamNode                

            #remove the neighbor reference from the outer two nodes neighboring the two segments we remove
            newSegmentUpstreamNode.removeNeighbor(upstreamSegment.segmentID)
            newSegmentDownstreamNode.removeNeighbor(downstreamSegment.segmentID)
            #remove the segment and nodes from the actual graph
            for neighbor in node.neighbors:
                self.removeSegment(neighbor.segment.segmentID)
            self.nodes.remove(node)

            #calculate new segment properties
            newLength = upstreamSegment.length + downstreamSegment.length
            # concat IDs to get a new unique ID
            newID = upstreamSegment.segmentID + downstreamSegment.segmentID

            self.addSegment(newSegmentUpstreamNode, newSegmentDownstreamNode, newID, newLength)


    #Adds the geometry stored in the gdalData object
    #gdalData: ref to a gdalData object
    #guaranteedNetLineIndex a streamline feature that is definitely on the network we are interested in
    def addGeom(self, gdalData):
        lineLayer = gdalData.lineLayer
        lineLayer.ResetReading()

        objectIDIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")
        lengthIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("LENGTHKM")
        fCodeIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("FCode")

        for line in lineLayer:
            #don't add duplicates
            segmentID = line.GetFieldAsString(objectIDIndex)
            length = line.GetFieldAsString(lengthIndex)
            fCode = line.GetFieldAsString(fCodeIndex)
            if self.hasContainedSegment(segmentID) or fCode in RESTRICTED_CODES:
                continue

            geom = line.GetGeometryRef()

            upstreamPt = geom.GetPoint(0)
            numPoints = geom.GetPointCount()
            downstreamPt = geom.GetPoint(numPoints-1)

            upstreamNode = None
            downstreamNode = None

            #see if existing nodes exist that connect to this segment
            for node in self.nodes:
                if self.pointsEqual (upstreamPt, node.position):
                    upstreamNode = node
                elif self.pointsEqual (downstreamPt, node.position):
                    downstreamNode = node
            
            #create new nodes if non were found
            if upstreamNode == None:
                upstreamNode = StreamNode(upstreamPt)
                self.nodes.append(upstreamNode)
            if downstreamNode == None:
                downstreamNode = StreamNode(downstreamPt)
                self.nodes.append(downstreamNode)

            self.addSegment(upstreamNode, downstreamNode, segmentID, length)
        
        self.cleanGraph()



