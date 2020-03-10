from GDALData import GDALData, MANUAL, LOCALDATA, QUERYDATA
from osgeo import gdalconst
from StreamGraph import *
from StreamGraphNavigator import *
from SiteInfoCreator import getSiteID



#x = -74.3254918    #Long Lake
#y =  44.0765791
""" x = -74.1042838
y = 44.1551339
x = -74.7735286
y = 42.6466516
attempts = 4

data = GDALData(y, x, loadMethod=QUERYDATA, queryAttempts = 8, timeout = 3)
#data3 = GDALData(y, x+0.2, loadMethod=QUERYDATA, queryAttempts = 8, timeout = 3)
print("--------------------------done querying")
graph = StreamGraph()
graph.addGeom(data)
graph.visualize()
42.6466516,-74.7735286
graphNav = StreamGraphNavigator(graph) """

while True:
    #segID = input("enter a edge segmentID: ")
    latLng = input("enter a lat/lng: ")

    (lat, lng) = latLng.split(",")
    lat = float(lat)
    lng = float(lng)

    """ try:
        segment = graph.segments[segID]
    except:
        print("couldn't find that segment, try again")
        continue
    segLen = round(segment.length, 2)
    print ("the length of that segment is " + str(segLen))
    segPosition = input("enter position on that segment between 0-" + str(segLen) + ": ")

    #upstreamSiteInfo = graph.getNextUpstreamSite(segment, float(segPosition))
    upstreamSiteInfo = graphNav.getNextUpstreamSite(segment, float(segPosition)) """


    siteId = getSiteID(lat, lng)

    if getSiteID is None:
        print("failed")
    else:
        print ("site is " + str(siteId))
