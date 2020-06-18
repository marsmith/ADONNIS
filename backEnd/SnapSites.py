import GDALData
import Helpers
import math
import sys
import collections
from StreamGraphNavigator import StreamGraphNavigator
import copy
import Failures
import WarningLog

if __debug__:
    import matplotlib.pyplot as plt

NUM_SNAPS = 6# how many possible locations that aren't the same as the nearest do we consider?
CUTOFF_DIST = 0.01
WARNING_DIST = 0.003
POINTS_PER_LINE = 2 #how many possible points on a given feature do we consider for snapping
adverbNameSeparators = [" at ", " above ", " near ", " below "]
waterTypeNames = [" brook", " pond", " river", " lake", " stream", " outlet", " creek", " bk", " ck"]
#a possible snap for a given point
Snap = collections.namedtuple('Snap', 'feature snapDistance distAlongFeature nameMatch warnings')
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
    
    if endIndex == len(siteName)-1:
        return ""
    return lowerCase[0:endIndex]

#snap a point to stream data. Basedata is expected to be a baseData object with GEOJson formatted data 
def snapPoint(snapablePoint, baseData, snapCutoff = CUTOFF_DIST):

    lineLayer = baseData.lineLayer

    sitePoint = snapablePoint.point
    siteName = snapablePoint.name
    siteId = snapablePoint.id
    stationIdentifier = getSiteStreamNameIdentifier(siteName)

    #mum of points to sample along the feature per kilometer in length
    #we assume that adjacent points in the geometry of the line are relatively continuous 
    # the goal here is to do a rough sorting of lines. But accurate enough that we can throw away lots of possibilities 
    samplesPerKM = 10
    sortedLines = []
    for line in lineLayer:
        lineGeom = line["geometry"]["coordinates"]
        numPoints = len(lineGeom)
        lineLength = float(line["properties"]["LENGTHKM"])
        numSamples = max(2, int(min(samplesPerKM * lineLength, numPoints)))
        objectID = line["properties"]["OBJECTID"]

        minDist = sys.float_info.max

        for i in range(numSamples):
            #get index of geometry point.
            #attempt to space all points evenly
            geoIndex = int((i / (numSamples-1)) * (numPoints-1))
            point = lineGeom[geoIndex]
            dist = Helpers.fastMagDist(point[0], point[1], sitePoint[0], sitePoint[1])

            if dist < minDist:
                minDist = dist
            
        sortedLines.append((line, minDist))
    sortedLines = sorted(sortedLines, key=lambda line: line[1])
    
    numPossibleLines = min(NUM_SNAPS * 2, len(sortedLines))
    possibleLines = sortedLines[:numPossibleLines]
    
    #for all segments, store the point on each segment nearest to the site's location
    possibleSnaps = [] #(point index, point distance, streamSegment index)

    nameMatchFound = False

    #get nearest point in the stream segment
    for sortedLine in possibleLines:
        line = sortedLine[0]
        lineGeom = line["geometry"]["coordinates"]
        numPoints = len(lineGeom)
        lineLength = float(line["properties"]["LENGTHKM"])
        objectID = line["properties"]["OBJECTID"]
        lineName = line["properties"]["GNIS_NAME"]


        if lineName == None:
            lineName = ""
        else:
            lineName = lineName.lower()

        nameMatch = False
        if len(stationIdentifier) > 0:
            if stationIdentifier in lineName:
                nameMatch = True

        averagePointDistance = lineLength / (numPoints-1)

        summedDistAlongSegment = 0
        nearestPointDistanceSqr = sys.float_info.max
        nearestPointDistAlongSegment = 0
        nearestPoint = None
        for i in range(0, numPoints-1):
            p1 = lineGeom[i]
            p2 = lineGeom[i+1]
            pointOnSegment, t = Helpers.nearestPointOnSegment(p1[0], p1[1], p2[0], p2[1], sitePoint[0], sitePoint[1])

            distanceSqr = Helpers.fastMagDist(sitePoint[0], sitePoint[1], pointOnSegment[0], pointOnSegment[1])

            if distanceSqr < nearestPointDistanceSqr:
                nearestPointDistanceSqr = distanceSqr
                nearestPointDistAlongSegment = summedDistAlongSegment + t * averagePointDistance
                nearestPoint = pointOnSegment
            summedDistAlongSegment += averagePointDistance

        warnings = []
        trueDist = math.sqrt(nearestPointDistanceSqr)
        if trueDist > WARNING_DIST:
            message = Helpers.formatID(str(siteId)) + " was forced to snap to an above averagely far away stream. This could be a faulty snap."
            warning = WarningLog.Warning(priority = WarningLog.LOW_PRIORITY, message = message, responsibleSite = siteId, implicatedSites = None)
            warnings.append(warning)
        snap = Snap(feature = line, snapDistance = trueDist, distAlongFeature = nearestPointDistAlongSegment, nameMatch = nameMatch, warnings = warnings)
        possibleSnaps.append(snap)
 

    sortedPossibleSnaps = sorted(possibleSnaps, key=lambda snap: snap.snapDistance)

    #limit the number of considered snaps to a fixed number
    consideredSnaps = sortedPossibleSnaps#sortedPossibleSnaps[:min(NUM_SNAPS, len(sortedPossibleSnaps))]
    nameMatchFound = False
    for i, snap in reversed(list(enumerate(consideredSnaps))):
        if snap.snapDistance > snapCutoff:
            consideredSnaps.pop(i)
        else:
            nameMatchFound = nameMatchFound or snap.nameMatch
    
    for i, snap in reversed(list(enumerate(consideredSnaps))):
        if snap.nameMatch == False and nameMatchFound == True:
            consideredSnaps.pop(i)

    if len(consideredSnaps) == 0:
        # if siteId == "01387700":
        #     print("test")
        return Failures.SNAP_FAILURE_CODE

    return consideredSnaps

