from backEnd.StreamGraphNavigator import StreamGraphNavigator
from backEnd.StreamGraph import StreamGraph
from backEnd.SnapSites import snapPoint
from backend.GDALData import GDALData, QUERYDATA


def getSiteID (lat, lng):
    streamGraph = StreamGraph()

    #typically lat/long are switched to fit the x/y order paradigm 
    point = (lng, lat)
    gdalData = GDALData(point[0], point[1], loadMethod = QUERYDATA)
    streamGraph.expand(point)

    (snappedPoint, distAlongSegment) = snapPoint(point, gdalData)

    navigator = StreamGraphNavigator(streamGraph)

    upstreamSite = navigator.getNextUpstreamSite()

    
