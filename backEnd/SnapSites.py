from GDALData import *
import matplotlib.pyplot as plt
""" 
class SnapSite(object):
    def __init__(self, maxSnapDist):
        #the assumed farthest distance between a site and its coorisponding snapped location
        self.maxSnapDist = maxSnapDist
 """

maxSnapDist = 3
def Snap(gdalData):
    print("snap")
    siteLayer = gdalData.siteLayer
    lineLayer = gdalData.lineLayer
    siteLayer.ResetReading()
    for site in siteLayer:
        lineLayer.ResetReading()

        geomRef = site.GetGeometryRef()
        buffer = geomRef.Buffer(maxSnapDist)
        test1 = 0
        for line in lineLayer:
            test1 += 1
        lineLayer.SetSpatialFilter(buffer)
        test2 = 0
        for line in lineLayer:
            test2 += 1
        
        #print("test1 = " + str(test1))
        #print(test2)
        lineLayer.SetSpatialFilter(None)

def visualize (gdalData):
    siteLayer = gdalData.siteLayer
    lineLayer = gdalData.lineLayer
    

    lineLayer.ResetReading()
    for line in lineLayer:
        geom = line.GetGeometryRef()
        numPoints = geom.GetPointCount()
        x = []
        y = []
        for i in range(0, numPoints):
            p = geom.GetPoint(i)
            x.append(p[0])
            y.append(p[1])

        plt.plot(x, y, linewidth=1, color='blue')

    siteLayer.ResetReading()
    x = []
    y = []
    for site in siteLayer:
        geom = site.GetGeometryRef()
        x.append(geom.GetPoint(0)[0])
        y.append(geom.GetPoint(0)[1])
    plt.scatter(x,y, color='red')


    plt.show()



x = -74.3254918    #Long Lake
y =  44.0765791
a = [x,y]
gdalData = GDALData()
attempts = 3
gdalData.loadFromQuery(y, x, attempts)
#gdalData.loadFromData()
Snap(gdalData)
visualize(gdalData)