#get a list of assignments for a given graph and a list of warnings generated
def getSiteSnapAssignment (graph, assignBadSites = False):
    #a copy of the current graph used to try different possible snap operations
    testingGraph = graph#copy.deepcopy(graph)#.clone()
    testingGraphNavigator = StreamGraphNavigator(testingGraph)

    allSnaps = []
    for snaps in graph.siteSnaps.values():
        allSnaps.extend(snaps)

    #assign all possible snaps of each site to the graph
    testingGraph.assignSiteSnaps(allSnaps)

    assignments = []
    allRankedChoices = {}

    def addAssignment (siteAssignment):
        alreadyContainedAssignment = False
        for i, assignment in enumerate(assignments):
            #if we find a match
            if assignment.siteID == siteAssignment.siteID:
                #and the newly added assignment is better than the original
                if siteAssignment.snapDist < assignment.snapDist:
                    #then replace
                    assignments[i] = siteAssignment
                elif __debug__:
                    print("tried to add a second assignment")
                #at this point, we've either replaced, or not since our current assignment is worse
                return
        #if we reach this line then we don't have an assignment for this ID yet. Add one
        assignments.append(siteAssignment)

    def removeAssignment (siteID):
        for i, assignment in enumerate(assignments):
            if assignment.siteID == siteID:
                assignments.pop(i)
                return

    #get the range of occurances of siteID in a list of IDs (sites)
    def getSiteIndexRange (siteID, sites):
        firstIndex = -1
        lastIndex = -1

        for i, site in enumerate(sites):
            if site.siteID == siteID:
                if firstIndex == -1:
                    firstIndex = i
                lastIndex = i
        return (firstIndex, lastIndex)

    #given a list of rankedChoices:
    #(assignment, orderError, distanceScore, upstreamSitesIdx, nameMatch, orderConflicts)
    #choose the best choice based on a tiered system. 
    def getBestRankedChoice (rankedChoices):
        minOrderError = sys.maxsize
        bestScoreChoice = None
        #find the choice that minimize ordering error
        for choice in rankedChoices:
            orderError = choice[1]
            distanceScore = choice[2]
            nameMatch = choice[4]
            #if we find a better order error, always choose this option
            if orderError < minOrderError:
                bestScoreChoice = choice
                minOrderError = orderError
            elif orderError == minOrderError:
                #if we find an equal order error but smaller dist score choice, choose it
                bestDistScore = bestScoreChoice[2]
                bestScoreNameMatch = bestScoreChoice[4]
                # if this dist is better than previous
                # AND either this choice is a name match or this isn't and the previous best isn't
                if distanceScore < bestDistScore and (nameMatch or (not nameMatch and not bestScoreNameMatch)):
                    bestScoreChoice = choice
        return bestScoreChoice

    #loop through all upstream paths by getting all sinks and getting all upstream paths from each sink
    sinks = graph.getSinks()
    for sink in sinks:
        upstreamPaths = sink.getUpstreamNeighbors()
        for path in upstreamPaths:
            upstreamSitesInfo = testingGraphNavigator.collectSortedUpstreamSites(path, path.length, siteLimit = sys.maxsize, autoExpand = False)[0]
            #trim the extra distance info off of the results. Not needed
            upstreamSites = [siteInfo[0] for siteInfo in upstreamSitesInfo]

            siteIndexRanges = {}
            for site in upstreamSites:
                siteID = site.siteID
                if siteID not in siteIndexRanges:
                    firstOccuranceIdx, lastOccuranceIdx = getSiteIndexRange(siteID, upstreamSites)
                    siteIndexRanges[siteID] = (firstOccuranceIdx, lastOccuranceIdx)
            
            #count all unique sites found on this branch. List them in order of appearance
            uniqueOrderedIDs = []
            for i, site in enumerate(upstreamSites):
                siteID = site.siteID
                if siteID not in uniqueOrderedIDs:
                    uniqueOrderedIDs.append(siteID)
            uniqueOrderedIDs = sorted(uniqueOrderedIDs, key=lambda site: int(Helpers.getFullID(site)), reverse=True)
            #list of sites that have already been chosen on this branch
            resolvedSites = dict()

            for orderedIdx, siteID in enumerate(uniqueOrderedIDs):
                firstOccuranceIdx, lastOccuranceIdx = siteIndexRanges[siteID]

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
                    nameMatch = assignment.nameMatch
                    #siteIDs that this assignment will force an out of sequence snap for
                    orderConflicts = []
                    #calculate the order error for this choice
                    for i in range(0, len(uniqueOrderedIDs)):
                        cmpSiteID = uniqueOrderedIDs[i]
                        #the case when we are comparing to a site thats been resolved
                        #is different than the case when a site we compare to is unresolved 

                        #if the cmp site is unresolved, we are looking to see if this site's choice 
                        #will force an order error for site that has yet to be chosen

                        #if the cmp site is resolved, we are looking to see if this site's choice
                        #conflicts with the choice ALREADY made for the cmp site

                        if cmpSiteID in resolvedSites:
                            #the third elem in the tuple is the ranked choice's upstream sites index
                            resolvedCmpUpstreamSitesIdx = resolvedSites[cmpSiteID][3]
                            #if this cmp site is resolved it must be a larger ID than us because
                            #sites are resolved in decending order of their IDs
                            if upstreamSitesIdx < resolvedCmpUpstreamSitesIdx:
                                orderError += 1
                                orderConflicts.append(cmpSiteID)
                        else:
                            cmpFirstOccuranceIdx, cmpLastOccuranceIdx = siteIndexRanges[cmpSiteID]
                            compare = Helpers.siteIDCompare(assignment.siteID, cmpSiteID)
                            #moving forward, if I choose this choice, will I cut off all the assignments for any remaining sites?
                            if cmpLastOccuranceIdx < upstreamSitesIdx and compare > 0:
                                # by choosing this choice, I'm stranding the the last snap choice 
                                # of a site with a lower ID than us downstream from us. 
                                orderError += 1
                                orderConflicts.append(cmpSiteID)
                            if cmpFirstOccuranceIdx > upstreamSitesIdx and compare < 0:
                                # by choosing this choice, I'm stranding all of the snap options 
                                # for cmpSite upstream from our current choice even though 
                                # cmpSiteID is higher than us 
                                orderError += 1
                                orderConflicts.append(cmpSiteID)
                    #get list of sites involved in the outcome of this sites snap choice
                    #this is all site IDs that have a snap choice that appears between the first instance of the 
                    #current site id and the last instance in the traversal 
                    involvedSites = set()
                    for i in range(firstOccuranceIdx+1, lastOccuranceIdx):
                        if upstreamSites[i].siteID != siteID and upstreamSites[i].siteID not in resolvedSites:
                            involvedSites.add(upstreamSites[i].siteID)

                    #for all sites that are 'involved' (appear between the first and last occurance index of the current site),
                    #find the best nearest possible distance allowed if we choose this assignment
                    minDistOfInvolved = {}

                    # by starting this loop at the index of the choice,
                    # we won't get snap options of this involved site that occur before the index of the current 
                    # choice. This is because if we choose this choice, anything before it on the traversal can't be chosen anymore
                    # if there are no instances of an involved site that occur after this choice, it won't be counted
                    # But, then that should trigger an increase in order error.
                    # since order error is taken as higher priority than distance, the fact we don't
                    # count up the distance for the missing site shouldn't be an issue
                    for i in range(upstreamSitesIdx, len(upstreamSites)):
                        involvedID = upstreamSites[i].siteID
                        #check if this site is truely an involved site
                        if involvedID in involvedSites:
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
                    
                    rankedChoices.append((assignment, orderError, distanceScore, upstreamSitesIdx, nameMatch, orderConflicts))

                bestScoreChoice = getBestRankedChoice(rankedChoices)
                resolvedSites[siteID] = bestScoreChoice

                if siteID in allRankedChoices:
                    #catch case when a site gets snapped onto two networks 
                    #later on we choose which network has the best fit
                    allRankedChoices[siteID].append(bestScoreChoice)
                else:
                    allRankedChoices[siteID] = [bestScoreChoice]

    #holds tuples of two sites that conflict with eachother. 
    siteConflicts = set()

    #choose an assignment from the prefiltered list of best choices
    #in almost all cases, there will only be one ranked choice to choose from
    #there will only be two if the site had a possible snap on two networks with different sinks
    for choices in allRankedChoices.values():
        bestRankedChoice = getBestRankedChoice(choices)
        assignment = bestRankedChoice[0]
        addAssignment(assignment)

        # for each conflict forced by this choice, add a conflict to the total list going 
        # in both directions (a conflicts with b AND b conflicts with a)
        orderConflicts = bestRankedChoice[5]
        for conflictingSite in orderConflicts:
            conflictingCmp = Helpers.siteIDCompare(conflictingSite, assignment.siteID)
            #make sure we put the larger ID first so that if this pair appears again we don't add it again (bc we use a set)
            if conflictingCmp > 0:
                siteConflicts.add((conflictingSite, assignment.siteID))
            else:
                siteConflicts.add((assignment.siteID, conflictingSite))

        if bestRankedChoice[1] > 0 and __debug__:
            print("adding " + assignment.siteID + " with " + str(bestRankedChoice[1]) + " order error:")
            for conflictingSite in bestRankedChoice[5]:
                print("\t conflicts with " + conflictingSite)      

    #this code doesn't really do anything. The above code accounts for all site IDs getting assigned
    """ #verify that all site IDs are accounted for
    #this code should never really have to run
    accountedForSiteIDs = set()
    for assignment in assignments:
        accountedForSiteIDs.add(assignment.siteID)
    
    for siteID in graph.siteSnaps:
        if siteID not in accountedForSiteIDs:
            if __debug__:
                print("missing site! adding in post: " + str(siteID))
            #add the most likely snap for this site
            assignments.append(graph.siteSnaps[siteID][0]) """

    #keep track of which sites we think are causing the conflicts
    atFaultSites = []
    atFaultPairs = []
    #store all sites that may be involved in a conflict
    allImplicatedSites = set()

    while len(siteConflicts) > 0:
        #count which sites appear in the most number of conflicts
        siteConflictTotals = dict((siteID, []) for siteID in graph.siteSnaps)
        mostConflicts = 0
        mostConflictingSite = None

        for conflict in siteConflicts:
            #a conflict is between two sites, a, and b
            conflictA = conflict[0]
            conflictB = conflict[1]
            
            #for this conflict pair add an involvement to both sites
            siteConflictTotals[conflictA].append(conflictB) 
            siteConflictTotals[conflictB].append(conflictA)

            if len(siteConflictTotals[conflictA]) > mostConflicts:
                mostConflicts = len(siteConflictTotals[conflictA])
                mostConflictingSite = conflictA
            
            if len(siteConflictTotals[conflictB]) > mostConflicts:
                mostConflicts = len(siteConflictTotals[conflictB])
                mostConflictingSite = conflictB
        
        #catch cases when sites conflict with eachother equally and fixing either would remove issues
        
        if mostConflicts == 1:
            #find the conflict pair that caused this conflict
            for conflict in siteConflicts:
                conflictA = conflict[0]
                conflictB = conflict[1]

                if conflictA == mostConflictingSite or conflictB == mostConflictingSite:
                    atFaultPairs.append((conflictA, conflictB))
                    allImplicatedSites.add(conflictA)
                    allImplicatedSites.add(conflictB)
                    break
        else:
            #remove this conflict and keep track of it as a problem site
            atFaultSites.append((mostConflictingSite, siteConflictTotals[mostConflictingSite]))
            allImplicatedSites.add(mostConflictingSite)

        siteConflictsCpy = siteConflicts.copy()
        for conflict in siteConflictsCpy:
            #a conflict is between two sites
            conflictA = conflict[0]
            conflictB = conflict[1]

            if conflictA == mostConflictingSite or conflictB == mostConflictingSite:
                siteConflicts.remove(conflict)

    warnings = []
    assignmentWarnings = []
    
    #generate warnings such as site a conflicts with x other sites
    for faultySite in atFaultSites:
        faultySiteID = faultySite[0]
        faultySiteConflicts = faultySite[1]
        conflictingSitesString = Helpers.formatList([Helpers.formatID(fsc) for fsc in faultySiteConflicts])
        
        message = Helpers.formatID(faultySiteID) + " conflicts with " + conflictingSitesString + ". Consider changing this site's ID"
        warnings.append(WarningLog.Warning(priority=WarningLog.MED_PRIORITY, message=message, responsibleSite = faultySiteID, implicatedSites=faultySiteConflicts))
    #generate warnings like site a conflicts with site b, replace either
    for faultyPair in atFaultPairs:
        pairA = str(faultyPair[0])
        pairB = str(faultyPair[1])
        message = Helpers.formatID(pairA) + " conflicts with " + Helpers.formatID(pairB) + ". Consider changing the site ID of one of these two sites"
        warnings.append(WarningLog.Warning(priority=WarningLog.MED_PRIORITY, message=message, responsibleSite = pairA, implicatedSites = [pairB]))

    #finally, assign any warning to the site itself
    for assignment in assignments:
        assignmentSiteID = assignment.siteID
        if assignmentSiteID in allImplicatedSites:
            message = Helpers.formatID(assignmentSiteID) + " was used to generate results AND is involved in a site conflict. See story/medium priority warnings for conflict details."
            warning = WarningLog.Warning(WarningLog.HIGH_PRIORITY, message, responsibleSite=assignmentSiteID, implicatedSites=None)
            assignment.assignmentWarnings.clear()
            assignment.assignmentWarnings.append(warning)

    #if we are not assigning bad sites remove all assignments related to at fault sites
    if not assignBadSites:
        for assignmentID in allImplicatedSites:
            if assignmentID in allImplicatedSites:
                removeAssignment(assignmentID)

    #we return warnings instead of adding them to log directly because this function may run many times
    #with each new query. So storing warnings in the graph allows the most up to date warnings to be 
    #retrieved at the time of returning the finished site ID data
    return (assignments, warnings)

if __debug__:
    #Visualizes 
    def visualize (baseData, snapped):
        siteLayer = baseData.siteLayer
        lineLayer = baseData.lineLayer

        for line in lineLayer:
            
            geom = line["geometry"]["coordinates"]
            numPoints = len(geom)
            x = []
            y = []
            for i in range(0, numPoints):
                p = geom[i]
                x.append(p[0])
                y.append(p[1])


            plt.plot(x, y, linewidth=1, color='blue')

        #display line endpoints
        #plt.scatter(lx,ly, color='black')
        x = []
        y = []
        for site in siteLayer:
            idNum = site["properties"]["site_no"]
            geom = site["geometry"]["coordinates"]
            x.append(geom[0])
            y.append(geom[1])

            plt.text(geom[0], geom[1], idNum, color='red')
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