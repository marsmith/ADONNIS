from StreamGraphNavigator import StreamGraphNavigator
from StreamGraph import StreamGraph
from SnapSites import snapPoint, SnapablePoint
import SnapSites
import GDALData
import Helpers
from SiteIDManager import SiteIDManager
import Failures
import math
import sys
import json
import WarningLog
import collections

#---query limits
MAX_PRIMARY_QUERIES = 30
#how many queries will we try AFTER finding a single upstream/downstream site to find the other upstream/downstream site?
MAX_SECONDARY_SITE_QUERIES = 5
#what's the smallest reasonable distance between two sites
#according to Gary Wall this is 500 feet 
#rounding down to be safe, we get 100 meters 
MIN_SITE_DISTANCE = 0.1 #(kilometers)

#---naming
AT_DISTANCE = 1609.34 #(meters) a mile. Otherwise, name is "near"
CONTEXT_DIST_LIMIT = 4000 #about 2.5 miles


def getSiteNameContext (lat, lng, streamGraph, baseData):
    context = {}
    point = (lng, lat)
    snapablePoint = SnapablePoint(point = point, name = "", id = "")
    snapInfo = snapPoint(snapablePoint, baseData) #get the most likely snap

    feature = snapInfo[0].feature
    
    segmentID = str(feature["properties"]["OBJECTID"])

    distAlongSegment = snapInfo[0].distAlongFeature
    #get the segment ID of the snapped segment
    graphSegment = streamGraph.getCleanedSegment(segmentID)

    navigator = StreamGraphNavigator(streamGraph)

    downstreamSegment = navigator.findNextLowerStreamLevelPath(graphSegment, expand = False)
    
    streamName = graphSegment.streamName
    if streamName == "":
        if not Failures.isFailureCode(downstreamSegment) and downstreamSegment.streamName != "":
            context["streamName"] = downstreamSegment.streamName + " tributary"
        else:
            context["streamName"] = "(INSERT STREAM NAME)"
    else:
        context["streamName"] = streamName
    
    placeInfo = GDALData.getNearestPlace(lat, lng)
    if Failures.isFailureCode(placeInfo):
        context["distanceToPlace"] = "-1"
        context["state"] = "unknown"
        context["placeName"] = "unknown"
    else:
        context["distanceToPlace"] = placeInfo["distanceToPlace"]
        context["state"] = placeInfo["state"]
        context["placeName"] = placeInfo["placeName"]
    context["lat"] = lat
    context["long"] = lng

    contextualPlaces = []
    
    bridges = GDALData.getNearestBridges(lat, lng)
    namedTribMouths = navigator.getNamedTribMouths()
    
    contextualPlaces.extend([{"name": context.name, "point":context.point, "distance":context.distance} for context in bridges])
    contextualPlaces.extend([{"name": mouth[0], "point": mouth[1], "distance":Helpers.degDistance(mouth[1][0], mouth[1][1], lng, lat)} for mouth in namedTribMouths])

    context["contextualPlaces"] = contextualPlaces

    return context
    

def getSiteNameInfo (siteNameContext):
    #beginning of name
    beginning = siteNameContext["streamName"] + " "

    #middle of the name. more choices here
    middle = []

    lat = siteNameContext["lat"]
    lng = siteNameContext["long"]

    middle.append ("")#capture base case when we don't want any middle context
    sortedContextualPlaces = sorted(siteNameContext["contextualPlaces"], key=lambda context: context["distance"])
    sortedContextualPlaces = sortedContextualPlaces[:min(3, len(sortedContextualPlaces))]
    for contextPlace in sortedContextualPlaces:
        name = contextPlace["name"]
        distance = contextPlace["distance"]
        point = contextPlace["point"]

        if distance > CONTEXT_DIST_LIMIT:
            continue

        cardinalDirection = Helpers.getCardinalDirection(point, (lng, lat))

        """ if distance < AT_DISTANCE:
            middle.append("at " + name + " ")
        else: """
        middle.append("near " + name + " ")

        #middle.append(cardinalDirection + " of " + name + " ")

        distMiles = Helpers.metersToMiles(distance)

        roundDist = Helpers.roundTo(distMiles, 0.1)
        roungDistStr = str(roundDist)[:3]
        if roundDist > 1 or roundDist < 1:
            middle.append(roungDistStr + " miles " + cardinalDirection + " of " + name + " ")
        else:
            middle.append("1 mile " + cardinalDirection + " of " + name + " ")

    #end of name
    end = ""
    if siteNameContext["distanceToPlace"] < AT_DISTANCE:
        end = "at "
    else:
        end = "near "

    end += siteNameContext["placeName"] + " " + siteNameContext["state"]

    allNames = [(beginning + possibleMiddle + end).upper() for possibleMiddle in middle]

    return {"suggestedNames":allNames, "context":siteNameContext}


