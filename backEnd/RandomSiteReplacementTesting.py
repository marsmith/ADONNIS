import random
from GDALData import getSiteIDsStartingWith, getSiteNeighbors, loadFromQuery
import json
from pathlib import Path
import os
from SiteInfoCreator import getSiteID
from SiteIDManager import SiteIDManager
from SnapSites import snapPoint, SnapablePoint
import Helpers

SITE_DATA_PATH = Path("testData")

def getPartNumber (n):
    nString = str(n)
    if len(nString) is 1:
        nString = "0" + nString
    return nString

def generateTestSiteIDList (numSites, partNumber):
    sitesPath = Path(__file__).parent.absolute() / SITE_DATA_PATH / "NYsites.txt"
    sitesString = sitesPath.read_text()
    lines = sitesString.split("\n")

    outFileName = "testingSet" + str(partNumber) + ".csv"
    outputPath = Path(__file__).parent.absolute() / SITE_DATA_PATH / outFileName
    outputFile = open(outputPath, "a")
    
    

    siteIDManager = SiteIDManager()

    header = "siteID, lat, lng, upperBound, lowerBound \n"
    outputFile.write(header)
    outputFile.close()

    numFound = 0
    while numFound < numSites:
        randomLine = int(random.random() * (len(lines) - 1))
        line = lines.pop(randomLine)
        data = line.split("\t")
        siteID = data[0]
        lat = float(data[1])
        lng = float(data[2])
    
        idNeighbors = siteIDManager.getNeighborIDs(siteID)
        if idNeighbors is not None:
            lowerNeighbor = idNeighbors[0]
            upperNeighbor = idNeighbors[1]
            print ("found neighbors")
            if lowerNeighbor is not None and upperNeighbor is not None and siteID[:2] == partNumber:
                print ("has upper and lower bound and correct part code")
                baseData = loadFromQuery(lat, lng)

                snapablePoint = SnapablePoint(point = (lng, lat), name = "", id = siteID)
                snapInfo = snapPoint(snapablePoint, baseData)

                if len(snapInfo) == 1:
                    print ("single snap. Writing to file")
                    outputFile = open(outputPath, "a")
                    newLine = siteID + ", " + str(lat) + ", " + str(lng) + ", " + upperNeighbor + ", " + lowerNeighbor + "\n"
                    outputFile.write(newLine)
                    numFound += 1
                    outputFile.close()
                else:
                    print ("multiple snaps. skipping")
            else:
                print ("missing upper or lower bound or incorrect part code")
    outputFile.close()
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

                generatedID = getSiteID(lat, lng, withheldSites = [siteID], enforceSingleSnap = True)

                #only test sites that have single best snaps.
                #this shouldn't limit the randomness of the tests. 
                #This restriction allows us to rule out snap errors of the replaced point
                if generatedID != "tooManySnaps":
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


def runTestList (fileName, outputName):
    sitesPath = Path(__file__).parent.absolute() / SITE_DATA_PATH / fileName
    sitesString = sitesPath.read_text()
    lines = sitesString.split("\n")

    outputPath = Path(__file__).parent.absolute() / SITE_DATA_PATH / outputName
    outputFile = open(outputPath, "a")

    header = "original site, adjacent site above, adjacent site below, new site, difference, between bounds \n"
    outputFile.write(header)
    outputFile.close()

    for i in range(1, len(lines)):
        line = lines[i]
        header = "siteID, lat, lng, upperBound, lowerBound \n"
        (siteID, lat, lng, upperBound, lowerBound) = line.split(", ")

        fullSiteID = Helpers.getFullID(siteID)
        upperID = Helpers.getFullID(upperBound)
        lowerID = Helpers.getFullID(lowerBound)
        output = ""
        generatedID = getSiteID(float(lat), float(lng), withheldSites = [siteID])
        betweenBounds = "n"
        
        try:
            originalDownstreamNum = int(fullSiteID[2:])
            generatedDownstreamNum = int(generatedID[2:])
            upperDownstreamNum = int(upperID[2:])
            lowerDownstreamNum = int(lowerID[2:])

            difference = abs(originalDownstreamNum - generatedDownstreamNum)
            
            if generatedDownstreamNum > lowerDownstreamNum and generatedDownstreamNum < upperDownstreamNum:
                betweenBounds = "y"
        except:
            difference = "nan"
            betweenBounds = "nan"
            difference = "nan"
        outputFile = open(outputPath, "a")
        output = "'" + fullSiteID + ",'" + upperID + ",'" + lowerID + ",'" + generatedID + ",'" + str(difference) + "," + betweenBounds + "\n"
        outputFile.write(output)
        outputFile.close()


runTestList("testingSet01.csv", "testingSet01_1.csv")
#generateTestSiteIDList(100, "01")
#randomReplacementTesting(30)
#print(getSiteNeighbors("01348000"))