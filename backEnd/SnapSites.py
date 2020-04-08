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

    closestSnap = consideredSnaps[0].snapDistance
    cutoff = closestSnap * PERCENT_DIST_CUTOFF

    #remove very unlikely snaps
    for snap in reversed(consideredSnaps):
        if snap.snapDistance > cutoff:
            consideredSnaps.remove(snap)


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
        #for snap in reversed(consideredSnaps):

    
    #if graph is not None and len(consideredSnaps) > 1:


    return consideredSnaps

def getSiteSnapAssignmentTwo(graph):
    #a copy of the current graph used to try different possible snap operations
    testingGraph = graph#copy.deepcopy(graph)#.clone()
    testingGraphNavigator = StreamGraphNavigator(testingGraph)

    allSnaps = []
    for snaps in graph.siteSnaps.values():
        allSnaps.extend(snaps)

    #assign all possible snaps of each site to the graph
    testingGraph.refreshSiteSnaps(allSnaps)

    #testingGraph.visualize()

    assignments = []
    possibleSnaps = {}

    def containsAssignment (siteID):
        for assignment in assignments:
            if assignment.siteID == siteID:
                return True
        return False

    def getSitesIndexRange (sites):
        firstSnapIndex = {} # a mapping of siteIDs to indexes.
        lastSnapIndex = {}
        for i, site in enumerate(sites):
            if site.siteID not in firstSnapIndex:
                firstSnapIndex[site.siteID] = i
            lastSnapIndex[site.siteID] = i
        return (firstSnapIndex, lastSnapIndex)

    sinks = graph.getSinks()
    for sink in sinks:
        upstreamPaths = sink.getUpstreamNeighbors()
        for path in upstreamPaths:
            upstreamSitesInfo = testingGraphNavigator.collectSortedUpstreamSites(path, path.length, siteLimit = sys.maxsize, autoExpand = False)
            #trim the extra distance info off of the results. Not needed
            upstreamSites = [siteInfo[0] for siteInfo in upstreamSitesInfo]
            #get the index bounds of each cluster of snaps of a particular site
            firstSnapIndex, lastSnapIndex = getSitesIndexRange(upstreamSites)
            
            #count all unique sites found on this branch. List them in order of appearance
            uniqueOrderedIDs = []
            for i, site in enumerate(upstreamSites):
                siteID = site.siteID
                if siteID not in uniqueOrderedIDs:
                    uniqueOrderedIDs.append(siteID)
            
            # iterate through all site IDs, based on their first and last occurances, 
            # remove snaps that are impossible
            # but keep snaps in place if they are impossible but removing them removes all instances
            # of the site. This means that the original IDs were assigned incorrectly 
            for testSiteID in uniqueOrderedIDs:
                testFirstOccuranceIdx = firstSnapIndex[testSiteID]
                testLastOccuranceIdx = lastSnapIndex[testSiteID]
                
                for i, iterSite in reversed(list(enumerate(upstreamSites))):
                    iterFirstOccuranceIdx = firstSnapIndex[iterSite.siteID]
                    iterLastOccuranceIdx = lastSnapIndex[iterSite.siteID]
                    # compare the siteID we are looking at 
                    compare = Helpers.siteIDCompare(testSiteID, iterSite.siteID)
                    # if this site is before the first occurance of our test site 
                    # and its number is lower than first occurance of our test site
                    # this is an invalid location of this site
                    if i < testFirstOccuranceIdx and compare > 0:
                        if iterLastOccuranceIdx < testFirstOccuranceIdx:
                            #this must be an invalid siteID case
                            #this is because the last occurance of the iterSite we're looking at 
                            #comes before the first occurance of the test site
                            # AND the itersite is smaller than the test site
                            # so, no combination of snaps would put this in the correct order
                            print ("the last snap of " + str(iterSite.siteID) + " is downstream the first snap of " + str(testSiteID))
                            pass
                        else:
                            upstreamSites.pop(i)
                    if i > testLastOccuranceIdx and compare < 0:
                        if iterFirstOccuranceIdx > testLastOccuranceIdx:
                            print("the first snap " + str(iterSite.siteID) + " is upstream of the last snap of " + str(testSiteID))
                            pass
                        else:
                            upstreamSites.pop(i)

            allSnaps = []
            
            for site in upstreamSites:
                if containsAssignment(site.siteID) is False:
                    assignments.append(site)

    accountedForSiteIDs = set()
    for assignment in assignments:
        accountedForSiteIDs.add(assignment.siteID)
    
    for siteID in graph.siteSnaps:
        if siteID not in accountedForSiteIDs:
            print("missing site! adding post: " + str(siteID))
            #add the most likely snap for this site
            assignments.append(graph.siteSnaps[siteID][0])

    return assignments
            


