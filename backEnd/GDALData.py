#Ian Scilipoti
#Feb, 5th, 2020
import requests
import os
from collections import namedtuple
import xml.etree.ElementTree as ET
import json
import math
import Helpers
import sys
import Failures


MAX_SAFE_QUERY_DIST_KM = 3.5

BaseData = namedtuple('BaseData', 'lineLayer siteLayer dataBoundary')
""" The core data needed for StreamGraph. """
PointOfContext = namedtuple('PointOfContext', 'distance point name')
""" A place that can be used as context for a site name. """
DataBoundary = namedtuple('DataBoundary', 'point radius')
""" The boundary around some queried data. """

RESTRICTED_FCODES = [56600]

ALLOWED_SITE_TYPES = ["OC","OC-CO","ES","LK","ST","ST-CA","ST-DCH","ST-TS","AT","WE","SP"]

QUERY_ATTEMPTS = 10 
# the distance in km around a queried data radius that we consider the data 
# to be safe from edge effects
DATA_PADDING = 0.6
TIMEOUT = 6


def queryWithAttempts (url, attempts, timeout = 3, queryName="data"):
    """ generic way to query a service with multiple attempts and individual timeout. 
        Mainly usful because of how unreliable NHD requests seem to be.
        
        :param attempts: How many attempts before returning QUERY_FAILURE_CODE.  
        :param timeout: How much time should each attempt be given. 
        :param queryName: A name associated with this request. Used in generating print warnings.

        :return: Response text or a Failure code. """
    attemptsUsed = 0
    success = False
    while (attemptsUsed < attempts):
        try:
            req = requests.get(url, timeout=timeout)
            success = True
            if __debug__:
                print("queried " + queryName + " successfully!")
            return req
        except:
            attemptsUsed += 1
            if __debug__:
                print("failed to retrieve " + queryName + " on attempt " + str(attemptsUsed) + ". Trying again")
    if success == False:
        if __debug__:
            print("failed to retrieve " + queryName + " on all attempts. Failing")
        return Failures.QUERY_FAILURE_CODE

def getNearestPlace (lat, lng, timeout = 5):
    """ Get's the nearest location information. 

    :param lat: Latitude of request
    :param lng: Longitude of request
    :param timeout: Request timeout before failure code is returned

    :return: A tuple with the following information (distance, town/place name, state code) """

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
    """ Get's nearby bridges and river-road crossings. Used to generate names. 
    
    :param lat: Latitude of request
    :param lng: Longitude of request
    :param timeout: Request timeout before failure code is returned
    
    :return: A list of PointOfContext instances for nearby bridges and river-road crossings. """
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

def buildGeoJson (xmlStr):
    """ Converts the xml response from NWIS to GeoJson
    
    :param xml: An XML string from an NWIS site service.
    
    :return: The formatted GeoJson representation of the xml. """
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
            hucCode = site.find('huc_cd').text

            #make sure this is a stream not a well. Well sites have 14 digits
            if siteType in ALLOWED_SITE_TYPES and len(siteNo) < 13:
                #build feature. This is based on the format of the geoJson returned from the streams query
                feature = {
                    "type":"Feature",
                    "geometry":{
                        "type": "Point",
                        "coordinates": [siteLng, siteLat]
                    },
                    "properties": {
                        "site_no":siteNo,
                        "station_nm":stationNm,
                        "huc_cd":hucCode
                    }
                }
                geojson["features"].append(feature)
    return json.dumps(geojson)
 
def getSiteIDsStartingWith (siteID, timeout = TIMEOUT):
    """ Get a list of siteIDs that start with a string of digits
    
    :param siteID: A partial or complete siteID string
    
    :return: A list of GeoJson formatted siteIDs"""
    similarSitesQuery = "https://waterdata.usgs.gov/nwis/inventory?search_site_no=" + siteID + "&search_site_no_match_type=beginning&site_tp_cd=ST&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&column_name=huc_cd&list_of_search_criteria=search_site_no%2Csite_tp_cd"
    result = queryWithAttempts (similarSitesQuery, QUERY_ATTEMPTS, timeout = timeout, queryName="similarSiteIds")
    
    if Failures.isFailureCode(result):
        return result

    geoJsonResults = buildGeoJson(result.text)
    try:
        sitesLayer = json.loads(geoJsonResults)["features"]
    except:
        if __debug__:
            print("could not read query")
        return Failures.QUERY_PARSE_FAILURE_CODE
    return (sitesLayer)  

