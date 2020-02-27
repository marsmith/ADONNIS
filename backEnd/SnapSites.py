from GDALData import GDALData, QUERYDATA
import matplotlib.pyplot as plt
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

def dist (x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
def dot (x1, y1, x2, y2):
    return x1*x2 + y1*y2

def Snap(gdalData):
    print("snap")
    stationNameIndex = gdalData.siteLayer.GetLayerDefn().GetFieldIndex("station_nm")
    lineNameIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("GNIS_NAME")
    siteLayer = gdalData.siteLayer
    lineLayer = gdalData.lineLayer
    siteLayer.ResetReading()
    sideInd = 0
    snappedSite = collections.namedtuple('snappedSite', 'site snappedLocation')
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
        nearestPointsOnSegments = [] #(point index, point distance, streamSegment index)

        #get nearest point in the stream segment
        for j in range(0, len(potentialLines)):#potential in potentialLines:
            lineGeom = potentialLines[j].GetGeometryRef()
            numPoints = lineGeom.GetPointCount()

            nearestPointDist = sys.float_info.max
            nearestPointIndex = -1

            for i in range(0, numPoints):
                point = lineGeom.GetPoint(i)
                distance = dist(point[0], point[1], sitePoint[0], sitePoint[1])
                if distance < nearestPointDist:
                    nearestPointDist = distance
                    nearestPointIndex = i
            
            nearestPoint = lineGeom.GetPoint(nearestPointIndex)
            #refine the snap to a midpoint along a segment
            """ adjacentPointIndRight = min(i+1, numPoints-1)
            adjacentPointIndLeft = max(i-1, 0)

            adjacentPointRight = lineGeom.GetPoint(adjacentPointIndRight)
            adjacentPointLeft = lineGeom.GetPoint(adjacentPointIndLeft)

            rightDist = dist(adjacentPointRight[0], adjacentPointRight[1], sitePoint[0], sitePoint[1])
            leftDist = dist(adjacentPointLeft[0], adjacentPointLeft[1], sitePoint[0], sitePoint[1])

            secondaryPoint = None
            if rightDist < leftDist:
                secondaryPoint = adjacentPointRight
            else:
                secondaryPoint = adjacentPointLeft

            segmentVec = (secondaryPoint[0] - nearestPoint[0], secondaryPoint[1], nearestPoint[1])
            segmentVecLen = dist(0, 0, segmentVec[0], segmentVec[1])

            toSitePointVec = (sitePoint[0] - nearestPoint[0], sitePoint[1] - nearestPoint[1])

            toSiteAlongSeg = dot(segmentVec[0], segmentVec[1], toSitePointVec[0], toSitePointVec[1]) / segmentVecLen
            toSiteAlongSegRatio = toSiteAlongSeg / segmentVecLen

            if toSiteAlongSegRatio > 0.2:
                print("test = " + str(toSiteAlongSegRatio)) """

            nearestPointsOnSegments.append((nearestPointIndex, nearestPointDist, j, nearestPoint))

        sortedPossibleSnaps = sorted(nearestPointsOnSegments, key=lambda point: point[1])

        needsUserConfirmation = False

        nearestDistance = sortedPossibleSnaps[0][1]
        consideredDistance = nearestDistance * 2 #arbitrary cutoff. logical that the correct snap couldn't be twice as far as the nearest snap..
        
        chosenSnapIndex = 0

        for i, possibleSnap in enumerate(sortedPossibleSnaps):
            if possibleSnap[1] < consideredDistance:
                snapStreamInd = possibleSnap[2]
                streamName = potentialLines[snapStreamInd].GetFieldAsString(lineNameIndex)

                # if the next stream snap option includes the identifier in its name or there is no identifier, snap here
                if stationIdentifier in streamName or stationIdentifier == "":
                    chosenSnapIndex = i
                    break
            else:
                #end if the option we're considering is  more than twice as far away as the closest 
                break

        if chosenSnapIndex != 0:
            print("snapped to non-closest")
        snappedSites.append(snappedSite(site=site, snappedLocation = sortedPossibleSnaps[chosenSnapIndex][3]))

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



x = -74.3254918    #Long Lake
y =  44.0765791
#x = -76.3612354  #04249020
#y = 43.4810611
a = [x,y]
gdalData = GDALData(y, x, loadMethod=QUERYDATA)
#gdalData.loadFromQuery(y, x+0.3, attempts)
#gdalData.loadFromData()
snapped = Snap(gdalData)
visualize(gdalData, snapped)
gdalData.siteLayer.ResetReading()
#stationName_index = gdalData.siteLayer.GetLayerDefn().GetFieldIndex("station_nm")

""" for site in gdalData.siteLayer:
    stationName = site.GetFieldAsString(stationName_index)
    print(stationName + " ------- " + getSiteStreamName(stationName)) """