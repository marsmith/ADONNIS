from osgeo import gdalconst
from StreamGraph import *
from StreamGraphNavigator import *
from SiteInfoCreator import getSiteID
from GDALData import getSiteIDsStartingWith
from SnapSites import getSiteSnapAssignment

while True:
    #segID = input("enter a edge segmentID: ")
    idReplacement = input("Test by replacing an existing site?")
    excludedList = []
    
    if idReplacement == "y":
        inputSite = input("enter a site to replace: ")

        (siteLayer, dataSource) = getSiteIDsStartingWith(inputSite)
        featureCount = siteLayer.GetFeatureCount()
        siteNumberIndex = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
        if featureCount >= 1:
            print("found site")
            for site in siteLayer:
                queriedID = site.GetFieldAsString(siteNumberIndex)
                if queriedID == inputSite:
                    point = site.GetGeometryRef().GetPoint()
                    lat = point[1]
                    lng = point[0]
                    excludedList.append(inputSite)
                    break
        else:
            print("failure")
            continue
    else:
        latLng = input("enter a lat/lng: ")
        latLng = latLng.split(",")
        if len(latLng) < 2:
            continue

        lat = float(latLng[0])
        lng = float(latLng[1])

    siteId = getSiteID(lat, lng, withheldSites = excludedList, debug = True)

    if getSiteID is None:
        print("failed")
    else:
        print ("site is " + str(siteId))
