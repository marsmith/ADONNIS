from osgeo import ogr
import os

BASE_DIR = os.path.join( os.path.dirname(os.path.dirname( __file__ )), '..' )
path_sites = BASE_DIR + '/data/ProjectedSites/ProjectedSites.shp'

sitesDataSource = ogr.Open(path_sites)
sl = sitesDataSource.GetLayer()