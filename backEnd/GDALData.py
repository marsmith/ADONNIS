#Ian Scilipoti
#Feb, 5th, 2020
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdal_array
from osgeo import gdalconst
import os

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
        # we dib't really need the reference to siteDataSource, however
        # if this reference isn't saved my guess is that the data source reference is destroyed 
        # this reference is likely required for things like siteLayer.GetSpatialRef()
        self.siteLayer = self.siteDataSource.GetLayer()

    #def loadFromQuery(self, lat, long):
        #fill this in with query stuff

