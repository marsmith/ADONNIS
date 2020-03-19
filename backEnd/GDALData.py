#Ian Scilipoti
#Feb, 5th, 2020
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdal_array
from osgeo import gdalconst
import requests
import os
from collections import namedtuple
import xml.etree.ElementTree as ET
import json
import math
from Helpers import *
import sys


LINE_FOLDER_NAME = "NHDFlowline_Project_SplitLin3"
SITES_FOLDER_NAME = "ProjectedSites"
MAX_SAFE_QUERY_DIST_KM = 7

BaseData = namedtuple('BaseData', 'lineLayer lineDS, siteLayer siteDS dataBoundary')

RESTRICTED_FCODES = [56600]

QUERY_ATTEMPTS = 10 
DATA_PADDING = 0.6
TIMEOUT = 2

def queryWithAttempts (url, attempts, timeout = 3, queryName="data"):
        attemptsUsed = 0
        success = False
        while (attemptsUsed < attempts):
            try:
                req = requests.get(url, timeout=timeout)
                success = True
                print("queried " + queryName + " successfully!")
                return req
            except requests.exceptions.ReadTimeout:
                attemptsUsed += 1
                print("failed to retrieve " + queryName + " on attempt " + str(attemptsUsed) + ". Trying again")
        if success == False:
            print("failed to retrieve " + queryName + " on all attempts. Failing")
            return None


""" def loadFromData (self):
    linesPath = self.localPath + "/" + LINE_FOLDER_NAME + "/" + LINE_FOLDER_NAME + ".shp"

    transformation = self.getTransformation()

    queryCenter = ogr.Geometry(ogr.wkbPoint)
    transformedQueryCenter = transformation.TransformPoint(self.lng, self.lat)
    queryCenter.AddPoint(transformedQueryCenter[0], transformedQueryCenter[1])
    #we want GDALData objects loaded from data to essentially act like queried data so we filter it around a query sized buffer
    dataBuffer = queryCenter.Buffer(self.radiusKM*1000)

    self.lineDataSource = ogr.Open(linesPath)
    self.lineLayer = self.lineDataSource.GetLayer() 
    self.lineLayer.SetSpatialFilter(dataBuffer)

    sitesPath = self.localPath + "/" + SITES_FOLDER_NAME + "/" + SITES_FOLDER_NAME + ".shp"   
    self.siteDataSource = ogr.Open(sitesPath)
    # we dob't really need the reference to siteDataSource, however
    # if this reference isn't saved my guess is that the data source reference is destroyed 
    # this reference is likely required for things like siteLayer.GetSpatialRef()
    self.siteLayer = self.siteDataSource.GetLayer()
    self.siteLayer.SetSpatialFilter(dataBuffer) """

#convert the xml results of a stream site query to geojson
def buildGeoJson (xmlStr):
    root = ET.fromstring(xmlStr)
    geojson = {
        "type": "FeatureCollection",
        "crs": {"type":"name","properties":{"name":"EPSG:4326"}},
        "features":[]
    }
    #check for no sites case
    if "no sites found" not in xmlStr:
        for site in root:
            siteNo = site.find('site_no').text
            stationNm = site.find('station_nm').text
            siteType = site.find('site_tp_cd').text
            siteLat = float(site.find('dec_lat_va').text)
            siteLng = float(site.find('dec_long_va').text)

            #make sure this is a stream not a well. Well sites have 14 digits
            if siteType == "ST" and len(siteNo) < 13:
                #build feature. This is based on the format of the geoJson returned from the streams query
                feature = {
                    "type":"Feature",
                    "geometry":{
                        "type": "Point",
                        "coordinates": [siteLng, siteLat]
                    },
                    "properties": {
                        "site_no":siteNo,
                        "station_nm":stationNm
                    }
                }
                geojson["features"].append(feature)
    return json.dumps(geojson)

#get site IDs similar to this site 
def getNearbyIds (siteID, minReturnedSites = 5, cutoffDigits = 6):
    numReturnedSites = 0
    while numReturnedSites < minReturnedSites:
        firstDigits = siteID[:8-cutoffDigits]#get the 8 digit number minus the number of cutoff digits
        results = getSiteIDsStartingWith(firstDigits)
        sitesLayer = results[0]
        
        numReturnedSites = sitesLayer.GetFeatureCount()
    
    return (sitesLayer, results[1])

