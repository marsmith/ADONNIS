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

    #upstreamSite = navigator.getNextUpstreamSite(graphSegment, distAlongSegment)
    downstreamSite = navigator.getNextDownstreamSite(graphSegment, distAlongSegment)
    print ("down stream site = " + str(downstreamSite))
    queryPt = graphSegment.getPointOnSegment(distAlongSegment)
    
    streamGraph.visualize(showSegInfo = True, customPoints=[queryPt])

    #turn upstreamSite[0]