def getSiteSnapAssignment(graph):
    #a copy of the current graph used to try different possible snap operations
    testingGraph = graph#copy.deepcopy(graph)#.clone()
    testingGraphNavigator = StreamGraphNavigator(testingGraph)

    

    allSnaps = []
    for snaps in graph.siteSnaps.values():
        allSnaps.extend(snaps)

    #assign all possible snaps of each site to the graph
    testingGraph.refreshSiteSnaps(allSnaps)

    graph.visualize()

    # groups of isolated sites are those inclosed by two sites that have only 1 snap option
    # we find these by collecting all upstream sites from 
    # this dict is keyed by the downstream site of a two 1 snap site pair
    isolatedSiteGroups = []

    sinks = graph.getSinks()
    for sink in sinks:
        upstreamPaths = sink.getUpstreamNeighbors()
        for path in upstreamPaths:
            group = set()
            upstreamSites = testingGraphNavigator.collectSortedUpstreamSites(path, path.length, siteLimit = sys.maxsize, autoExpand = False)
            #at the beginning of the graph near s ink, before the first site can be considered an 'anchor'
            #since its a defined cutoff point 
            previousSiteAnchor = True
            for siteInfo in upstreamSites:
                site = siteInfo[0]

                # otherwise, continue building new group
                numSnaps = len(testingGraph.siteSnaps[site.siteID])
                if numSnaps == 1:
                    if previousSiteAnchor is False:
                        group.add(site.siteID)
                        isolatedSiteGroups.append(group)
                        group = set()
                        group.add(site.siteID)
                    else:
                        group = set()
                        group.add(site.siteID)
                else:
                    group.add(site.siteID)
                
                previousSiteAnchor = numSnaps==1
                    
            if len(group) > 1:
               isolatedSiteGroups.append(group)

    #since we added all site snaps to the graph before our search, there will be duplicates
    #for atleast each snap variation
    #but also could be duplicates if there is a downstream fork
    #so we merge all groups that contain the same site. These groups are co-dependent
    combinedIsolatedSiteGroups = []

    for group in isolatedSiteGroups:
        if len(combinedIsolatedSiteGroups) == 0:
            combinedIsolatedSiteGroups.append(group)
        else:
            foundIntersectingGroup = False
            for combinedGroup in combinedIsolatedSiteGroups:
                #check if two groups share sites in common
                allIntersections = group.intersection(combinedGroup)
                #need to ensure that sites shared have single snaps
                #since each group starts and ends with a site with 
                #a single snap (an anchor site)
                #these anchor sites can appear in multiple groups
                multiSnapSiteIntersections = set()
                for siteID in allIntersections:
                    if len(graph.siteSnaps[siteID]) > 1:
                        multiSnapSiteIntersections.add(siteID)
                #only if groups both contain a site with multiple possible snaps do we merge
                if len(multiSnapSiteIntersections) > 0:
                    combinedGroup.update(group)
                    foundIntersectingGroup = True

            if foundIntersectingGroup == False:
                combinedIsolatedSiteGroups.append(group)

    if len(combinedIsolatedSiteGroups) == 0:
        print("NO COMBINATIONS")

    #assignments is a list containing the final snap assignments for each site 
    assignments = []

    def containsAssignment (siteID):
        for assignment in assignments:
            if assignment.siteID == siteID:
                if len(graph.siteSnaps[siteID]) > 1:
                    print("Two assignments of site with more than 2 snaps. ERROR")
                return True
        return False

    for group in combinedIsolatedSiteGroups:
        allSnaps = []
        for siteID in group:
            allSnaps.append(graph.siteSnaps[siteID])
        combinations = list(itertools.product(*allSnaps))

        bestCombinations = []
        bestError = sys.maxsize

        #get the list of combinations that has the lowest error in siteID ordering
        #there could be multiple snaps that have this property
        for i, combination in enumerate(combinations):
            testingGraph.refreshSiteSnaps(combination)
            error = testingGraphNavigator.getGraphSiteIDError()

            if error < bestError:
                bestError = error
                bestCombinations = [combination]
            elif error == bestError:
                #if this is as good as the previous best, add it as a possibility
                bestCombinations.append(combination)

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

        #add this assignment to our total list
        for assignment in smallestSumDistCombination:
            if containsAssignment(assignment.siteID) is False:
                assignments.append(assignment)


    for snaps in graph.siteSnaps:
        if len(snaps) == 1:
            #only one assignment
            assignment = snaps[0]
            if containsAssignment(assignment.siteID):
                assignments.append(assignment)
            

    """ allSnaps = []

    for siteID in graph.siteSnaps:
        snaps = graph.siteSnaps[siteID]
        allSnaps.append(snaps)

    combinations = list(itertools.product(*allSnaps))

    bestCombinations = []
    bestError = sys.maxsize

    #get the list of combinations that has the lowest error in siteID ordering
    #there could be multiple snaps that have this property
    for i, combination in enumerate(combinations):
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
            smallestSumDistCombination = combination """

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


