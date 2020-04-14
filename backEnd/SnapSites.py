import GDALData
import matplotlib.pyplot as plt
import Helpers
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

NUM_SNAPS = 3# how many possible locations that aren't the same as the nearest do we consider?
PERCENT_DIST_CUTOFF = 3 #if a potential snap is 
CUTOFF_DIST = 0.0005
adverbNameSeparators = [" at ", " above ", " near ", " below "]
waterTypeNames = [" brook", " pond", " river", " lake", " stream", " outlet", " creek", " bk", " ck"]
#a possible snap for a given point
Snap = collections.namedtuple('Snap', 'feature snapDistance distAlongFeature nameMatch')
# a point that can be snapped. Name and ID are used occasionally to aid in snapping
SnapablePoint = collections.namedtuple('SnapablePoint', 'point name id')


#Gets a key string from the site name that could be used to help snap sites later 
def getSiteStreamNameIdentifier (siteName):
    lowerCase = siteName.lower()
    endIndex = len(siteName)-1
    for adverb in adverbNameSeparators:
        try:
            endIndex = min(endIndex, lowerCase.index(adverb))
        except:       
            pass
    split = lowerCase[0:endIndex]
    
    """ for waterBody in waterTypeNames:
        try:
            endIndex = split.index(waterBody)
        except:
            pass """

    if endIndex == len(siteName)-1:
        return ""
    return lowerCase[0:endIndex]

def dot (x1, y1, x2, y2):
    return x1*x2 + y1*y2

def snapPoint(snapablePoint, baseData, graph = None):
    lineNameIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("GNIS_NAME")
    lengthIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("LENGTHKM")
    objectIDIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")

    lineLayer = baseData.lineLayer
    lineLayer.ResetReading()

    sitePoint = snapablePoint.point
    siteName = snapablePoint.name
    siteId = snapablePoint.id

    #mum of points to sample along the feature per kilometer in length
    #we assume that adjacent points in the geometry of the line are relatively continuous 
    # the goal here is to do a rough sorting of lines. But accurate enough that we can throw away lots of possibilities 
    samplesPerKM = 10
    sortedLines = []
    for line in lineLayer:
        lineGeom = line.GetGeometryRef()
        numPoints = lineGeom.GetPointCount()
        lineLength = float(line.GetFieldAsString(lengthIndex))
        numSamples = max(2, int(min(samplesPerKM * lineLength, numPoints)))

        minDist = sys.float_info.max

        for i in range(numSamples):
            #get index of geometry point.
            #attempt to space all points evenly
            geoIndex = int((i / (numSamples-1)) * (numPoints-1))
            point = lineGeom.GetPoint(geoIndex)
            dist = Helpers.fastMagDist(point[0], point[1], sitePoint[0], sitePoint[1])

            if dist < minDist:
                minDist = dist
            
        sortedLines.append((line, minDist))
    sortedLines = sorted(sortedLines, key=lambda line: line[1])
    
    numPossibleLines = min(NUM_SNAPS * 2, len(sortedLines))
    possibleLines = sortedLines[:numPossibleLines]
    
    #for all segments, store the point on each segment nearest to the site's location
    possibleSnaps = [] #(point index, point distance, streamSegment index)

    #get nearest point in the stream segment
    for sortedLine in possibleLines:
        line = sortedLine[0]
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
            #get a fast approx dist            
            distance = Helpers.fastMagDist(point[0], point[1], sitePoint[0], sitePoint[1])
            if distance < nearestPointDist:
                nearestPointDist = distance
                nearestPointIndex = i
                nearestPointDistAlongSegment = distAlongSegment

            distAlongSegment += geomSegmentLen
        
        nearestPoint = lineGeom.GetPoint(nearestPointIndex)
        #calculate the true distance
        nearestPointDist = Helpers.dist(sitePoint[0], sitePoint[1], nearestPoint[0], nearestPoint[1])
        snap = Snap(feature = line, snapDistance = nearestPointDist, distAlongFeature = nearestPointDistAlongSegment)
        possibleSnaps.append(snap)

    if len(possibleSnaps) == 0:
        return None

    sortedPossibleSnaps = sorted(possibleSnaps, key=lambda snap: snap.snapDistance)
    #limit the number of considered snaps to a fixed number
    consideredSnaps = sortedPossibleSnaps[:min(NUM_SNAPS, len(sortedPossibleSnaps))]

    #closestSnap = consideredSnaps[0].snapDistance
    #cutoff = closestSnap * PERCENT_DIST_CUTOFF

    #remove very unlikely snaps
    """ for snap in reversed(consideredSnaps):
        if snap.snapDistance > CUTOFF_DIST:
            consideredSnaps.remove(snap) """
    if siteId == "01309900":
        print("test")

    stationIdentifier = getSiteStreamNameIdentifier(siteName)
    if len(stationIdentifier) > 0:
        nameMatch = False
        nameMatchSnaps = []
        #find name match. If name match is found, then we can be sure of this snap
        for snap in consideredSnaps:
            lineName = snap.feature.GetFieldAsString(lineNameIndex).lower()
            if stationIdentifier in lineName:
                nameMatch = True
                nameMatchSnaps.append(snap)
        if nameMatch is True:
            consideredSnaps = nameMatchSnaps

    """ if len(stationIdentifier) > 0:
        nameMatch = False
        nameMatchSnaps = []
        #find name match. If name match is found, then we can be sure of this snap
        for snap in consideredSnaps:
            lineName = snap.feature.GetFieldAsString(lineNameIndex).lower()
            if stationIdentifier in lineName:
                nameMatch = True
                nameMatchSnaps.append(snap)
        if nameMatch is True:
            consideredSnaps = nameMatchSnaps """

    return consideredSnaps

