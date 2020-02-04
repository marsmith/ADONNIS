#!/usr/bin/python3.6


from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdal_array
from osgeo import gdalconst
import sys
import json
import os

os.environ['GDAL_DATA'] = 'C:/Users/marsmith/miniconda/envs/adonnis/Library/share/gdal'
os.environ['PROJ_LIB'] = 'C:/Users/marsmith/miniconda/envs/adonnis/Library/share/proj'

def Namer(placeName, State, distance, GNIS_Name, mouthOrOutlet, cardinalDir, folderPath, siteLayerName):
    beg = []
    if mouthOrOutlet != "":
        beg.append("Near " + mouthOrOutlet + " of " + GNIS_Name)
    beg.append(GNIS_Name)
        
    dis = []
    if distance <= 1:
        dis.append("at")
        dis.append("near")
        if "north" in cardinalDir:
            dis.append("above")
        if "south" in cardinalDir:
            dis.append("below")
        dis.append(cardinalDir + " of")
        dis.append(str(round(distance,2)) + " miles " + cardinalDir + " of")

    else:
        dis.append("near")
        if "north" in cardinalDir:
            dis.append("above")
        if "south" in cardinalDir:
            dis.append("below")
        dis.append(cardinalDir + " of")
        dis.append(str(round(distance, 2)) + " miles " + cardinalDir + " of")
    
    end = placeName + ", " + State

    possibilities = []
    for b in beg:
        for d in dis:
            possibilities.append(str(b) + " " + str(d) + " " + str(end))

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
    
    if poss == None:
        return ["Found nothing"]
    return poss
a = sys.argv[1]
k = a.split(",")
pos = Namer(k[0], k[1], float(k[2]), k[3], k[4], k[5], "../data/", "ProjectedSites")

res = {'Results':pos}
results = json.dumps(res)
print(results)

 