#withheld sites is a list of sites to be ignored while calculating a new site
def getSiteID (lat, lng, withheldSites = [], debug = False):
    warningLog = WarningLog.WarningLog(lat, lng)
    
    streamGraph = StreamGraph(withheldSites = withheldSites, debug = debug, warningLog = warningLog)
    siteIDManager = SiteIDManager()

    #typically lat/long are switched to fit the x/y order paradigm 
    point = (lng, lat)
    #get data around query point and construct a graph
    baseData = GDALData.loadFromQuery(lat, lng)

    #create the json that gets resturned
    def getResults (siteID = "unknown", story = "See warning log", failed=False):
        if not failed:
            siteNameContext = getSiteNameContext(lat, lng, streamGraph, baseData)
            nameResults = getSiteNameInfo(siteNameContext)
        else:
            nameResults = {"suggestedNames":["unknown"], "context":{}}


        results = dict()
        results["id"] = siteID
        results["story"] = "Requested site info at " + str(lat)[:7] + ", " + str(lng)[:7] + ". " + story
        results["log"] = warningLog.getJSON()
        results["nameInfo"] = nameResults
        return results

    if Failures.isFailureCode(baseData):
        if debug is True:
            print ("could not get data")
        warningLog.addWarning(WarningLog.HIGH_PRIORITY, baseData)
        return getResults()

    streamGraph.addGeom(baseData)

    #snap query point to a segment
    snapablePoint = SnapablePoint(point = point, name = "", id = "")
    snapInfo = snapPoint(snapablePoint, baseData) #get the most likely snap
    if Failures.isFailureCode(snapInfo):
        if debug is True:
            print ("could not snap")
        warningLog.addWarning(WarningLog.HIGH_PRIORITY, snapInfo)
        return getResults()

    feature = snapInfo[0].feature
    segmentID = str(feature["properties"]["OBJECTID"])
    distAlongSegment = snapInfo[0].distAlongFeature
    #get the segment ID of the snapped segment
    graphSegment = streamGraph.getCleanedSegment(segmentID)

    snappedPoint = streamGraph.segments[segmentID].getPointOnSegment(distAlongSegment)

    if debug:
        SnapSites.visualize(baseData, [])
        streamGraph.visualize(customPoints=[snappedPoint], showSegInfo = True)
        streamGraph.visualize(customPoints=[snappedPoint], showSegInfo = False)

    #build a navigator object
    #we want to terminate the search each time a query happens
    #this allows us to stagger upstream and downstream searches
    #although this means repeating parts of the search multiple times, searching a already constructed
    #graph takes practically no time at all
    navigator = StreamGraphNavigator(streamGraph, terminateSearchOnQuery = True, debug = debug)

    upstreamSite = None
    downstreamSite = None
    endOfUpstreamNetwork = False
    endOfDownstreamNetwork = False
    secondaryQueries = 0
    primaryQueries = 0

    #each iteration extends the graph by one query worth of data
    # in this step we try to find an upstream and downstream site
    while (upstreamSite is None or downstreamSite is None) and secondaryQueries < MAX_SECONDARY_SITE_QUERIES and primaryQueries < MAX_PRIMARY_QUERIES and (endOfUpstreamNetwork is False or endOfDownstreamNetwork is False):
        if upstreamSite is None and endOfUpstreamNetwork is False:
            #we haven't found upstream yet
            upstreamReturn = navigator.getNextUpstreamSite(graphSegment, distAlongSegment)
            if upstreamReturn == Failures.END_OF_BASIN_CODE:
                endOfUpstreamNetwork = True
            if Failures.isFailureCode(upstreamReturn) is not True and upstreamReturn is not None:
                upstreamSite = upstreamReturn

        if downstreamSite is None and endOfDownstreamNetwork is False:
            #we haven't found downstream yet
            downstreamReturn = navigator.getNextDownstreamSite(graphSegment, distAlongSegment)
            if downstreamReturn == Failures.END_OF_BASIN_CODE:
                endOfDownstreamNetwork = True
            if Failures.isFailureCode(downstreamReturn) is not True and downstreamReturn is not None:
                downstreamSite = downstreamReturn

        if upstreamSite is not None or downstreamSite is not None:
            #we've found at least one site
            secondaryQueries += 1
        else:
            primaryQueries += 1

    #add warnings from found sites
    if upstreamSite is not None:
        siteAssignment = upstreamSite[0]
        for warning in siteAssignment.generalWarnings:
            warningLog.addWarningTuple(warning)
        for warning in siteAssignment.assignmentWarnings:
            warningLog.addWarningTuple(warning)
    
    if downstreamSite is not None:
        siteAssignment = downstreamSite[0]
        for warning in siteAssignment.generalWarnings:
            warningLog.addWarningTuple(warning)
        for warning in siteAssignment.assignmentWarnings:
            warningLog.addWarningTuple(warning)
    
    for warning in streamGraph.currentAssignmentWarnings:
        warningLog.addWarningTuple(warning)

    story = ""
    newID = ""

    if upstreamSite is not None and downstreamSite is not None:
        #we have an upstream and downstream

        upstreamSiteID = upstreamSite[0].siteID
        downstreamSiteID = downstreamSite[0].siteID
        partCode = upstreamSiteID[0:2]

        if Helpers.siteIDCompare(downstreamSiteID, upstreamSiteID) < 0:
            message = "The found upstream site is larger than found downstream site. ADONNIS output almost certainly incorrect."
            warningLog.addWarning(WarningLog.HIGH_PRIORITY, message)

        fullUpstreamSiteID = Helpers.getFullID(upstreamSiteID)
        fullDownstreamSiteID = Helpers.getFullID(downstreamSiteID)

        upstreamSiteIdDsnStr = fullUpstreamSiteID[2:]
        downstreamSiteIdDsnStr = fullDownstreamSiteID[2:]

        #get the downstream number portion of the ID
        upstreamSiteIdDsn = int(upstreamSiteIdDsnStr)
        downstreamSiteIdDsn = int(downstreamSiteIdDsnStr)

        totalAddressSpaceDistance = upstreamSite[1] + downstreamSite[1]
        newSitePercentage = downstreamSite[1] / totalAddressSpaceDistance

        newDon = int(downstreamSiteIdDsn * (1 - newSitePercentage) + upstreamSiteIdDsn * newSitePercentage)

        newID = Helpers.buildFullID(partCode, newDon)
        newID = beautifyID(newID, downstreamSiteID, upstreamSiteID, warningLog)
        story = "Found an upstream site (" + upstreamSiteID + ") and a downstream site (" + downstreamSiteID + "). New site is the weighted average of these two sites."

        if debug is True:
            print ("found upstream is " + upstreamSiteID)
            print ("found downstream is " + downstreamSiteID)
            streamGraph.visualize(customPoints=[snappedPoint])
            SnapSites.visualize(baseData, [])
        
    elif upstreamSite is not None:
        upstreamSiteID = upstreamSite[0].siteID
        partCode = upstreamSiteID[:2]
        fullUpstreamID = Helpers.getFullID(upstreamSiteID)

        upstreamSiteDSN = int(fullUpstreamID[2:])
        upstreamSiteDistance = upstreamSite[1]

        siteIDOffset = math.ceil(upstreamSiteDistance / MIN_SITE_DISTANCE)

        newSiteIDDSN = upstreamSiteDSN + siteIDOffset

        #allowed wiggle room in the new site. Depending on how much distance is between the found site
        #we allow for a larger range in the final ID. Has to be at least 10% within the rule of min_site_distance
        allowedError = math.floor(max(1, min(siteIDOffset / 10, 5)))

        upperBound = Helpers.buildFullID(partCode, upstreamSiteDSN + siteIDOffset + allowedError)
        lowerBound = Helpers.buildFullID(partCode, upstreamSiteDSN + siteIDOffset - allowedError)
        
        newID = Helpers.buildFullID(partCode, newSiteIDDSN)
        newID = beautifyID(newID, lowerBound, upperBound, warningLog)
        offsetAfterBeautify = Helpers.getSiteIDOffset(newID, fullUpstreamID)
        story = "Only found a upstream site (" + upstreamSiteID + "). New site ID is based on upstream site while allowing space for " + str(offsetAfterBeautify) + " sites between upstream site and new site"
        
        if debug is True:
            print("found upstream, but not downstream")
            print("upstream siteID is " + str(upstreamSiteID))
            streamGraph.visualize(customPoints=[snappedPoint])
            SnapSites.visualize(baseData, [])

    elif downstreamSite is not None:
        downstreamSiteID = downstreamSite[0].siteID
        partCode = downstreamSiteID[:2]
        fullDownstreamID = Helpers.getFullID(downstreamSiteID)

        downstreamSiteDSN = int(fullDownstreamID[2:])
        downstreamSiteDistance = downstreamSite[1]

        siteIDOffset = math.ceil(downstreamSiteDistance / MIN_SITE_DISTANCE)

        newSiteIDDSN = downstreamSiteDSN - siteIDOffset

        allowedError = math.floor(max(1, min(siteIDOffset / 10, 5)))

        upperBound = Helpers.buildFullID(partCode, downstreamSiteDSN - siteIDOffset + allowedError)
        lowerBound = Helpers.buildFullID(partCode, downstreamSiteDSN - siteIDOffset - allowedError)
        
        newID = Helpers.buildFullID(partCode, newSiteIDDSN)
        newID = beautifyID(newID, lowerBound, upperBound, warningLog)
        offsetAfterBeautify = Helpers.getSiteIDOffset(newID, fullDownstreamID)
        story = "Only found a downstream site (" + downstreamSiteID + "). New site is based on downstream site while allowing space for " + str(offsetAfterBeautify) + " sites between downstream site and new site"
        
        if debug is True:
            print("found downstream, but not upstream")
            print("downstream siteID is " + str(downstreamSiteID))
            streamGraph.visualize(customPoints=[snappedPoint])
            SnapSites.visualize(baseData, [])
    else:
        # get huge radius of sites:
        sitesInfo = GDALData.loadSitesFromQuery(lat, lng, 30)
        if Failures.isFailureCode(sitesInfo):
            warningLog.addWarning(WarningLog.HIGH_PRIORITY, sitesInfo)
            return getResults()
        
        sites = []
        for site in sitesInfo:
            siteNumber = site["properties"]["site_no"]
            sitePoint = site["geometry"]["coordinates"]
            fastDistance = Helpers.fastMagDist(sitePoint[0], sitePoint[1], point[0], point[1])
            sites.append((siteNumber, sitePoint, fastDistance))
        
        sortedSites = sorted(sites, key=lambda site: site[2])

        oppositePairA = None
        oppositePairB = None
        foundOppositePair = False
        i = 1
        while foundOppositePair is False:
            curSite = sortedSites[i]
            curPartCode = curSite[0][:2]
            curSitePoint = curSite[1]
            curDirection = Helpers.normalize(curSitePoint[0] - point[0], curSitePoint[1] - point[1])
            for cmpSite in sortedSites[:i]:
                cmpSitePoint = cmpSite[1]
                cmpDirection = Helpers.normalize(cmpSitePoint[0] - point[0], cmpSitePoint[1] - point[1]) 
                cmpPartCode = cmpSite[0][:2]
                dot = Helpers.dot(curDirection[0], curDirection[1], cmpDirection[0], cmpDirection[1])
                
                #check if these two directions are mostly opposite
                # dot < 0 means they are at least perpendicular
                if dot < 0.4 and curPartCode == cmpPartCode:
                    foundOppositePair = True
                    oppositePairA = cmpSite
                    oppositePairB = curSite
            i += 1
        
        partCode = oppositePairA[0][:2]

        fullIDA = Helpers.getFullID(oppositePairA[0])
        fullIDB = Helpers.getFullID(oppositePairB[0])

        dsnA = int(fullIDA[2:])
        dsnB = int(fullIDB[2:])

        distA = oppositePairA[2]
        distB = oppositePairB[2]

        totalAddressSpaceDistance = distA + distB
        newSitePercentage = distA / totalAddressSpaceDistance

        newDsn = int(dsnA * (1 - newSitePercentage) + dsnB * newSitePercentage)

        newID = Helpers.buildFullID(partCode, newDsn)
        newID = beautifyID(newID, fullIDA, fullIDB, warningLog)

        story = "Could not find any sites on the network. Estimating based on " + oppositePairA[0] + " and " + oppositePairB[0] + "."
        
        if debug:
            print("no sites found nearby. Estimating new ID based on nearby sites")
            print ("new estimate based on " + oppositePairA[0] + " and " + oppositePairB[0])
            print ("estimation is " + newID)
            streamGraph.visualize()
            SnapSites.visualize(baseData, [])

    return getResults(siteID = newID, story = story) 

