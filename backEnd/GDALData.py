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
import Helpers
import sys
from pathlib import Path
import Failures


STREAM_PATH = "hu4"
MAX_SAFE_QUERY_DIST_KM = 7

BaseData = namedtuple('BaseData', 'lineLayer lineDS, siteLayer siteDS dataBoundary')
PointOfContext = namedtuple('PointOfContext', 'distance point name')

RESTRICTED_FCODES = [56600]

QUERY_ATTEMPTS = 10 
# the distance in km around a queried data radius that we consider the data 
# to be safe from edge effects
DATA_PADDING = 0.6
TIMEOUT = 6

def queryWithAttempts (url, attempts, timeout = 3, queryName="data", debug = False):
    attemptsUsed = 0
    success = False
    while (attemptsUsed < attempts):
        try:
            req = requests.get(url, timeout=timeout)
            success = True
            if debug is True:
                print("queried " + queryName + " successfully!")
            return req
        except:
            attemptsUsed += 1
            if debug is True:
                print("failed to retrieve " + queryName + " on attempt " + str(attemptsUsed) + ". Trying again")
    if success == False:
        if debug is True:
            print("failed to retrieve " + queryName + " on all attempts. Failing")
        return Failures.QUERY_FAILURE_CODE

def getNearestPlace (lat, lng, timeout = 5):
    locationsUrl = "https://carto.nationalmap.gov/arcgis/rest/services/geonames/MapServer/18/query?geometry=" + str(lng) +"," + str(lat) + "&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=7000&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=geojson"
    result = queryWithAttempts(locationsUrl, QUERY_ATTEMPTS, timeout = timeout, queryName="nearPlaces")
    
    if Failures.isFailureCode(result):
        return result

    try:
        data = json.loads(result.text)
    except:
        return Failures.QUERY_PARSE_FAILURE_CODE

    features = data["features"]

    nearestFeatureDistance = sys.maxsize
    nearestFeature = None
    for feature in features:
        attrib = feature["properties"]

        point = feature["geometry"]["coordinates"][0]
        distance = Helpers.fastMagDist(point[1], point[0], lat, lng)
        if distance < nearestFeatureDistance:
            nearestFeatureDistance = distance
            nearestFeature = feature
    
    attrib = nearestFeature["properties"]
    stateAlpha = attrib["state_alpha"]
    placeName = attrib["gaz_name"]

    nearestPoint = nearestFeature["geometry"]["coordinates"][0]
    distance = Helpers.degDistance(nearestPoint[1], nearestPoint[0], lat, lng)

    return {"distanceToPlace":distance, "placeName":placeName, "state":stateAlpha}
    
def getNearestBridges (lat, lng, timeout = 5):
    locationsUrl = "https://carto.nationalmap.gov/arcgis/rest/services/geonames/MapServer/10/query?geometry=" + str(lng) +"," + str(lat) + "&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=7000&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=geojson"
    result = queryWithAttempts(locationsUrl, QUERY_ATTEMPTS, timeout = timeout, queryName="nearBridges")
    
    if Failures.isFailureCode(result):
        return result

    try:
        data = json.loads(result.text)
    except:
        return Failures.QUERY_PARSE_FAILURE_CODE

    features = data["features"]

    bridges = []
    for feature in features:
        attrib = feature["properties"]

        point = feature["geometry"]["coordinates"][0]

        distance = Helpers.degDistance(point[1], point[0], lat, lng)
        name = attrib["gaz_name"]
        bridges.append(PointOfContext(point=point, distance=distance, name=name))
    
    return bridges

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

def getSiteIDsStartingWith (siteID, timeout = TIMEOUT, debug = False):
    
    similarSitesQuery = "https://waterdata.usgs.gov/nwis/inventory?search_site_no=" + siteID + "&search_site_no_match_type=beginning&site_tp_cd=ST&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=search_site_no%2Csite_tp_cd"
    result = queryWithAttempts (similarSitesQuery, QUERY_ATTEMPTS, timeout = timeout, queryName="similarSiteIds")
    
    if Failures.isFailureCode(result):
        return result

    geoJsonResults = buildGeoJson(result.text)
    try:
        sitesDataSource = gdal.OpenEx(geoJsonResults)#, nOpenFlags=gdalconst.GA_Update)
        sitesLayer = sitesDataSource.GetLayer()
    except:
        if debug is True:
            print("could not read query")
        return Failures.QUERY_PARSE_FAILURE_CODE
    return (sitesLayer, sitesDataSource)  

