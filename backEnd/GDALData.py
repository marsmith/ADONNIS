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

#This class provides a generic way of passing around data
#New instances of GDALData can be generated either from online query or via local data storage. 

LINE_FOLDER_NAME = "NHDFlowline_Project_SplitLin3"
SITES_FOLDER_NAME = "ProjectedSites"
MAX_SAFE_QUERY_DIST_KM = 7

MANUAL = 0
LOCALDATA = 1
QUERYDATA = 2

RESTRICTED_FCODES = [56600]



class GDALData(object):


    def __init__(self, lat, lng, radiusKM = 5, loadMethod = MANUAL, queryAttempts = 10, dataPaddingKM = 0.6, timeout = 2, projectCoords = False):
        self.localPath = os.path.join( os.path.dirname(os.path.dirname( __file__ ))) + "\data"
        self.lineDataSource = None
        self.siteDataSource = None
        self.lineLayer = None
        self.siteLayer = None

        self.lat = lat
        self.lng = lng
        self.radiusKM = radiusKM
        self.queryAttempts = queryAttempts
        self.dataPaddingKM = dataPaddingKM
        self.safeDataBoundary = None

        self.timeout = timeout

        self.utmCode = self.getUTM(self.lng)
        self.EPSGCode = int("269" + str(self.utmCode))
        self.projectCoords = projectCoords

        if loadMethod == LOCALDATA:
            self.loadFromData()
        if loadMethod == QUERYDATA:
            self.loadFromQuery()
        if loadMethod == MANUAL:
            print("this GDALDATA object will not automatically load data. Call loadFromData or loadFromQuery")
    
    def getTransformation (self):
        worldRef = osr.SpatialReference()
        worldRef.ImportFromEPSG(4326)

        stateRef = osr.SpatialReference()
        stateRef.ImportFromEPSG(self.EPSGCode) #projection from UTM zone of the current lat/lng
        return osr.CoordinateTransformation(worldRef,stateRef)

    def loadFromData (self):
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
        self.siteLayer.SetSpatialFilter(dataBuffer)

    def getUTM (self, long):
        return (math.floor((long + 180)/6) % 60) + 1

    def queryWithAttempts (self, url, attempts, timeout = 3, queryName="data"):
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

    def buildGeoJson (self, xmlStr):
        transformation = self.getTransformation()
        root = ET.fromstring(xmlStr)
        geojson = {
            "type": "FeatureCollection",
            "crs": {"type":"name","properties":{"name":"EPSG:" + str(self.EPSGCode)}},
            "features":[]
        }
        #check for no sites case
        if "no sites found" not in xmlStr:
            for site in root:
                siteNo = int(site.find('site_no').text)
                stationNm = site.find('station_nm').text
                siteType = site.find('site_tp_cd').text
                siteLat = float(site.find('dec_lat_va').text)
                siteLng = float(site.find('dec_long_va').text)

                if self.projectCoords is True:
                    [coordX, coordY, z] = transformation.TransformPoint(siteLng, siteLat)
                else:
                    coordX = siteLng
                    coordY = siteLat

                #make sure this is a stream not a well
                if(siteType == "ST"):
                    #build feature. This is based on the format of the geoJson returned from the streams query
                    feature = {
                        "type":"Feature",
                        "geometry":{
                            "type": "Point",
                            "coordinates": [coordX, coordY]
                        },
                        "properties": {
                            "site_no":siteNo,
                            "station_nm":stationNm
                        }
                    }
                    geojson["features"].append(feature)
        return json.dumps(geojson)

    def loadFromQuery(self):

        if self.radiusKM > MAX_SAFE_QUERY_DIST_KM:
            raise RuntimeError("Queries with radii greater than " + str(MAX_SAFE_QUERY_DIST_KM) + " may cause data loss due to webserver limitations")

        transformation = self.getTransformation()
        outProjectionCode = self.EPSGCode
        if self.projectCoords is False:
            outProjectionCode = 4326 #code for global lat/lng
        #lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query?geometry=" + str(self.lng) + "," + str(self.lat) + "&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=GNIS_NAME%2C+LENGTHKM%2C+STREAMLEVE&returnGeometry=true&outSR=" + str(self.EPSGCode) + "&returnDistinctValues=false&queryByDistance=" + str(self.radiusKM*1000) + "&featureEncoding=esriDefault&f=geojson"
        lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/2/query?geometry=" + str(self.lng) + "," + str(self.lat) + "&outFields=GNIS_NAME%2C+LENGTHKM%2C+STREAMLEVE%2C+FCODE%2C+OBJECTID%2C+ARBOLATESU&geometryType=esriGeometryPoint&inSR=4326&outSR=" + str(outProjectionCode) + "&distance=" + str(self.radiusKM*1000) + "&units=esriSRUnit_Meter&returnGeometry=true&f=geojson"
        #lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query?geometry=" + str(self.lng) + "," + str(self.lat) + "&outFields=*&geometryType=esriGeometryPoint&inSR=4326&outSR=" + str(self.EPSGCode) + "&distance=" + str(self.radiusKM*1000) + "&units=esriSRUnit_Meter&returnGeometry=true&f=geojson"        
        req = self.queryWithAttempts(lineURL, self.queryAttempts, queryName="lineData", timeout = self.timeout)
        
        if req == None:
            sys.exit("FATAL: could not query stream line data")
            return None
        
        try:
            lineDataSource = gdal.OpenEx(req.text)#, nOpenFlags=gdalconst.GA_Update)
            lineLayer = lineDataSource.GetLayer()
        except:
            sys.exit("FATAL: could not read the queried json data")
            return None

        if self.lineDataSource == None:
            self.lineDataSource = lineDataSource
            self.lineLayer = lineLayer
        else:
            print(self.lineLayer.GetFeatureCount())
            print(lineLayer.GetFeatureCount())
            testLayer = lineDataSource.CreateLayer("union layer", self.lineLayer.GetSpatialRef(), ogr.wkbLineString)
            self.lineLayer.Union(lineLayer, testLayer)
            print(testLayer.GetFeatureCount())

        approxRadiusInDeg = approxKmToDegrees(self.radiusKM)

        #northwest
        nwLat = self.lat + approxRadiusInDeg
        nwLng = self.lng + approxRadiusInDeg

        #southeast
        seLat = self.lat - approxRadiusInDeg
        seLng = self.lng - approxRadiusInDeg

        siteURL = "https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=" + str(nwLng) + "&nw_latitude_va=" + str(nwLat) + "&se_longitude_va=" + str(seLng) + "&se_latitude_va=" + str(seLat) + "&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box"
        req = req = self.queryWithAttempts(siteURL, 4, queryName="siteData", timeout = self.timeout)

        if req == None:
            sys.exit("FATAL: could not query stream site data")
            return None

        xmlSites = req.text#this query returns an xml. Have to conver to geoJson
        geoJsonSites = self.buildGeoJson(xmlSites)
        try:
            siteDataSource = gdal.OpenEx(geoJsonSites)#, nOpenFlags=gdalconst.GA_Update)
            siteLayer = siteDataSource.GetLayer()
        except:
            sys.exit("FATAL: could not read the queried stream site data")
            return None

        if self.siteDataSource == None:
            self.siteDataSource = siteDataSource
            self.siteLayer = siteLayer
        else:
            self.siteLayer.Union(siteLayer, self.siteLayer)

        self.siteLayer.ResetReading()
         
        queryCenter = ogr.Geometry(ogr.wkbPoint)#up stream point - wkb point is the code for point based geometry
        
        if self.projectCoords is True:
            transformedQueryCenter = transformation.TransformPoint(self.lng, self.lat)
            queryCenter.AddPoint(transformedQueryCenter[0], transformedQueryCenter[1])
        else:
            queryCenter.AddPoint(self.lng, self.lat)

        safeDataBoundaryRad = (self.radiusKM - self.dataPaddingKM) * 1000
        if self.projectCoords is False:
            safeDataBoundaryRad = approxKmToDegrees(safeDataBoundaryRad / 1000)

        self.safeDataBoundary = queryCenter.Buffer(safeDataBoundaryRad)
