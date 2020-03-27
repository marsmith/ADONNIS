import GDALData
import matplotlib.pyplot as plt
from Helpers import *
import math
import sys
import collections
from StreamGraphNavigator import StreamGraphNavigator
import copy
import itertools
""" 
class SnapSite(object):
    def __init__(self, maxSnapDist):
        #the assumed farthest distance between a site and its coorisponding snapped location
        self.maxSnapDist = maxSnapDist
 """

NUM_SNAPS = 4# how many possible locations that aren't the same as the nearest do we consider?
PERCENT_DIST_CUTOFF = 4 #if a potential snap is 
adverbNameSeparators = [" at ", " above ", " near "]
waterTypeNames = [" brook", " pond", " river", " lake", " stream", " outlet", " creek", " bk", " ck"]
#a possible snap for a given point
Snap = collections.namedtuple('Snap', 'feature snapDistance distAlongFeature')
# a point that can be snapped. Name and ID are used occasionally to aid in snapping
SnapablePoint = collections.namedtuple('SnapablePoint', 'point name id')


#Gets a key string from the site name that could be used to help snap sites later 
def getSiteStreamNameIdentifier (siteName):
    lowerCase = siteName.lower()
    endIndex = len(siteName)-1
    for adverb in adverbNameSeparators:
        try:
            endIndex = lowerCase.index(adverb)  
            break  
        except:       
            pass
    split = lowerCase[0:endIndex]
    
    for waterBody in waterTypeNames:
        try:
            endIndex = split.index(waterBody)
        except:
            pass

    if endIndex == len(siteName)-1:
        return ""
    return lowerCase[0:endIndex]

def dot (x1, y1, x2, y2):
    return x1*x2 + y1*y2

def snapPoint(snapablePoint, baseData):
    lineNameIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("GNIS_NAME")
    lengthIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("LENGTHKM")
    objectIDIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")

    lineLayer = baseData.lineLayer
    lineLayer.ResetReading()

    sitePoint = snapablePoint.point
    siteName = snapablePoint.name
    siteId = snapablePoint.id
    
    #for all segments, store the point on each segment nearest to the site's location
    possibleSnaps = [] #(point index, point distance, streamSegment index)

    #get nearest point in the stream segment
    for line in lineLayer:
        lineGeom = line.GetGeometryRef()
        numPoints = lineGeom.GetPointCount()
        lineLength = float(line.GetFieldAsString(lengthIndex))
        objectID = line.GetFieldAsString(objectIDIndex)

        nearestPointDist = sys.float_info.max
        nearestPointIndex = -1
        nearestPointDistAlongSegment = 0

        distAlongSegment = 0
        for i in range(0, numPoints):
            point = lineGeom.GetPoint(i)
            #we make assumption that each point in the geo is equally spaced
            geomSegmentLen = lineLength / numPoints
            #get length of each polyline of the stream segment. Divide by 1000 to get in km
            distAlongSegment += geomSegmentLen 

            distance = dist(point[0], point[1], sitePoint[0], sitePoint[1])
            if distance < nearestPointDist:
                nearestPointDist = distance
                nearestPointIndex = i
                nearestPointDistAlongSegment = distAlongSegment
        
        nearestPoint = lineGeom.GetPoint(nearestPointIndex)
        snap = Snap(feature = line, snapDistance = nearestPointDist, distAlongFeature = nearestPointDistAlongSegment)
        possibleSnaps.append(snap)

    if len(possibleSnaps) == 0:
        return None

    sortedPossibleSnaps = sorted(possibleSnaps, key=lambda snap: snap.snapDistance)
    #limit the number of considered snaps to a fixed number
    consideredSnaps = sortedPossibleSnaps[:min(NUM_SNAPS, len(sortedPossibleSnaps))]

    closestSnap = consideredSnaps[0].snapDistance
    cutoff = closestSnap * PERCENT_DIST_CUTOFF

    #remove very unlikely snaps
    for snap in reversed(consideredSnaps):
        if snap.snapDistance > cutoff:
            consideredSnaps.remove(snap)

    stationIdentifier = getSiteStreamNameIdentifier(siteName)
    if len(stationIdentifier) > 0:
        #find name match. If name match is found, then we can be sure of this snap
        for snap in consideredSnaps:
            lineName = snap.feature.GetFieldAsString(lineNameIndex).lower()
            if stationIdentifier in lineName:
                consideredSnaps = [snap]
                break

    return consideredSnaps

def getSiteSnapAssignment(graph):
    #a copy of the current graph used to try different possible snap operations
    testingGraph = copy.deepcopy(graph)
    testingGraphNavigator = StreamGraphNavigator(testingGraph)

    allSnaps = []

    for siteID in graph.siteSnaps:
        snaps = graph.siteSnaps[siteID]
        allSnaps.append(snaps)

    combinations = list(itertools.product(*allSnaps))

    bestCombinations = []
    bestError = sys.maxsize

    #get the list of combinations that has the lowest error in siteID ordering
    #there could be multiple snaps that have this property
    for combination in combinations:
        testingGraph.refreshSiteSnaps(combination)
        error = testingGraphNavigator.getGraphSiteIDError()

        if error < bestError:
            bestError = error
            bestCombinations = [combination]
        elif error == bestError:
            #if this is as good as the previous best, add it as a possibility
            bestCombinations.append(combination)

    if len(bestCombinations) == 0:
        print ("No combination of snaps found")
        return None

    smallestSumDist = sys.maxsize
    smallestSumDistCombination = None
    #further find a snap based on cumulative dist to snapped position
    for combination in bestCombinations:
        sumDist = 0
        for snap in combination:
            sumDist += snap.snapDist
        if sumDist < smallestSumDist:
            smallestSumDist = sumDist
            smallestSumDistCombination = combination

    return smallestSumDistCombination

#Visualizes 
def visualize (baseData, snapped):
    siteLayer = baseData.siteLayer
    lineLayer = baseData.lineLayer
    
    """ siteLayer.ResetReading()
    feat = siteLayer.GetNextFeature()
    testBuff = feat.GetGeometryRef().Buffer(3000)
    lineLayer.SetSpatialFilter(testBuff) """

    lx = []
    ly = []

    lineLayer.ResetReading()
    for line in lineLayer:
        
        geom = line.GetGeometryRef()
        numPoints = geom.GetPointCount()
        x = []
        y = []
        for i in range(0, numPoints):
            p = geom.GetPoint(i)
            x.append(p[0])
            y.append(p[1])

        p1 = geom.GetPoint(0)
        lx.append(p1[0])
        ly.append(p1[1]+10)

        plt.plot(x, y, linewidth=1, color='blue')

    #display line endpoints
    plt.scatter(lx,ly, color='black')

    siteLayer.ResetReading()
    x = []
    y = []
    for site in siteLayer:
        geom = site.GetGeometryRef()
        x.append(geom.GetPoint(0)[0])
        y.append(geom.GetPoint(0)[1])
    plt.scatter(x,y, color='red')

    x = []
    y = []
    for snap in snapped:
        site = snap[0]
        snapLoc = snap[1]
        x.append(snapLoc[0])
        y.append(snapLoc[1])
    plt.scatter(x,y, color='green')

    plt.show()


