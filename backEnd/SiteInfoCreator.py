from StreamGraphNavigator import StreamGraphNavigator, isFailureCode, QUERY_FAILURE_CODE
from StreamGraph import StreamGraph
from SnapSites import snapPoint, SnapablePoint
import GDALData

#how many queries will we try AFTER finding a single upstream/downstream site to find the other upstream/downstream site?
MAX_SECONDARY_SITE_QUERIES = 10

def getSiteID (lat, lng, withheldSites = [], debug = False):
    streamGraph = StreamGraph(withheldSites = withheldSites)

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
    segmentID = snapInfo[0].featureObjectID
    distAlongSegment = snapInfo[0].distAlongFeature
    #get the segment ID of the snapped segment
    graphSegment = streamGraph.getCleanedSegment(segmentID)

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
            streamGraph.visualize(customPoints=[point])
        return newSiteID

    else:
        if debug is True:
            streamGraph.visualize(customPoints=[point])
        return "edge case"