def getSiteSnapAssignment (graph, debug = False):
    #a copy of the current graph used to try different possible snap operations
    testingGraph = graph#copy.deepcopy(graph)#.clone()
    testingGraphNavigator = StreamGraphNavigator(testingGraph)

    allSnaps = []
    for snaps in graph.siteSnaps.values():
        allSnaps.extend(snaps)

    #assign all possible snaps of each site to the graph
    testingGraph.refreshSiteSnaps(allSnaps)

    if debug:
        testingGraph.visualize()

    assignments = []
    possibleSnaps = {}

    def addAssignment (siteAssignment):
        alreadyContainedAssignment = False
        for i, assignment in enumerate(assignments):
            #if we find a match
            if assignment.siteID == siteAssignment.siteID:
                #and the newly added assignment is better than the original
                if siteAssignment.snapDist < assignment.snapDist:
                    #then replace
                    assignments[i] = siteAssignment
                else:
                    print("tried to add a second assignment")
                #at this point, we've either replaced, or not since our current assignment is worse
                return
        #if we reach this line then we don't have an assignment for this ID yet. Add one
        assignments.append(siteAssignment)

    def getSiteIndexRange (siteID, sites):
        firstIndex = -1
        lastIndex = -1

        for i, site in enumerate(sites):
            if site.siteID == siteID:
                if firstIndex == -1:
                    firstIndex = i
                lastIndex = i
        return (firstIndex, lastIndex)

    sinks = graph.getSinks()
    for sink in sinks:
        upstreamPaths = sink.getUpstreamNeighbors()
        for path in upstreamPaths:
            upstreamSitesInfo = testingGraphNavigator.collectSortedUpstreamSites(path, path.length, siteLimit = sys.maxsize, autoExpand = False)[0]
            #trim the extra distance info off of the results. Not needed
            upstreamSites = [siteInfo[0] for siteInfo in upstreamSitesInfo]
            
            #count all unique sites found on this branch. List them in order of appearance
            uniqueOrderedIDs = []
            for i, site in enumerate(upstreamSites):
                siteID = site.siteID
                if siteID not in uniqueOrderedIDs:
                    uniqueOrderedIDs.append(siteID)

            for orderedIdx, siteID in enumerate(uniqueOrderedIDs):
                firstOccuranceIdx, lastOccuranceIdx = getSiteIndexRange(siteID, upstreamSites)

                #get a list of possible assignments for this ID
                #Here, an choice is a tuple (assignment, index)
                siteChoices = []

                #Here, a ranked choice is a tuple (assignment, orderError, distScore)
                rankedChoices = []
                
                for i in range(firstOccuranceIdx, lastOccuranceIdx+1):
                    if upstreamSites[i].siteID == siteID:
                        siteChoices.append((upstreamSites[i], i))
                
                for choice in siteChoices:
                    assignment = choice[0]
                    upstreamSitesIdx = choice[1] #the index of this site in the list 'upstreamSites'
                    orderError = 0
                    distanceScore = 0
                    #calculate the order error for this choice
                    for i in range(orderedIdx, len(uniqueOrderedIDs)):
                        cmpSiteID = uniqueOrderedIDs[i]
                        cmpFirstOccuranceIdx, cmpLastOccuranceIdx = getSiteIndexRange(cmpSiteID, upstreamSites)
                        compare = Helpers.siteIDCompare(assignment.siteID, cmpSiteID)
                        #moving forward, if I choose this choice, will I cut off all the assignments for any remaining sites?
                        if cmpLastOccuranceIdx < upstreamSitesIdx and compare > 0:
                            # by choosing this choice, I'm stranding the the last snap choice 
                            # of a site with a lower ID than us downstream from us. 
                            orderError += 1
                        if cmpFirstOccuranceIdx > upstreamSitesIdx and compare < 0:
                            # by choosing this choice, I'm stranding all of the snap options 
                            # for cmpSite upstream from our current choice even though 
                            # cmpSiteID is higher than us 
                            orderError += 1
                    #for all sites that are 'involved' (appear between the first and last occurance index of the current site),
                    #find the best nearest possible distance allowed if we choose this assignment
                    minDistOfInvolved = {}

                    for i in range(upstreamSitesIdx, lastOccuranceIdx+1):
                        involvedID = upstreamSites[i].siteID
                        if involvedID != siteID:
                            #if this site is not the same as the one we are trying to assign:
                            if involvedID in minDistOfInvolved:
                                minDistOfInvolved[involvedID] = min(minDistOfInvolved[involvedID], upstreamSites[i].snapDist)
                            else:
                                minDistOfInvolved[involvedID] = upstreamSites[i].snapDist

                    # the total snap distance must be inceased by the snapDist of this choice
                    distanceScore += assignment.snapDist
                    # and it is increased at MINIMUM by the best choices remaining for other involved sites
                    for minDist in minDistOfInvolved.values():
                        distanceScore += minDist
                    
                    rankedChoices.append((assignment, orderError, distanceScore, upstreamSitesIdx))

                minOrderError = sys.maxsize
                bestScoreChoice = None
                #find the choice that minimize ordering error
                for choice in rankedChoices:
                    orderError = choice[1]
                    distanceScore = choice[2]
                    #if we find a better order error, always choose this option
                    if orderError < minOrderError:
                        bestScoreChoice = choice
                        minOrderError = orderError
                    elif orderError == minOrderError:
                        #if we find an equal order error but smaller dist score choice, choose it
                        bestDistScore = bestScoreChoice[2]
                        if distanceScore < bestDistScore:
                            bestScoreChoice = choice
                if bestScoreChoice[1] > 0:
                    print("adding a site with " + str(bestScoreChoice[1]) + " order error")

                bestScoreAssignment = bestScoreChoice[0]
                bestScoreUpstreamSitesIdx = bestScoreChoice[3]
                addAssignment(bestScoreAssignment)


    accountedForSiteIDs = set()
    for assignment in assignments:
        accountedForSiteIDs.add(assignment.siteID)
    
    for siteID in graph.siteSnaps:
        if siteID not in accountedForSiteIDs:
            print("missing site! adding post: " + str(siteID))
            #add the most likely snap for this site
            assignments.append(graph.siteSnaps[siteID][0])

    return assignments

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
        ly.append(p1[1])

        plt.plot(x, y, linewidth=1, color='blue')

    #display line endpoints
    #plt.scatter(lx,ly, color='black')
    siteNumberIndex = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
    siteLayer.ResetReading()
    x = []
    y = []
    for site in siteLayer:
        idNum = site.GetFieldAsString(siteNumberIndex)
        geom = site.GetGeometryRef()
        x.append(geom.GetPoint(0)[0])
        y.append(geom.GetPoint(0)[1])

        plt.text(geom.GetPoint(0)[0], geom.GetPoint(0)[1], idNum, color='red')
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


