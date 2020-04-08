from StreamGraphNavigator import StreamGraphNavigator, isFailureCode, QUERY_FAILURE_CODE
from StreamGraph import StreamGraph
from SnapSites import snapPoint, SnapablePoint
import SnapSites
import GDALData
from Helpers import *
from SiteIDManager import SiteIDManager
import math

#how many queries will we try AFTER finding a single upstream/downstream site to find the other upstream/downstream site?
MAX_SECONDARY_SITE_QUERIES = 5
#what's the smallest reasonable distance between two sites
#according to Gary Wall this is 500 feet 
#rounding down to be safe, we get 100 meters 
MIN_SITE_DISTANCE = 0.1 #kilometers 

def getSiteID (lat, lng, withheldSites = [], debug = False, enforceSingleSnap = False):
    streamGraph = StreamGraph(withheldSites = withheldSites)
    siteIDManager = SiteIDManager()

    #typically lat/long are switched to fit the x/y order paradigm 
    point = (lng, lat)
    #get data around query point and construct a graph
    baseData = GDALData.loadFromQuery(lat, lng)
    if baseData is None:
        print ("could not get data")
        return QUERY_FAILURE_CODE
        
    if baseData.lineLayer.GetFeatureCount() == 0:
        return QUERY_FAILURE_CODE

    streamGraph.addGeom(baseData)

    #snap query point to a segment
    snapablePoint = SnapablePoint(point = point, name = "", id = "")
    snapInfo = snapPoint(snapablePoint, baseData) #get the most likely snap
    if snapInfo is None:
        print ("could not snap")
        return None
    if len(snapInfo) > 1 and enforceSingleSnap is True:
        print ("couldn't find a single snap")
        return "tooManySnaps"
    feature = snapInfo[0].feature
    objectIDIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")
    segmentID = feature.GetFieldAsString(objectIDIndex)
    distAlongSegment = snapInfo[0].distAlongFeature
    #get the segment ID of the snapped segment
    graphSegment = streamGraph.getCleanedSegment(segmentID)

    if debug:
        streamGraph.visualize(customPoints=[point], showSegInfo = False)

    #build a navigator object
    #we want to terminate the search each time a query happens
    #this allows us to stagger upstream and downstream searches
    #although this means repeating parts of the search multiple times, searching a already constructed
    #graph takes practically no time at all
    navigator = StreamGraphNavigator(streamGraph, terminateSearchOnQuery = True)

    upstreamSite = None
    downstreamSite = None
    secondaryQueries = 0

    #each iteration extends the graph by one query worth of data
    # in this step we try to find an upstream and downstream site
    while (upstreamSite is None or downstreamSite is None) and secondaryQueries < MAX_SECONDARY_SITE_QUERIES:
        if upstreamSite is None:
            #we haven't found upstream yet
            upstreamReturn = navigator.getNextUpstreamSite(graphSegment, distAlongSegment)
            if isFailureCode(upstreamReturn) is not True and upstreamReturn is not None:
                upstreamSite = upstreamReturn

        if downstreamSite is None:
            #we haven't found downstream yet
            downstreamReturn = navigator.getNextDownstreamSite(graphSegment, distAlongSegment)
            if isFailureCode(downstreamReturn) is not True and downstreamReturn is not None:
                downstreamSite = downstreamReturn

        if upstreamSite is not None or downstreamSite is not None:
            #we've found at least one site
            secondaryQueries += 1


    if upstreamSite is not None and downstreamSite is not None:
        #we have an upstream and downstream

        upstreamSiteID = upstreamSite[0]
        downstreamSiteID = downstreamSite[0]

        partCode = upstreamSiteID[0:2]

        upstreamSiteIdDonStr = upstreamSiteID[2:]
        downstreamSiteIdDonStr = downstreamSiteID[2:]

        if len(upstreamSiteIdDonStr) < 8:
            upstreamSiteIdDonStr += "00"

        if len(downstreamSiteIdDonStr) < 8:
            downstreamSiteIdDonStr += "00"

        upstreamSiteIdDon = int(upstreamSiteIdDonStr)
        downstreamSiteIdDon = int(downstreamSiteIdDonStr)

        totalAddressSpaceDistance = upstreamSite[1] + downstreamSite[1]
        newSitePercentage = downstreamSite[1] / totalAddressSpaceDistance

        newDon = int(downstreamSiteIdDon * (1 - newSitePercentage) + upstreamSiteIdDon * newSitePercentage)

        newSiteID = partCode + str(newDon)
        if debug is True:
            print ("found upstream is " + upstreamSiteID)
            print ("found downstream is " + downstreamSiteID)
        return newSiteID
    elif upstreamSite is not None:
        upstreamSiteID = upstreamSite[0]
        partCode = upstreamSiteID[:2]
        fullUpstreamID = getFullID(upstreamSiteID)

        upstreamSiteDSN = int(fullUpstreamID[2:])
        upstreamSiteDistance = upstreamSite[1]

        siteIDOffset = math.ceil(upstreamSiteDistance / MIN_SITE_DISTANCE)

        newSiteIDDSN = upstreamSiteDSN + siteIDOffset
        
        newSiteID = partCode + str(newSiteIDDSN)

        return newSiteID
        if debug is True:
            print("found upstream, but not downstream")
            print("upstream siteID is " + str(upstreamSiteID))

    elif downstreamSite is not None:
        downstreamSiteID = downstreamSite[0]
        partCode = downstreamSiteID[:2]
        fullDownstreamID = getFullID(downstreamSiteID)

        downstreamSiteDSN = int(fullDownstreamID[2:])
        downstreamSiteDistance = downstreamSite[1]

        siteIDOffset = math.ceil(downstreamSiteDistance / MIN_SITE_DISTANCE)

        newSiteIDDSN = downstreamSiteDSN + siteIDOffset
        
        newSiteID = partCode + str(newSiteIDDSN)

        return newSiteID
        if debug is True:
            print("found downstream, but not upstream")
            print("downstream siteID is " + str(downstreamSiteID))
    else:
        return "no sites found"
        print ("no sites")