def getSiteIDsStartingWith (siteID, timeout = TIMEOUT):
    
    similarSitesQuery = "https://waterdata.usgs.gov/nwis/inventory?search_site_no=" + siteID + "&search_site_no_match_type=beginning&site_tp_cd=ST&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=search_site_no%2Csite_tp_cd"
    result = queryWithAttempts (similarSitesQuery, QUERY_ATTEMPTS, timeout = timeout, queryName="similarSiteIds")
    geoJsonResults = buildGeoJson(result.text)
    try:
        sitesDataSource = gdal.OpenEx(geoJsonResults)#, nOpenFlags=gdalconst.GA_Update)
        sitesLayer = sitesDataSource.GetLayer()
    except:
        print("could not read query")
        return None
    return (sitesLayer, sitesDataSource)

def getSiteNeighbors (inSiteID):

    partCode = inSiteID[:2]
    firstDigit = int(inSiteID[3:4])
    (siteLayer, sitesDataSource) = getSiteIDsStartingWith(inSiteID[:4])

    siteNumberIndex = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
    previousSiteID = None
    sites = []
    matchIndex = -1
    for site in siteLayer:
        siteID = site.GetFieldAsString(siteNumberIndex)
        point = site.GetGeometryRef().GetPoint(0)
        lat = point[1]
        lng = point[0]
        sites.append((siteID, lat, lng))

        if siteID == inSiteID:
            matchIndex = len(sites) - 1
    
    if matchIndex > 0:
        lowerNeighbor = sites[matchIndex-1]
    else:
        lowerNeighbor = None
    
    if matchIndex < len(sites)-1:
        higherNeighbor = sites[matchIndex+1]
    else:
        higherNeighbor = None

    return (lowerNeighbor, higherNeighbor)

    



def loadFromQuery(lat, lng, radiusKM = 5):

    if radiusKM > MAX_SAFE_QUERY_DIST_KM:
        raise RuntimeError("Queries with radii greater than " + str(MAX_SAFE_QUERY_DIST_KM) + " may cause data loss due to webserver limitations")

    outProjectionCode = 4326

    lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query?geometry=" + str(lng) + "," + str(lat) + "&outFields=GNIS_NAME%2C+LENGTHKM%2C+STREAMLEVE%2C+FCODE%2C+OBJECTID%2C+ARBOLATESU&geometryType=esriGeometryPoint&inSR=4326&outSR=" + str(outProjectionCode) + "&distance=" + str(radiusKM*1000) + "&units=esriSRUnit_Meter&returnGeometry=true&f=geojson"
    req = queryWithAttempts(lineURL, QUERY_ATTEMPTS, queryName="lineData", timeout = TIMEOUT)
    
    if req == None:
        print("could not read query")
        return None
    try:
        lineDataSource = gdal.OpenEx(req.text)#, nOpenFlags=gdalconst.GA_Update)
        lineLayer = lineDataSource.GetLayer()
    except:
        print("could not read query")
        return None

    approxRadiusInDeg = approxKmToDegrees(radiusKM)

    #northwest
    nwLat = lat + approxRadiusInDeg
    nwLng = lng + approxRadiusInDeg

    #southeast
    seLat = lat - approxRadiusInDeg
    seLng = lng - approxRadiusInDeg

    siteURL = "https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=" + str(nwLng) + "&nw_latitude_va=" + str(nwLat) + "&se_longitude_va=" + str(seLng) + "&se_latitude_va=" + str(seLat) + "&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box"
    req = queryWithAttempts(siteURL, QUERY_ATTEMPTS, queryName="siteData", timeout = TIMEOUT)

    if req == None:
        print("could not read query")
        return None

    xmlSites = req.text#this query returns an xml. Have to conver to geoJson
    geoJsonSites = buildGeoJson(xmlSites)
    try:
        siteDataSource = gdal.OpenEx(geoJsonSites)#, nOpenFlags=gdalconst.GA_Update)
        siteLayer = siteDataSource.GetLayer()
    except:
        print("could not read query")
        return None

    siteLayer.ResetReading()
    queryCenter = ogr.Geometry(ogr.wkbPoint)#up stream point - wkb point is the code for point based geometry
    
    queryCenter.AddPoint(lng, lat)

    safeDataBoundaryRad = (radiusKM - DATA_PADDING)
    safeDataBoundaryRad = approxKmToDegrees(safeDataBoundaryRad)

    safeDataBoundary = queryCenter.Buffer(safeDataBoundaryRad)

    data = BaseData(lineLayer = lineLayer, lineDS = lineDataSource, siteLayer = siteLayer, siteDS = siteDataSource, dataBoundary = safeDataBoundary)

    return data