def loadHUCSites (code):
    """ Loads all sites from specified hydraulic unit code.
    
    :param code: The HUC code.
    
    :return: A list of siteIDs. """
    siteURL = "https://waterservices.usgs.gov/nwis/site/?format=mapper&huc=" + code + "&siteType=ST&siteStatus=all"
    req = queryWithAttempts(siteURL, QUERY_ATTEMPTS, queryName="siteData", timeout = TIMEOUT)
    returnList = []
    try:
        root = ET.fromstring(req.text)
        allSites = root.find('sites')
        for site in allSites:
            siteID = site.attrib['sno']

            if len(siteID) <= 10:
                returnList.append(siteID)

    except:
        return Failures.QUERY_PARSE_FAILURE_CODE
    return returnList

def loadSitesFromQuery (lat, lng, radiusKM = 5):
    """ Gets sites from NWIS within a certain radius. 

    :param lat: Latitude of request.
    :param lng: Longitude of request.
    :param radiusKM: Radius of sites to request in KM.

    :return: A list of GeoJson formatted sites. 
    """
    approxRadiusInDeg = Helpers.approxKmToDegrees(radiusKM)
    #northwest
    nwLat = lat + approxRadiusInDeg
    nwLng = lng + approxRadiusInDeg
    #southeast
    seLat = lat - approxRadiusInDeg
    seLng = lng - approxRadiusInDeg

    siteURL = "https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=" + str(nwLng) + "&nw_latitude_va=" + str(nwLat) + "&se_longitude_va=" + str(seLng) + "&se_latitude_va=" + str(seLat) + "&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=huc_cd&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box"
    req = queryWithAttempts(siteURL, QUERY_ATTEMPTS, queryName="siteData", timeout = TIMEOUT)
    if Failures.isFailureCode(req):
        return req

    xmlSites = req.text#this query returns an xml. Have to conver to geoJson
    geoJsonSites = buildGeoJson(xmlSites)
    try:
        jsonSites = json.loads(geoJsonSites)
        return jsonSites["features"]
    except:
        if __debug__:
            print("could not read query")
        return Failures.QUERY_PARSE_FAILURE_CODE

def loadFromQuery(lat, lng, radiusKM = 3.5):
    """ This function gets the core data needed to construct a stream graph. It wraps loadSitesFromQuery().
    
    :param lat: Latitude of request.
    :param lng: Longitude of request.
    :param radiusKM: Radius of sites to request in KM.

    :return: A BaseData instance.
    """
    if radiusKM > MAX_SAFE_QUERY_DIST_KM:
        raise RuntimeError("Queries with radii greater than " + str(MAX_SAFE_QUERY_DIST_KM) + " may cause data loss due to webserver limitations")

    outProjectionCode = 4326

    lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query?geometry=" + str(lng) + "," + str(lat) + "&outFields=GNIS_NAME%2C+LENGTHKM%2C+STREAMLEVE%2C+FCODE%2C+OBJECTID%2C+ARBOLATESU&geometryType=esriGeometryPoint&inSR=4326&outSR=" + str(outProjectionCode) + "&distance=" + str(radiusKM*1000) + "&units=esriSRUnit_Meter&returnGeometry=true&f=geojson"
    req = queryWithAttempts(lineURL, QUERY_ATTEMPTS, queryName="lineData", timeout = TIMEOUT)
    
    if Failures.isFailureCode(req):
        if __debug__:
            print("could not read query")
        return req
    try:
        lineLayer = json.loads(req.text)["features"]
    except:
        if __debug__:
            print("could not read query")
        return Failures.QUERY_PARSE_FAILURE_CODE
    
    if len(lineLayer) == 0:
        return Failures.EMPTY_QUERY_CODE

    sites = loadSitesFromQuery(lat, lng, radiusKM)
    
    if Failures.isFailureCode(sites):
        return sites
    
    dataBoundary = DataBoundary(point=(lng, lat), radius = Helpers.approxKmToDegrees(radiusKM - DATA_PADDING))

    data = BaseData(lineLayer = lineLayer, siteLayer = sites, dataBoundary = dataBoundary)

    return data