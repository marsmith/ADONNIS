from GDALData import GDALData, MANUAL, LOCALDATA, QUERYDATA
from osgeo import gdalconst
from StreamGraph import *
from StreamGraphNavigator import *



#x = -74.3254918    #Long Lake
#y =  44.0765791
x = -74.1042838
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

graphNav = StreamGraphNavigator(graph)

while True:
    segID = input("enter a edge segmentID: ")
    try:
        segment = graph.segments[segID]
    except:
        print("couldn't find that segment, try again")
        continue
    segLen = round(segment.length, 2)
    print ("the length of that segment is " + str(segLen))
    segPosition = input("enter position on that segment between 0-" + str(segLen) + ": ")

    #upstreamSiteInfo = graph.getNextUpstreamSite(segment, float(segPosition))
    upstreamSiteInfo = graphNav.getNextUpstreamSite(segment, float(segPosition))
    if upstreamSiteInfo is not None:
        print ("Success! the nearest upstream site is " + str(upstreamSiteInfo[0]) + ". It is " + str(upstreamSiteInfo[1]) + " kilometers upstream along tribs. \n")
    else:
        print ("Could not find site upstream")
    graph.visualize()
#edge = graph.segments[180058818269073]
#foundEdge = graph.getNextUpstreamSiteID(edge, edge.length)
#print (str(edge.segmentID) + " site is " + str(foundEdge))
#graph.addGeom(data2)
#graph.addGeom(data3)


#graph.addGeom(data2)
