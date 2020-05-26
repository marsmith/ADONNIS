from StreamGraph import *
from StreamGraphNavigator import *
import SiteInfoCreator
from GDALData import getSiteIDsStartingWith
from SnapSites import getSiteSnapAssignment
import json
import sys

#test driver. Allows for command line interaction and testing
while True:
    #segID = input("enter a edge segmentID: ")
    idReplacement = input("Test by replacing an existing site?")
    excludedList = []
    
    if idReplacement == "y":
        inputSite = input("enter a site to replace: ")

        siteLayer = getSiteIDsStartingWith(inputSite)
        featureCount = len(siteLayer)
        if featureCount >= 1:
            print("found site")
            for site in siteLayer:
                queriedID = site["properties"]["site_no"]
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

    arguments = sys.argv

    results = SiteInfoCreator.SiteInfoCreator(lat, lng, withheldSites = excludedList).getSiteID(useBadSites=False)

    if results is None:
        print("failed")
    else:
        print ("site:\n " + results["id"])
        print ("story:\n " + results["story"])
        print ("log:\n " + json.dumps(results["log"]))
