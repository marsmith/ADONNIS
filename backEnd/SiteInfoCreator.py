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

#how many queries will we try AFTER finding a single upstream/downstream site to find the other upstream/downstream site?
MAX_PRIMARY_QUERIES = 30
MAX_SECONDARY_SITE_QUERIES = 5
#what's the smallest reasonable distance between two sites
#according to Gary Wall this is 500 feet 
#rounding down to be safe, we get 100 meters 
MIN_SITE_DISTANCE = 0.1 #kilometers 


#withheld sites is a list of sites to be ignored while calculating a new site

def getSiteID (lat, lng, withheldSites = [], debug = False):
    warningLog = WarningLog.WarningLog(lat, lng)

    streamGraph = StreamGraph(withheldSites = withheldSites, debug = debug, warningLog = warningLog)
    siteIDManager = SiteIDManager()

    #typically lat/long are switched to fit the x/y order paradigm 
    point = (lng, lat)
    #get data around query point and construct a graph
    baseData = GDALData.loadFromQuery(lat, lng)

    def getResults (siteID = "unknown", story = "See warning log"):
        results = dict()
        results["id"] = siteID
        results["story"] = story
        results["log"] = warningLog.getFormattedMessage()
        return results

    if Failures.isFailureCode(baseData):
        if debug is True:
            print ("could not get data")
        warningLog.addWarning(WarningLog.FATAL_ERROR, baseData)
        return getResults()

    streamGraph.addGeom(baseData)

    #snap query point to a segment
    snapablePoint = SnapablePoint(point = point, name = "", id = "")
    snapInfo = snapPoint(snapablePoint, baseData) #get the most likely snap
    if Failures.isFailureCode(snapInfo):
        if debug is True:
            print ("could not snap")
        warningLog.addWarning(WarningLog.FATAL_ERROR, snapInfo)
        return getResults()

    feature = snapInfo[0].feature
    objectIDIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")
    segmentID = feature.GetFieldAsString(objectIDIndex)
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


    story = ""
    newID = ""

    if upstreamSite is not None and downstreamSite is not None:
        #we have an upstream and downstream

        upstreamSiteID = upstreamSite[0]
        downstreamSiteID = downstreamSite[0]
        partCode = upstreamSiteID[0:2]

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

        newID = partCode + str(newDon)
        story = "Found an upstream site (" + upstreamSiteID + ") and a downstream site (" + downstreamSiteID + ")"

        if debug is True:
            print ("found upstream is " + upstreamSiteID)
            print ("found downstream is " + downstreamSiteID)
            streamGraph.visualize(customPoints=[snappedPoint])
            SnapSites.visualize(baseData, [])
        
    elif upstreamSite is not None:
        upstreamSiteID = upstreamSite[0]
        partCode = upstreamSiteID[:2]
        fullUpstreamID = Helpers.getFullID(upstreamSiteID)

        upstreamSiteDSN = int(fullUpstreamID[2:])
        upstreamSiteDistance = upstreamSite[1]

        siteIDOffset = math.ceil(upstreamSiteDistance / MIN_SITE_DISTANCE)

        newSiteIDDSN = upstreamSiteDSN + siteIDOffset
        
        newID = partCode + str(newSiteIDDSN)
        story = "Only found a upstream site (" + upstreamSiteID + "). Allowing space for " + siteIDOffset + "sites between upstream site and new site"
        
        if debug is True:
            print("found upstream, but not downstream")
            print("upstream siteID is " + str(upstreamSiteID))
            streamGraph.visualize(customPoints=[snappedPoint])
            SnapSites.visualize(baseData, [])

    elif downstreamSite is not None:
        downstreamSiteID = downstreamSite[0]
        partCode = downstreamSiteID[:2]
        fullDownstreamID = Helpers.getFullID(downstreamSiteID)

        downstreamSiteDSN = int(fullDownstreamID[2:])
        downstreamSiteDistance = downstreamSite[1]

        siteIDOffset = math.ceil(downstreamSiteDistance / MIN_SITE_DISTANCE)

        newSiteIDDSN = downstreamSiteDSN - siteIDOffset
        
        newID = partCode + str(newSiteIDDSN)
        story = "Only found a downstream site (" + downstreamSiteID + "). Allowing space for " + siteIDOffset + "sites between downstream site and new site"
        
        if debug is True:
            print("found downstream, but not upstream")
            print("downstream siteID is " + str(downstreamSiteID))
            streamGraph.visualize(customPoints=[snappedPoint])
            SnapSites.visualize(baseData, [])
    else:
        # get huge radius of sites:
        sitesInfo = GDALData.loadSitesFromQuery(lat, lng, 30)
        if Failures.isFailureCode(sitesInfo):
            warningLog.addWarning(WarningLog.FATAL_ERROR, sitesInfo)
            return getResults()

        siteLayer, siteDatasource = sitesInfo
        siteNumberIndex = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
        
        sites = []
        for site in siteLayer:
            siteNumber = site.GetFieldAsString(siteNumberIndex)
            sitePoint = site.GetGeometryRef().GetPoint(0)
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

        newID = str(partCode) + str(newDsn)
        # we shorten the ID to get all of the site IDs including various 2 digit extensions already used
        newIDShortened = newID[:8]

        #now check if this number exists already
        idsInfo = GDALData.getSiteIDsStartingWith(newIDShortened)
        if Failures.isFailureCode(idsInfo):
            warningLog.addWarning(WarningLog.FATAL_ERROR, idsInfo)
            return getResults()
        siteLayer, siteDataSource = idsInfo
        foundGap = False
        existingNumbers = []
        for site in siteLayer:
            siteNumber = site.GetFieldAsString(siteNumberIndex)
            existingNumbers.append(siteNumber)
        
        if len(existingNumbers) > 0:
            #if the ID we want is taken, try all possible extensions until one is free
            for i in range(0, 100):
                testExtension = str(i)

                if len(testExtension) == 1:
                    testExtension = "0" + testExtension

                testNewID = newIDShortened + testExtension
                if testNewID not in existingNumbers:
                    newID = testNewID
                    foundGap = True
                    break
        if not foundGap:
            warningLog.addWarning(WarningLog.FATAL_ERROR, Failures.NO_SITEID_GAP_CODE)
            return getResults()

        story = "Could not find any sites on the network. Estimating based on " + oppositePairA[0] + " and " + oppositePairB[0] + "."
        
        if debug:
            print("no sites found nearby. Estimating new ID based on nearby sites")
            print ("new estimate based on " + oppositePairA[0] + " and " + oppositePairB[0])
            print ("estimation is " + newID)
            streamGraph.visualize()
            SnapSites.visualize(baseData, [])

    return getResults(siteID = newID, story = story)  

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