def loadSitesFromQuery (lat, lng, radiusKM = 5, debug = False):
    approxRadiusInDeg = Helpers.approxKmToDegrees(radiusKM)
    #northwest
    nwLat = lat + approxRadiusInDeg
    nwLng = lng + approxRadiusInDeg
    #southeast
    seLat = lat - approxRadiusInDeg
    seLng = lng - approxRadiusInDeg

    siteURL = "https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=" + str(nwLng) + "&nw_latitude_va=" + str(nwLat) + "&se_longitude_va=" + str(seLng) + "&se_latitude_va=" + str(seLat) + "&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box"
    req = queryWithAttempts(siteURL, QUERY_ATTEMPTS, queryName="siteData", timeout = TIMEOUT)
    if Failures.isFailureCode(req):
        return req

    xmlSites = req.text#this query returns an xml. Have to conver to geoJson
    geoJsonSites = buildGeoJson(xmlSites)
    try:
        siteDataSource = gdal.OpenEx(geoJsonSites)#, nOpenFlags=gdalconst.GA_Update)
        siteLayer = siteDataSource.GetLayer()
        return (siteLayer, siteDataSource)
    except:
        if debug is True:
            print("could not read query")
        return Failures.QUERY_PARSE_FAILURE_CODE

def loadFromQuery(lat, lng, radiusKM = 5, debug = False):

    if radiusKM > MAX_SAFE_QUERY_DIST_KM:
        raise RuntimeError("Queries with radii greater than " + str(MAX_SAFE_QUERY_DIST_KM) + " may cause data loss due to webserver limitations")

    outProjectionCode = 4326

    lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query?geometry=" + str(lng) + "," + str(lat) + "&outFields=GNIS_NAME%2C+LENGTHKM%2C+STREAMLEVE%2C+FCODE%2C+OBJECTID%2C+ARBOLATESU&geometryType=esriGeometryPoint&inSR=4326&outSR=" + str(outProjectionCode) + "&distance=" + str(radiusKM*1000) + "&units=esriSRUnit_Meter&returnGeometry=true&f=geojson"
    req = queryWithAttempts(lineURL, QUERY_ATTEMPTS, queryName="lineData", timeout = TIMEOUT)
    
    if Failures.isFailureCode(req):
        if debug is True:
            print("could not read query")
        return req
    try:
        lineDataSource = gdal.OpenEx(req.text)#, nOpenFlags=gdalconst.GA_Update)
        lineLayer = lineDataSource.GetLayer()
    except:
        if debug is True:
            print("could not read query")
        return Failures.QUERY_PARSE_FAILURE_CODE
    
    if lineLayer.GetFeatureCount() == 0:
        return Failures.EMPTY_QUERY_CODE

    sites = loadSitesFromQuery(lat, lng, radiusKM)
    
    if Failures.isFailureCode(sites):
        return sites
    siteLayer = sites[0]
    siteDataSource = sites[1]

    queryCenter = ogr.Geometry(ogr.wkbPoint)#up stream point - wkb point is the code for point based geometry
    
    queryCenter.AddPoint(lng, lat)

    safeDataBoundaryRad = (radiusKM - DATA_PADDING)
    safeDataBoundaryRad = Helpers.approxKmToDegrees(safeDataBoundaryRad)

    safeDataBoundary = queryCenter.Buffer(safeDataBoundaryRad)

    data = BaseData(lineLayer = lineLayer, lineDS = lineDataSource, siteLayer = siteLayer, siteDS = siteDataSource, dataBoundary = safeDataBoundary)

    return data


#for now just loads linedata from local since line data is usually much slower
def loadFromData (lat, lng, radiusKM = 5):
    linesPath = Path(__file__).parent.absolute() / STREAM_PATH / "hu4.shp"


    queryCenter = ogr.Geometry(ogr.wkbPoint)
    queryCenter.AddPoint(lat, lng)

    degRadius = Helpers.approxKmToDegrees(radiusKM)
    #we want GDALData objects loaded from data to essentially act like queried data so we filter it around a query sized buffer
    dataBuffer = queryCenter.Buffer(radiusKM*1000)

    lineDataSource = ogr.Open(linesPath)
    lineLayer = lineDataSource.GetLayer() 
    lineLayer.SetSpatialFilter(dataBuffer)

    sites = loadSitesFromQuery(lat, lng, radiusKM)
    if Failures.isFailureCode(sites):
        return sites
    siteLayer = sites[0]
    siteDataSource = sites[1]

    return BaseData(lineLayer = lineLayer, lineDS = lineDataSource, siteLayer = siteLayer, siteDS = siteDataSource, dataBoundary = dataBuffer)