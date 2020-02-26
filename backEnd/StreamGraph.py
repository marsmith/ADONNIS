from collections import namedtuple
from GDALData import *
import matplotlib.pyplot as plt
import random

#constants for neighbor relationships
UNKNOWN = -1
UPSTREAM = 0
UPSTREAMTRIB = 1
DOWNSTREAM = 2


#tuples used
NeighborRelationship = namedtuple('NeighborRelationship', 'neighbor relationship')
#a stream node 
class StreamNode (object):
    def __init__(self, position):
        #streamNodes get 1 appended on the FID to ensure uniqueness
        self.neighbors = []
        self.position = position

    def addNeighbor (self, segment, relationship = UNKNOWN):
        self.neighbors.append(NeighborRelationship(neighbor=segment, relationship=relationship))


#a segment connecting two points
class StreamSegment (object):
    def __init__(self, upStreamNode, downStreamNode, ID, length):
        #streamSegments get 0 appended on the FID to ensure uniqueness
        self.upStreamNode = upStreamNode
        self.downStreamNode = downStreamNode
        self.gages = []

class StreamGraph (object):

    def __init__(self):
        self.segments = {}
        self.nodes = []

        self.removedSegments = frozenset()#cleaned segments. keep track to prevent duplicates
    
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
            if len(streamNode.neighbors) != 2:
                continue
            x.append(streamNode.position[0])
            y.append(streamNode.position[1])
        plt.scatter(x,y, color='red')

        plt.show()


    #calculate what branches are tributaries, etc 
    def calculateStreamStructure (self):
        pass

    def removeSegment (self, segmentID):
        if segmentID in self.segments:
            del self.segments[segmentID]


    #remove loops, and collapse nodes with only two neighbors
    def cleanGraph (self):
        for node in self.nodes:
            if len(node.neighbors) == 2:


    #Adds the geometry stored in the gdalData object
    #gdalData: ref to a gdalData object
    #guaranteedNetLineIndex a streamline feature that is definitely on the network we are interested in
    def addGeom(self, gdalData):
        lineLayer = gdalData.lineLayer
        lineLayer.ResetReading()

        objectIDIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")
        lengthIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("LENGTHKM")

        for line in lineLayer:
            #don't add duplicates
            objectID = line.GetFieldAsString(objectIDIndex)
            length = line.GetFieldAsString(lengthIndex)
            if objectID in self.segments:
                continue

            geom = line.GetGeometryRef()

            upStreamPt = geom.GetPoint(0)
            numPoints = geom.GetPointCount()
            downStreamPt = geom.GetPoint(numPoints-1)

            upStreamNode = None
            downStreamNode = None

            #see if existing nodes exist that connect to this segment
            for node in self.nodes:
                if self.pointsEqual (upStreamPt, node.position):
                    upStreamNode = node
                elif self.pointsEqual (downStreamPt, node.position):
                    downStreamNode = node
            
            if upStreamNode == None:
                upStreamNode = StreamNode(upStreamPt)
                self.nodes.append(upStreamNode)
            if downStreamNode == None:
                downStreamNode = StreamNode(downStreamPt)
                self.nodes.append(downStreamNode)

            newSegment = StreamSegment(upStreamNode, downStreamNode, objectID, length)

            self.segments[objectID] = newSegment
            upStreamNode.addNeighbor(newSegment)
            downStreamNode.addNeighbor(newSegment)



