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

    def buildGeoJson (self, xmlStr):
        root = ET.fromstring(xmlStr)
        geojson = {
            "type": "FeatureCollection",
            "crs": {"type":"name","properties":{"name":"EPSG:4326"}},
            "features":[]
        }
        for site in root:
            siteNo = int(site.find('site_no').text)
            stationNm = site.find('station_nm').text
            siteType = site.find('site_tp_cd').text
            siteLat = float(site.find('dec_lat_va').text)
            siteLng = float(site.find('dec_long_va').text)
            #make sure this is a stream not a well
            if(siteType == "ST"):
                #build feature. This is based on the format of the geoJson returned from the streams query
                feature = {
                    "type":"Feature",
                    "geometry":{
                        "type": "Point",
                        "coordinates": [siteLat, siteLng]
                    },
                    "properties": {
                        "site_no":siteNo,
                        "station_nm":stationNm
                    }
                }
                geojson["features"].append(feature)
        return json.dumps(geojson)

    def loadFromQuery(self, lat, lng, maxRequestAttempts):
        lineURL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6/query?geometry=" + str(lng) + "," + str(lat) + "&outFields=GNIS_NAME%2CREACHCODE&geometryType=esriGeometryPoint&inSR=4326&outSR=4326&distance=4000&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&f=geojson"
        print("requesting stream data...")
        lineDataAttempts = 0
        success = False
        while (lineDataAttempts < maxRequestAttempts):
            try:
                req = requests.get(lineURL, timeout=5)
                success = True
                break
            except requests.exceptions.ReadTimeout:
                print("failed to retrieve stream data on attempt " + str(lineDataAttempts) + ". Trying again")
        if success == False:
            print("failed to retrieve stream data on all attempts. Failing")
            return None
        
        print("recieved stream data!")
        self.lineDataSource = gdal.OpenEx(req.text)
        self.lineLayer = self.lineDataSource.GetLayer()

        radius = 5 #km this value is defined in gdalData somewhere
        approxRadiusInDeg = self.approxKmToDegrees(radius)

        #northwest
        nwLat = lat + approxRadiusInDeg
        nwLng = lng + approxRadiusInDeg

        #southeast
        seLat = lat - approxRadiusInDeg
        seLng = lng - approxRadiusInDeg

        print("requesting gauge site data...")
        siteURL = "https://waterdata.usgs.gov/nwis/inventory?nw_longitude_va=" + str(nwLng) + "&nw_latitude_va=" + str(nwLat) + "&se_longitude_va=" + str(seLng) + "&se_latitude_va=" + str(seLat) + "&coordinate_format=decimal_degrees&group_key=NONE&format=sitefile_output&sitefile_output_format=xml&column_name=site_no&column_name=station_nm&column_name=site_tp_cd&column_name=dec_lat_va&column_name=dec_long_va&list_of_search_criteria=lat_long_bounding_box"
        
        siteDataAttempts = 0
        success = False
        while (siteDataAttempts < maxRequestAttempts):
            try:
                req = requests.get(siteURL, timeout=5)
                success = True
                break
            except requests.exceptions.ReadTimeout:
                print("failed to retrieve site data on attempt " + str(siteDataAttempts) + ". Trying again")
        if success == False:
            print("failed to retrieve site data on all attempts. Failing")
            return None
        
        print("recieved gage data! converting to geoJSON...")
        xmlSites = req.text#this query returns an xml. Have to conver to geoJson
        geoJsonSites = self.buildGeoJson(xmlSites)
        self.siteDataSource = gdal.OpenEx(geoJsonSites)
        self.siteLayer = self.siteDataSource.GetLayer()
        print("stream data successfully recieved.")

