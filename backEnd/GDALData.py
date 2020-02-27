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

#This class provides a generic way of passing around data
#New instances of GDALData can be generated either from online query or via local data storage. 

LINE_FOLDER_NAME = "NHDFlowline_Project_SplitLin3"
SITES_FOLDER_NAME = "ProjectedSites"
MAX_SAFE_QUERY_DIST_KM = 7

class GDALData(object):

    def __init__(self):
        self.localPath = os.path.join( os.path.dirname(os.path.dirname( __file__ ))) + "\data"
        print("self path = " + self.localPath)
        self.lineDataSource = None
        self.siteDataSource = None
        self.lineLayer = None
        self.siteLayer = None


    def loadFromData (self):
        linesPath = self.localPath + "/" + LINE_FOLDER_NAME + "/" + LINE_FOLDER_NAME + ".shp"
        self.lineDataSource = ogr.Open(linesPath)
        self.lineLayer = self.lineDataSource.GetLayer() 
    
        sitesPath = self.localPath + "/" + SITES_FOLDER_NAME + "/" + SITES_FOLDER_NAME + ".shp"   
        self.siteDataSource = ogr.Open(sitesPath)
        # we dob't really need the reference to siteDataSource, however
        # if this reference isn't saved my guess is that the data source reference is destroyed 
        # this reference is likely required for things like siteLayer.GetSpatialRef()
        self.siteLayer = self.siteDataSource.GetLayer()

    def approxKmToDegrees (self, km):
        return (1/111) * km

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

    def buildGeoJson (self, xmlStr, EPSGCode, transformation):
      
        root = ET.fromstring(xmlStr)
        geojson = {
            "type": "FeatureCollection",
            "crs": {"type":"name","properties":{"name":"EPSG:" + str(EPSGCode)}},
            "features":[]
        }
        for site in root:
            siteNo = int(site.find('site_no').text)
            stationNm = site.find('station_nm').text
            siteType = site.find('site_tp_cd').text
            siteLat = float(site.find('dec_lat_va').text)
            siteLng = float(site.find('dec_long_va').text)

            [projX, projY, z] = transformation.TransformPoint(siteLng, siteLat)

            #make sure this is a stream not a well
            if(siteType == "ST"):
                #build feature. This is based on the format of the geoJson returned from the streams query
                feature = {
                    "type":"Feature",
                    "geometry":{
                        "type": "Point",
                        "coordinates": [projX, projY]
                    },
                    "properties": {
                        "site_no":siteNo,
                        "station_nm":stationNm
                    }
                }
                geojson["features"].append(feature)
        return json.dumps(geojson)

    def loadFromQuery(self, lat, lng, radiusKM, maxRequestAttempts):
        #Get UTM and EPSG codes to convert coordinates to projection

        if radiusKM > MAX_SAFE_QUERY_DIST_KM:
            raise RuntimeError("Queries with radii greater than " + str(MAX_SAFE_QUERY_DIST_KM) + " may cause data loss due to webserver limitations")

        utmCode = self.getUTM(lng)
        EPSGCode = int("269" + str(utmCode))

        worldRef = osr.SpatialReference()
        worldRef.ImportFromEPSG(4326)

        stateRef = osr.SpatialReference()
        stateRef.ImportFromEPSG(EPSGCode) #projection from UTM zone of the current lat/lng
        print("utm is " + str(utmCode))
        transformation = osr.CoordinateTransformation(worldRef,stateRef)

        lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query?geometry=" + str(lng) + "," + str(lat) + "&outFields=*&geometryType=esriGeometryPoint&inSR=4326&outSR=" + str(EPSGCode) + "&distance=" + str(radiusKM*1000) + "&units=esriSRUnit_Meter&returnGeometry=true&f=geojson"        
        req = self.queryWithAttempts(lineURL, 4, queryName="lineData")
        

        lineDataSource = gdal.OpenEx(req.text)#, nOpenFlags=gdalconst.GA_Update)
        lineLayer = lineDataSource.GetLayer()

        if self.lineDataSource == None:
            self.lineDataSource = lineDataSource
            self.lineLayer = lineLayer
        else:
            print(self.lineLayer.GetFeatureCount())
            print(lineLayer.GetFeatureCount())
            testLayer = lineDataSource.CreateLayer("union layer", self.lineLayer.GetSpatialRef(), ogr.wkbLineString)
            self.lineLayer.Union(lineLayer, testLayer)
            print(testLayer.GetFeatureCount())

        approxRadiusInDeg = self.approxKmToDegrees(radiusKM)

        #northwest
        nwLat = lat + approxRadiusInDeg
        nwLng = lng + approxRadiusInDeg

        #southeast
        seLat = lat - approxRadiusInDeg
        seLng = lng - approxRadiusInDeg

        siteURL = "https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=" + str(nwLng) + "&nw_latitude_va=" + str(nwLat) + "&se_longitude_va=" + str(seLng) + "&se_latitude_va=" + str(seLat) + "&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box"
        req = req = self.queryWithAttempts(siteURL, 4, queryName="siteData")

        xmlSites = req.text#this query returns an xml. Have to conver to geoJson
        geoJsonSites = self.buildGeoJson(xmlSites, EPSGCode, transformation)
        siteDataSource = gdal.OpenEx(geoJsonSites)#, nOpenFlags=gdalconst.GA_Update)
        siteLayer = siteDataSource.GetLayer()

        if self.siteDataSource == None:
            self.siteDataSource = siteDataSource
            self.siteLayer = siteLayer
        else:
            self.siteLayer.Union(siteLayer, self.siteLayer)

        self.siteLayer.ResetReading()

