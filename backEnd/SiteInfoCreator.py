from StreamGraphNavigator import StreamGraphNavigator
from StreamGraph import StreamGraph
from SnapSites import snapPointToSegment
from GDALData import GDALData, QUERYDATA


def getSiteID (lat, lng):
    streamGraph = StreamGraph()

    #typically lat/long are switched to fit the x/y order paradigm 
    point = (lng, lat)
    gdalData = GDALData(lat, lng, loadMethod = QUERYDATA)
    streamGraph.addGeom(gdalData)
    streamGraph.visualize()
    snapInfo = snapPointToSegment(point, gdalData)
    if snapInfo is None:
        print ("could not snap")
        return None
    (segmentID, distAlongSegment) = snapInfo
    graphSegment = streamGraph.getCleanedSegment(segmentID)

    navigator = StreamGraphNavigator(streamGraph)

    upstreamSite = navigator.getNextUpstreamSite(graphSegment, distAlongSegment)
    downstreamSite = navigator.getNextDownstreamSite(graphSegment, distAlongSegment)

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

    print ("New Site ID = " + newSiteID)
    queryPt = graphSegment.getPointOnSegment(distAlongSegment)
    
    streamGraph.visualize(showSegInfo = True, customPoints=[queryPt])
    print("test")
    #turn upstreamSite[0]

