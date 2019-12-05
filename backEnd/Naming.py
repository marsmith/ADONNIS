#!/usr/bin/python3.6


from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdal_array
from osgeo import gdalconst
import os


def recommendName(folderPath,sitefileName,datapack={"placeName":None,"placeNameState":None,\
                    "distanceWord":None,"distanceNumber":None,"GNIS_NAME":None}):
    path = folderPath + "/" + sitefileName + "/" + sitefileName + ".shp"
    sitesDataSource = ogr.Open(path_sites)
    sl = sitesDataSource.GetLayer()
    siteNumber_index = sl.GetLayerDefn().GetFieldIndex("site_no")
    siteName_index = sl.GetLayerDefn().GetFieldIndex("station_nm")

    try:
        waterName = datapack["GNIS_NAME"]   
        if waterName is None:
            raise Exception("GNIS_NAME not provided. Using Unnamed Trib instead")     
    except:
        waterName = "Unnamed Trib"
    try:
        distanceWord = datapack["distanceWord"]
        if distanceWord is None:
            raise Exception("distanceWord not provided. Using Unnamed Trib instead")
    except :
        distanceWord = "In Vicinity of"

    try:
        placeNameState = datapack["placeNameState"]
        if placeNameState is None:
            raise Exception("State not provided. Improvising!")
    except:
        placeNameState = "USA"
    
    try:
        placeName = datapack["placeName"]
        if placeName is None:
            raise Exception("recommendName() [Error]: No place name for reference provided!")
    except:
        return "Unknown Site"
    
    tries = 0
    recommendedName = "{0} {1} {2} {3}".format(waterName,distanceWord,placeNameState,placeNameState)  
    recomendations = []; recomendations.append(recommendedName)

    while tries < 99:
        for site in sl:
            siteName = site.GetFieldAsString(siteName_index)
            i = 0
            while i < len(recomendations):           
                if siteName == recomendations[i]:
                    # Lets try other recomendations
                    recomendations.pop(i)
                    rec1 = "{0} {1} {2} {3}".format(waterName,str(distanceWord[0]) + str(distanceWord[len(distanceWord - 1)]),placeNameState,placeNameState)
                else:
                    i += 1
            
            
