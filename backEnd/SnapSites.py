from GDALData import GDALData, QUERYDATA
import matplotlib.pyplot as plt
from Helpers import *
import math
import sys
import collections
""" 
class SnapSite(object):
    def __init__(self, maxSnapDist):
        #the assumed farthest distance between a site and its coorisponding snapped location
        self.maxSnapDist = maxSnapDist
 """

maxSnapDist = 1000
snapVerificationTolerance = 0.4#if the second nearest snap location is within 20% of the distance of the nearest, raise a warning flag
numSecondarySnapsConsidered = 4# how many possible locations that aren't the same as the nearest do we consider?
adverbNameSeparators = [" at ", " above ", " near "]
waterTypeNames = [" brook", " pond", " river", " lake", " stream", " outlet", " creek", " bk", " ck"]
SnappedSite = collections.namedtuple('SnappedSite', 'site snappedFeature snappedLocation snapDistance distAlongFeature')

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
    return siteName[0:endIndex]

def dot (x1, y1, x2, y2):
    return x1*x2 + y1*y2

#this is trash. Just need a way to get the segment and distance on said segment from an arbitary point
def snapPointToSegment (point, gdalData):

    nearestPointDist = sys.float_info.max
    nearestPointIndex = -1
    nearestPointDistAlongSegment = 0
    nearestPointSegmentID = 0

    objectIDIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")
    gdalData.lineLayer.ResetReading()
    for line in gdalData.lineLayer:
        lineGeom = line.GetGeometryRef()
        numPoints = lineGeom.GetPointCount()
        segmentID = line.GetFieldAsString(objectIDIndex)

        distAlongSegment = 0

        for i in range(0, numPoints):
            prevLinePoint = lineGeom.GetPoint(max(0, i-1))
            linePoint = lineGeom.GetPoint(i)

            geomSegmentLen = dist(linePoint[0], linePoint[1], prevLinePoint[0], prevLinePoint[1])
            #get length of each polyline of the stream segment. Divide by 1000 to get in km
            distAlongSegment += geomSegmentLen / 1000 

            distance = dist(linePoint[0], linePoint[1], point[0], point[1])
            if distance < nearestPointDist:
                nearestPointDist = distance
                nearestPointIndex = i
                nearestPointDistAlongSegment = distAlongSegment
                nearestPointSegmentID = segmentID

    if nearestPointIndex == -1:
        print ("Could not snap lat/lng to a stream")
        return None
    else:
        return (nearestPointSegmentID, nearestPointDistAlongSegment)

def Snap(gdalData):
    stationNameIndex = gdalData.siteLayer.GetLayerDefn().GetFieldIndex("station_nm")
    lineNameIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("GNIS_NAME")
    siteLayer = gdalData.siteLayer
    lineLayer = gdalData.lineLayer
    siteLayer.ResetReading()
    sideInd = 0
    
    snappedSites = []
    for site in siteLayer:
        lineLayer.ResetReading()

        siteGeom = site.GetGeometryRef()
        buffer = siteGeom.Buffer(maxSnapDist)
        #lineLayer.SetSpatialFilter(buffer)
        potentialLines = []
        for line in lineLayer:
            potentialLines.append(line)
        
        sitePoint = siteGeom.GetPoint(0)
        stationName = site.GetFieldAsString(stationNameIndex)
        #an identifier that could likely appear in both the station name and the 
        #name of the correct stream it should be snapped to
        stationIdentifier = getSiteStreamNameIdentifier(stationName) 
        
        #for all segments, store the point on each segment nearest to the site's location
        possibleSnaps = [] #(point index, point distance, streamSegment index)

        #get nearest point in the stream segment
        for j in range(0, len(potentialLines)):#potential in potentialLines:
            lineGeom = potentialLines[j].GetGeometryRef()
            numPoints = lineGeom.GetPointCount()

            nearestPointDist = sys.float_info.max
            nearestPointIndex = -1
            nearestPointDistAlongSegment = 0

            distAlongSegment = 0

            for i in range(0, numPoints):
                prevPoint = lineGeom.GetPoint(max(0, i-1))
                point = lineGeom.GetPoint(i)

                geomSegmentLen = dist(point[0], point[1], prevPoint[0], prevPoint[1])
                #get length of each polyline of the stream segment. Divide by 1000 to get in km
                distAlongSegment += geomSegmentLen / 1000 

                distance = dist(point[0], point[1], sitePoint[0], sitePoint[1])
                if distance < nearestPointDist:
                    nearestPointDist = distance
                    nearestPointIndex = i
                    nearestPointDistAlongSegment = distAlongSegment
            
            nearestPoint = lineGeom.GetPoint(nearestPointIndex)

            snap = SnappedSite(site=site, snappedFeature = potentialLines[j], snappedLocation = nearestPoint, snapDistance = nearestPointDist, distAlongFeature = nearestPointDistAlongSegment)
            possibleSnaps.append(snap)



        sortedPossibleSnaps = sorted(possibleSnaps, key=lambda snap: snap.snapDistance)

        nearestDistance = sortedPossibleSnaps[0].snapDistance
        maxConsideredDistance = nearestDistance * 2 #arbitrary cutoff. logical that the correct snap couldn't be twice as far as the nearest snap..
        
        chosenSnapIndex = 0

        for i, possibleSnap in enumerate(sortedPossibleSnaps):
            snapDistance = possibleSnap.snapDistance
            if snapDistance < maxConsideredDistance:
                snappedFeature = possibleSnap.snappedFeature
                streamName = snappedFeature.GetFieldAsString(lineNameIndex)

                # if the next stream snap option includes the identifier in its name or there is no identifier, snap here
                if stationIdentifier in streamName or stationIdentifier == "":
                    chosenSnapIndex = i
                    break
            else:
                #end if the option we're considering is  more than twice as far away as the closest 
                break

        if chosenSnapIndex != 0:
            print("snapped to non-closest")
        snappedSites.append(sortedPossibleSnaps[chosenSnapIndex])

        lineLayer.SetSpatialFilter(None)
    return snappedSites


#Visualizes 
def visualize (gdalData, snapped):
    siteLayer = gdalData.siteLayer
    lineLayer = gdalData.lineLayer
    
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



""" x = -74.3254918    #Long Lake
y =  44.0765791
#x = -76.3612354  #04249020
#y = 43.4810611
a = [x,y]
gdalData = GDALData(y, x, loadMethod=QUERYDATA)
#gdalData.loadFromQuery(y, x+0.3, attempts)
#gdalData.loadFromData()
snapped = Snap(gdalData)
visualize(gdalData, snapped)
gdalData.siteLayer.ResetReading() """
#stationName_index = gdalData.siteLayer.GetLayerDefn().GetFieldIndex("station_nm")

""" for site in gdalData.siteLayer:
    stationName = site.GetFieldAsString(stationName_index)
    print(stationName + " ------- " + getSiteStreamName(stationName)) """