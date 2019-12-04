from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdal_array
from osgeo import gdalconst
import sys
import json

def Namer(placeName, State, distance, GNIS_Name, mouthOrOutlet, cardinalDir, folderPath, siteLayerName):
    beg = ""
    if mouthOrOutlet != "":
        beg = "Near " + mouthOrOutlet + " of " + GNIS_Name
    else:
        beg = GNIS_Name
        
    dis = []
    if distance <= 1:
        dis.append("at")
        dis.append("near")
        if "north" in cardinalDir:
            dis.append("above")
        if "south" in cardinalDir:
            dis.append("below")
        dis.append(cardinalDir + " of")
        dis.append(str(int(distance)) + " miles " + cardinalDir + " of")
        dis.append(str(distance) + " miles " + cardinalDir + " of")

    else:
        dis.append("near")
        if "north" in cardinalDir:
            dis.append("above")
        if "south" in cardinalDir:
            dis.append("below")
        dis.append(cardinalDir + " of")
        dis.append(str(int(distance)) + " miles " + cardinalDir + " of")
        dis.append(str(round(distance, 2)) + " miles " + cardinalDir + " of")
    
    end = placeName + ", " + State

    possibilities = [str(beg) + " " + str(i) + " " + str(end) for i in dis]

    poss = sorted(possibilities, key = len)

    path_sites = str(folderPath) + "/" + str(siteLayerName) + "/" + str(siteLayerName) + ".shp"
    sitesDataSource = ogr.Open(path_sites)
    sl = sitesDataSource.GetLayer()
    siteName_index = sl.GetLayerDefn().GetFieldIndex("station_nm")
    for s in sl:
        name = s.GetFieldAsString(siteName_index)
        for p in poss:
            if p == name:
                poss.remove(p)
    
    return poss

a = sys.argv[1]
k = a.split(",")
pos = Namer(k[0], k[1], float(k[2]), k[3], k[4], k[5], "../data/", "ProjectedSites")

res = {'Results':pos}
results = json.dumps(res)
print(results)

 