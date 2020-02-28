from collections import namedtuple
from GDALData import GDALData, RESTRICTED_FCODES
from Helpers import *
import ogr
import matplotlib.pyplot as plt
import random

#constants for neighbor relationships
UNKNOWN = 0         #000
UPSTREAM = 1        #001 a one in the one's place means upstream
UPSTREAMTRIB = 3    #011 contains a one in the one's place, but also contains a 1 in the two's place, indicating upstream and a trib
DOWNSTREAM = 4      #100 contains a one in the four's place indicating a downstream site 




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
            #does the relationship contain this flag
            if neighbor.relationship & neighborCode == neighborCode:
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
        self.safeDataBoundaryKM = None #gdal geometry object. Points inside should have all neighboring segments stored

        self.removedSegments = set()#cleaned segments. keep track to prevent duplicates
    
    #visualize the graph using matplotlib
    def visualize(self):
        for streamSeg in self.segments.values():
            startPt = streamSeg.upStreamNode.position
            endPt = streamSeg.downStreamNode.position

            x = [startPt[0], endPt[0]]
            y = [startPt[1], endPt[1]]
            dx = endPt[0] - startPt[0]
            dy = endPt[1] - startPt[1]
            plt.arrow(startPt[0], startPt[1], dx, dy, width=1, head_width = 20, color='blue', length_includes_head=True)

            plt.plot(x,y, lineWidth=1, color='blue')

            midPoint = (startPt[0]/2 + endPt[0]/2, startPt[1]/2 + endPt[1]/2)

            plt.text(midPoint[0], midPoint[1], streamSeg.segmentID, fontsize = 8)
        
        x = []
        y = []
        for streamNode in self.nodes:
            x.append(streamNode.position[0])
            y.append(streamNode.position[1])
        plt.scatter(x,y, color='green')

        #display safe boundary polygon
        geom = self.safeDataBoundaryKM
        for ring in geom:
            numPoints = ring.GetPointCount()
            x = []
            y = []
            for i in range(0, numPoints):
                point = ring.GetPoint(i)
                x.append(point[0])
                y.append(point[1])
            plt.plot(x,y, lineWidth=1, color='red')

        """ x = []
        y = []
        for streamNode in self.nodes:
            if streamNode.numNeighbors() != 2:
                continue
            x.append(streamNode.position[0])
            y.append(streamNode.position[1])
        plt.scatter(x,y, color='red') """

        plt.show()


    #calculate what branches are tributaries, etc 
    def calculateStreamStructure (self):
        pass

    def findMainStreamPath (self, junctionNode):
        #which are the possible upstream branches
        possibleBranches = []
        for neighbor in junctionNode.neighbors:
            if neighbor.relationship == UPSTREAM:
                possibleBranches.append(neighbor.segment)
        #use the following attributes as priority for determining main path: stream name, upstream length

        #need to find downstream branch. this may be difficult with loops

    #safely remove a segment from the graph
    def removeSegment (self, segment):
        segmentID = segment.segmentID
        if segmentID in self.segments:
            #for neighbor in segment
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
    #used when adding new segments to prevent duplicates
    def hasContainedSegment (self, segmentID):
        if segmentID in self.segments or segmentID in self.removedSegments:
            return True
        else:
            return False

    #Get a list of nodes that have no downstream connection. A lot of these nodes will be outside of the safe zone, but they can be used to traverse 
    #the entire graph since every node must be upstream from a sink
    def getSinks (self):
        sinks = []
        for node in self.nodes:
            if len(node.getCodedNeighbors(DOWNSTREAM)) == 0:
                sinks.append(node)
        return sinks
    
    def pointWithinSafeDataBoundary (self, point):
        pointGeo = ogr.Geometry(ogr.wkbPoint)
        pointGeo.AddPoint(point[0], point[1])
        return pointGeo.Within(self.safeDataBoundaryKM)

    #remove loops, and collapse nodes with only two neighbors
    def cleanGraph (self):

        #close all loops upstream of 'sinkNode'
        def closeLoops (sinkNode):
            frontier = [sinkNode]
            discovered = [sinkNode]
            while len(frontier) > 0:
                nextNode = frontier.pop(0)
                for neighbor in nextNode.neighbors:
                    #this neighbor has an upstream relationship
                    if neighbor.relationship & UPSTREAM == UPSTREAM:
                        upstreamNode = neighbor.segment.upStreamNode
                        if upstreamNode not in discovered:
                            frontier.append(upstreamNode)
                            discovered.append(upstreamNode)
                        else:
                            self.removeSegment(neighbor.segment)

        sinks = self.getSinks()
        #remove loops
        for sink in sinks:
            closeLoops(sink)

        queue = []
        for node in self.nodes:
            hasUpstream = len(node.getCodedNeighbors(UPSTREAM)) > 0
            hasDownstream = len(node.getCodedNeighbors(DOWNSTREAM)) > 0
            #ensure that the node only hs two neighbors, one upstream, one downstream,
            if node.numNeighbors() == 2 and hasUpstream and hasDownstream and self.pointWithinSafeDataBoundary(node.position):
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
                self.removeSegment(neighbor.segment)
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
            length = float(line.GetFieldAsString(lengthIndex))
            fCode = int(line.GetFieldAsString(fCodeIndex))
            if self.hasContainedSegment(segmentID) or fCode in RESTRICTED_FCODES:
                continue

            geom = line.GetGeometryRef()

            upstreamPt = geom.GetPoint(0)
            numPoints = geom.GetPointCount()
            downstreamPt = geom.GetPoint(numPoints-1)

            upstreamNode = None
            downstreamNode = None

            #see if existing nodes exist that connect to this segment
            for node in self.nodes:
                if pointsEqual (upstreamPt, node.position):
                    upstreamNode = node
                elif pointsEqual (downstreamPt, node.position):
                    downstreamNode = node
            
            #create new nodes if non were found
            if upstreamNode == None:
                upstreamNode = StreamNode(upstreamPt)
                self.nodes.append(upstreamNode)
            if downstreamNode == None:
                downstreamNode = StreamNode(downstreamPt)
                self.nodes.append(downstreamNode)

            self.addSegment(upstreamNode, downstreamNode, segmentID, length)
        
        if self.safeDataBoundaryKM == None:
            self.safeDataBoundaryKM = gdalData.safeDataBoundaryKM
        else:
            self.safeDataBoundaryKM = self.safeDataBoundaryKM.Union(gdalData.safeDataBoundaryKM)

        self.cleanGraph()



