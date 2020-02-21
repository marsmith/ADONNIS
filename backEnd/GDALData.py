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

class GDALData(object):

    def __init__(self):
        self.localPath = os.path.join( os.path.dirname(os.path.dirname( __file__ ))) + "\data"
        print("self path = " + self.localPath)
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

    def loadFromQuery(self, lat, lng, maxRequestAttempts):
        #Get UTM and EPSG codes to convert coordinates to projection

        utmCode = self.getUTM(lng)
        EPSGCode = int("269" + str(utmCode))

        worldRef = osr.SpatialReference()
        worldRef.ImportFromEPSG(4326)

        stateRef = osr.SpatialReference()
        stateRef.ImportFromEPSG(EPSGCode) #projection from UTM zone of the current lat/lng
        print("utm is " + str(utmCode))
        transformation = osr.CoordinateTransformation(worldRef,stateRef)

        lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query?geometry=" + str(lng) + "," + str(lat) + "&outFields=GNIS_NAME%2CREACHCODE&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=10000&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=geojson"        
        req = self.queryWithAttempts(lineURL, 4, queryName="lineData")
        lineJson = json.loads(req.text)
        #change coordinates to UTM projection. Start with changing the metadata
        lineJson["crs"]["properties"]["name"] = "EPSG" + str(EPSGCode)
        for feature in lineJson["features"]:
            for coords in feature["geometry"]["coordinates"]:
                featureLat = coords[1]
                featureLng = coords[0]
                [projX, projY, z] = transformation.TransformPoint(featureLng, featureLat)
                coords[0] = projX
                coords[1] = projY

        projectedJson = json.dumps(lineJson)
        print(projectedJson[0:300])
        
        self.lineDataSource = gdal.OpenEx(projectedJson)
        self.lineLayer = self.lineDataSource.GetLayer()

        #transform geometry to utm projection
        self.lineLayer.ResetReading()
        for line in self.lineLayer:
            geomRef = line.GetGeometryRef()
            geomRef.Transform(transformation)

        radius = 10 #km this value is defined in gdalData somewhere
        approxRadiusInDeg = self.approxKmToDegrees(radius)

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
        self.siteDataSource = gdal.OpenEx(geoJsonSites)
        self.siteLayer = self.siteDataSource.GetLayer()

        self.siteLayer.ResetReading()
        
        print(self.siteLayer.GetSpatialRef())
        


        print(EPSGCode)