def beautifyID (siteID, lowerBound, upperBound, warningLog):
    siteID = str(siteID)
    shortenedID = siteID[:7]
    DSN = int(Helpers.getFullID(siteID)[2:])
    partCode = siteID[:2]

    lowerBoundDSN = int(Helpers.getFullID(lowerBound)[2:])
    upperBoundDSN = int(Helpers.getFullID(upperBound)[2:])
    
    roundingPrecisions = [100, 50, 20, 10, 5, 2, 1]

    #now check if this number exists already
    idsInfo = GDALData.getSiteIDsStartingWith(shortenedID)
    if Failures.isFailureCode(idsInfo):
        warningLog.addWarning(WarningLog.LOW_PRIORITY, "Cannot verify if this site number already exists. Ensure this step is manually completed.")
        return siteID
    
    siteLayer = idsInfo

    existingNumbers = set()
    for site in siteLayer:
        siteNumber = site["proprties"]["site_no"]
        existingNumbers.add(siteNumber)
    
    for roundTo in roundingPrecisions:
        roundedDSN = Helpers.roundTo(DSN, roundTo)
        fullRounded = Helpers.buildFullID(partCode, roundedDSN)
        if fullRounded not in existingNumbers and Helpers.betweenBounds(roundedDSN, lowerBoundDSN, upperBoundDSN):
            return Helpers.shortenID(fullRounded)

    #if we haven't returned yet we have a problem.
    idMinusExtension = siteID[:8]

    #as a last ditch effort, try all extensions to find one that's unique
    if len(existingNumbers) > 0:
        #if the ID we want is taken, try all possible extensions until one is free
        for i in range(0, 100):
            testExtension = str(i)

            if len(testExtension) == 1:
                testExtension = "0" + testExtension

            testNewID = idMinusExtension + testExtension

            testNewDSN = int(testNewID[2:])

            if testNewID not in existingNumbers and Helpers.betweenBounds(testNewDSN, lowerBoundDSN, upperBoundDSN):
                return testNewID
    
    warningLog.addWarning(WarningLog.MED_PRIORITY, "Failed to find gap in ID space for new ID. This ID already exists.")
    return siteID    

if __name__ == "__main__":

    arguments = sys.argv[1]

    lat,lng = arguments.split(",")

    lat = float(lat)
    lng = float(lng)

    dictResults = getSiteID(lat, lng)

    print (json.dumps(dictResults))

    """ if Failures.isFailureCode(siteInfo):
        res = {'Results': str(siteInfo), 'Story': "Could not produce story.", 'Log': ""}
        results = json.dumps(res)
        print(results)
    else:
        res = {'Results': str(siteInfo[0]), 'Story': str(siteInfo[1])}
        results = json.dumps(res)
        print(results) """
