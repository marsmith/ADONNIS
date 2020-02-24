from GDALData import *
import matplotlib.pyplot as plt
import math
import sys
""" 
class SnapSite(object):
    def __init__(self, maxSnapDist):
        #the assumed farthest distance between a site and its coorisponding snapped location
        self.maxSnapDist = maxSnapDist
 """

maxSnapDist = 1000
snapVerificationTolerance = 0.2#if the second nearest snap location is within 20% of the distance of the nearest, raise a warning flag
numSecondarySnapsConsidered = 4# how many possible locations that aren't the same as the nearest do we consider?
adverbNameSeparators = [" at ", " above ", " near "]
waterTypeNames = [" brook", " pond", " river", " lake", " stream", " outlet", " creek", " bk", " ck"]

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

def Snap(gdalData):
    print("snap")
    siteLayer = gdalData.siteLayer
    lineLayer = gdalData.lineLayer
    siteLayer.ResetReading()
    sideInd = 0
    for site in siteLayer:
        lineLayer.ResetReading()

        siteGeom = site.GetGeometryRef()
        buffer = siteGeom.Buffer(maxSnapDist)
        lineLayer.SetSpatialFilter(buffer)
        potentialLines = []
        for line in lineLayer:
            potentialLines.append(line)
        
        sitePoint = siteGeom.GetPoint(0)

        #for all segments, store the point on each segment nearest to the site's location
        nearestPointsOnSegments = [] #(point index, point distance, streamSegment index)

        #get nearest point in the stream segment
        for j in range(0, len(potentialLines)):#potential in potentialLines:
            lineGeom = potentialLines[j].GetGeometryRef()
            numPoints = lineGeom.GetPointCount()

            nearestPointDist = sys.float_info.max
            nearestPointIndex = -1

            for i in range(0, numPoints):
                point = lineGeom.GetPoint(i)
                dist = math.sqrt((point[0] - sitePoint[0])**2 + (point[1] - sitePoint[1])**2)
                if dist < nearestPointDist:
                    nearestPointDist = dist
                    nearestPointIndex = i

            nearestPointsOnSegments.append((nearestPointIndex, nearestPointDist, j))

        nearestPossibleSnaps = sorted(nearestPointsOnSegments, key=lambda point: point[1])

        needsUserConfirmation = False

        nearestDistance = nearestPossibleSnaps[0][1]
        verificationDistance = nearestDistance + snapVerificationTolerance * nearestDistance
        
        print(nearestPointsOnSegments[0:3])

        lineLayer.SetSpatialFilter(None)
        siteInd = 0

def visualize (gdalData):
    siteLayer = gdalData.siteLayer
    lineLayer = gdalData.lineLayer
    
    """ siteLayer.ResetReading()
    feat = siteLayer.GetNextFeature()
    testBuff = feat.GetGeometryRef().Buffer(3000)
    lineLayer.SetSpatialFilter(testBuff)
 """

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

        plt.plot(x, y, linewidth=1, color='blue')

    siteLayer.ResetReading()
    x = []
    y = []
    for site in siteLayer:
        geom = site.GetGeometryRef()
        x.append(geom.GetPoint(0)[0])
        y.append(geom.GetPoint(0)[1])
    plt.scatter(x,y, color='red')


    plt.show()



x = -74.3254918    #Long Lake
y =  44.0765791
a = [x,y]
gdalData = GDALData()
attempts = 3
gdalData.loadFromQuery(y, x, attempts)
#gdalData.loadFromData()
Snap(gdalData)
#visualize(gdalData)
gdalData.siteLayer.ResetReading()
#stationName_index = gdalData.siteLayer.GetLayerDefn().GetFieldIndex("station_nm")

""" for site in gdalData.siteLayer:
    stationName = site.GetFieldAsString(stationName_index)
    print(stationName + " ------- " + getSiteStreamName(stationName)) """