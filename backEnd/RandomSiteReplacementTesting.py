import random
from GDALData import getSiteIDsStartingWith, getSiteNeighbors
import json
from pathlib import Path
import os
from SiteInfoCreator import getSiteID
from SiteIDManager import SiteIDManager

SITE_DATA_PATH = Path("testData")

def getPartNumber (n):
    nString = str(n)
    if len(nString) is 1:
        nString = "0" + nString
    return nString

def generateTestSiteIDList (numSites, partNumber):
    partNumbString = getPartNumber(partNumber)
    firstDigit = 0
    
    for i in range (1, 9):
        (siteLayer, dataSource) = getSiteIDsStartingWith(partNumbString + str(i), timeout = 20)

        allSites = []
        siteNumberIndex = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
        for site in siteLayer:
            siteID = site.GetFieldAsString(siteNumberIndex)
            point = site.GetGeometryRef().GetPoint(0)
            lat = point[1]
            lng = point[0]

            allSites.append((siteID, lat, lng))

        outStructure = []
        for i in range (numSites):
            if len(allSites) is 0:
                break
            randomIndex = int(random.random() * (len(allSites)-1))
            siteInfo = allSites.pop(randomIndex)
            site = {"siteNo":siteInfo[0], "lat":siteInfo[1], "lng":siteInfo[2]}
            outStructure.append(site)
        jsonText = json.dumps(outStructure)

        sitesFile = open("testData/rndSites" + partNumbString + str(i) + ".json","w+")
        sitesFile.write(jsonText)


def randomReplacementTesting (numTests):
    sitesPath = Path(__file__).parent.absolute() / SITE_DATA_PATH / "NYsites.txt"
    sitesString = sitesPath.read_text()
    lines = sitesString.split("\n")

    output = "originalSite, adjacent site above, adjacent site below, new site, difference, between bounds \n"
    numOutLines = 0

    siteIDManager = SiteIDManager()

    while numOutLines < numTests:
        randomLine = int(random.random() * (len(lines) - 1))
        line = lines.pop(randomLine)
        data = line.split("\t")
        siteID = data[0]
        lat = float(data[1])
        lng = float(data[2])

        idNeighbors = siteIDManager.getNeighborIDs(siteID)
        if idNeighbors is not None and siteID[:2] == "01":
            lowerNeighbor = idNeighbors[0]
            upperNeighbor = idNeighbors[1]
            if len(lowerNeighbor) < 10:
                lowerNeighbor += "00"
            if len(upperNeighbor) < 10:
                upperNeighbor += "00"

            if lowerNeighbor is not None and upperNeighbor is not None:

                generatedID = getSiteID(lat, lng, withheldSites = [siteID])

                fullSiteID = siteID
                if len(fullSiteID) < 10:
                    fullSiteID += "00"

                originalDSN = int(fullSiteID[2:])
                try:
                    calculatedDSN = int(generatedID[2:])
                    difference = originalDSN - calculatedDSN

                    upperBoundDSN = int(upperNeighbor[2:])
                    lowerBoundDSN = int(lowerNeighbor[2:])

                    betweenBounds = "n"
                    #upstream bound has lower number per rules
                    if calculatedDSN < upperBoundDSN and calculatedDSN > lowerBoundDSN:
                        betweenBounds = "y"
                except:
                    difference = "nan"
                    betweenBounds = "nan"

                output += "'" + fullSiteID + ",'" + upperNeighbor + ",'" + lowerNeighbor + ",'" + generatedID + ",'" + str(difference) + "," + betweenBounds + "\n"
                #we have both neighbors found. We use this test case bc it is more convenient and seems just as random
                numOutLines += 1
    outputPath = Path(__file__).parent.absolute() / SITE_DATA_PATH / "testOutput.csv"

    outputFile = open(outputPath, "a")
    outputFile.write(output)
    outputFile.close()


#generateTestSiteIDList(100, 1)
randomReplacementTesting(100)
#print(getSiteNeighbors("01348000"))