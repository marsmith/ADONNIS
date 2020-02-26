from collections import namedtuple
from GDALData import *

#constants for neighbor relationships
UNKNOWN = -1
UPSTREAM = 0
UPSTREAMTRIB = 1
DOWNSTREAM = 2


#tuples used
NeighborRelationship = namedtuple('NeighborRelationship', 'neighbor relationship')
Point = namedtuple('Point', 'x y')

#a stream node 
class StreamNode (Object):
    def __init__(self, position):
        #streamNodes get 1 appended on the FID to ensure uniqueness
        self.neighbors = []
        self.position = position

    def addNeighbor (self, segment):
        self.neighbors.append(NeighborRelationship(neighbor=segment, relationship=UNKNOWN))

#a segment connecting two points
class StreamSegment (Object):
    def __init__(self, FID, geometry, name):
        #streamSegments get 0 appended on the FID to ensure uniqueness
        self.FID = int("0"+str(FID))
        self.geometry = geometry
        self.name = name
        self.upStreamNode = None
        self.downStreamNode = None

class StreamGraph (Object):

    def __init__(self):
        segments = []
        nodes = []
    

    #Adds the geometry stored in the gdalData object
    #gdalData: ref to a gdalData object
    #guaranteedNetLineIndex a streamline feature that is definitely on the network we are interested in
    def addGeom(self, gdalData):
        lineLayer = gdalData.lineLayer
        lineLayer.ResetReading()

        for line in lineLayer:
            geom = line.GetGeometryRef()

            upStreamPt = geom.GetPoint(0)
            numPoints = geom.GetPointCount()
            downStreamPt = geom.GetPoint(numPoints-1)

            for segment in self.segments:
            


