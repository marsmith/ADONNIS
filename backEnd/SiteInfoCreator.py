#!/usr/bin/python3.6

from StreamGraphNavigator import StreamGraphNavigator
from StreamGraph import StreamGraph
from SnapSites import snapPoint, SnapablePoint
import SnapSites
import GDALData
import Helpers
from SiteIDManager import SiteIDManager
import Failures
import math
import sys
import json
import WarningLog
import collections

#---query limits
MAX_PRIMARY_QUERIES = 30
#how many queries will we try AFTER finding a single upstream/downstream site to find the other upstream/downstream site?
MAX_SECONDARY_SITE_QUERIES = 5
#what's the smallest reasonable distance between two sites
#according to Gary Wall this is 500 feet 
#rounding down to be safe, we get 100 meters 
MIN_SITE_DISTANCE = 0.1 #(kilometers)

#---naming
AT_DISTANCE = 1609.34 #(meters) a mile. Otherwise, name is "near"
CONTEXT_DIST_LIMIT = 4000 #about 2.5 miles

class SiteInfoCreator (object):

    def __init__(self, lat, lng, withheldSites = []):
        self.lat = lat
        self.lng = lng
        self.warningLog = WarningLog.WarningLog(lat, lng)
        self.streamGraph = StreamGraph(withheldSites = withheldSites, warningLog = self.warningLog)
        self.siteIDManager = SiteIDManager()
        self.context = None
        self.baseData = GDALData.loadFromQuery(self.lat, self.lng)

        if Failures.isFailureCode(self.baseData):
            if __debug__:
                print ("could not get data")
            warningLog.addWarning(WarningLog.HIGH_PRIORITY, self.baseData)
        else:
            self.streamGraph.addGeom(self.baseData)

    def getSiteNameContext (self, lat, lng, streamGraph, baseData):
        if self.context is not None:
            return self.context
        context = {}
        point = (lng, lat)
        snapablePoint = SnapablePoint(point = point, name = "", id = "")
        snapInfo = snapPoint(snapablePoint, baseData, snapCutoff = 1) #get the most likely snap

        if Failures.isFailureCode(snapInfo):
            return snapInfo

        feature = snapInfo[0].feature
        
        segmentID = str(feature["properties"]["OBJECTID"])

        distAlongSegment = snapInfo[0].distAlongFeature
        #get the segment ID of the snapped segment
        graphSegment = streamGraph.getCleanedSegment(segmentID)

        navigator = StreamGraphNavigator(streamGraph)

        downstreamSegment = navigator.findNextLowerStreamLevelPath(graphSegment, downStreamPositionOnSegment=distAlongSegment, expand = False)
        
        streamName = graphSegment.streamName
        if streamName == "":
            if not Failures.isFailureCode(downstreamSegment) and downstreamSegment[0].streamName != "":
                context["streamName"] = downstreamSegment[0].streamName + " tributary"
            else:
                context["streamName"] = "(INSERT STREAM NAME)"
        else:
            context["streamName"] = streamName
        
        placeInfo = GDALData.getNearestPlace(lat, lng)
        if Failures.isFailureCode(placeInfo):
            context["distanceToPlace"] = "-1"
            context["state"] = "unknown"
            context["placeName"] = "unknown"
        else:
            context["distanceToPlace"] = placeInfo["distanceToPlace"]
            context["state"] = placeInfo["state"]
            context["placeName"] = placeInfo["placeName"]
        context["lat"] = lat
        context["long"] = lng

        contextualPlaces = []
        
        bridges = GDALData.getNearestBridges(lat, lng)
        namedTribMouths = navigator.getNamedTribMouths()
        
        contextualPlaces.extend([{"name": context.name, "point":context.point, "distance":context.distance} for context in bridges])
        contextualPlaces.extend([{"name": mouth[0], "point": mouth[1], "distance":Helpers.degDistance(mouth[1][0], mouth[1][1], lng, lat)} for mouth in namedTribMouths])

        context["contextualPlaces"] = contextualPlaces

        upstreamDistance = graphSegment.arbolateSum - (graphSegment.length - distAlongSegment)
        #check if we are at a stream mouth     
        upstreamDistMiles = Helpers.metersToMiles(upstreamDistance * 1000)
        if upstreamDistMiles < 1:
            context["source"] = "at source"
        elif upstreamDistMiles < 3:
            context["source"] = "near source"
        else:
            context["source"] = ""

        if Failures.isFailureCode(downstreamSegment):
            context["mouth"] = ""
        else:
            downstreamDistMiles = Helpers.metersToMiles(downstreamSegment[1]*1000)
            #make sure that the mouth distance is less than upstream dist
            #before assigning descriptor. Otherwise, we could have near mouth and near source as option 
            #on the same site
            if downstreamDistMiles > upstreamDistMiles:
                context["mouth"] = ""
            else:
                #likewise, if downstream is closer, don't use "at source" type descriptors
                context["source"] = ""
                if downstreamDistMiles < 1:
                    context["mouth"] = "at mouth"
                elif downstreamDistMiles < 3:
                    context["mouth"] = "near mouth"
                else:
                    context["mouth"] = ""

        self.context = context
        return context
           
    def getSiteNameInfo (self, siteNameContext):
        #beginning of name
        beginning = [siteNameContext["streamName"] + " "]
        if len(siteNameContext["mouth"]) > 0:
            beginning.append(siteNameContext["streamName"] + " " + siteNameContext["mouth"] + " ")
        if len(siteNameContext["source"]) > 0:
            beginning.append(siteNameContext["streamName"] + " " + siteNameContext["source"] + " ")
        #middle of the name. more choices here
        middle = []

        lat = siteNameContext["lat"]
        lng = siteNameContext["long"]

        middle.append ("")#capture base case when we don't want any middle context
        sortedContextualPlaces = sorted(siteNameContext["contextualPlaces"], key=lambda context: context["distance"])
        sortedContextualPlaces = sortedContextualPlaces[:min(3, len(sortedContextualPlaces))]
        for contextPlace in sortedContextualPlaces:
            name = contextPlace["name"]
            distance = contextPlace["distance"]
            point = contextPlace["point"]

            if distance > CONTEXT_DIST_LIMIT:
                continue

            cardinalDirection = Helpers.getCardinalDirection(point, (lng, lat))

            """ if distance < AT_DISTANCE:
                middle.append("at " + name + " ")
            else: """
            middle.append("near " + name + " ")

            #middle.append(cardinalDirection + " of " + name + " ")

            distMiles = Helpers.metersToMiles(distance)

            roundDist = Helpers.roundTo(distMiles, 0.1)
            roungDistStr = str(roundDist)[:3]
            if roundDist > 1 or roundDist < 1:
                middle.append(roungDistStr + " miles " + cardinalDirection + " of " + name + " ")
            else:
                middle.append("1 mile " + cardinalDirection + " of " + name + " ")

        #end of name
        end = ""
        if siteNameContext["distanceToPlace"] < AT_DISTANCE:
            end = "at "
        else:
            end = "near "

        end += siteNameContext["placeName"] + " " + siteNameContext["state"]
        allNames = []
        for mid in middle:
            for beg in beginning:
                allNames.append((beg + mid + end).upper())

        return {"suggestedNames":allNames, "context":siteNameContext}


#withheld sites is a list of sites to be ignored while calculating a new site
    def getSiteID (self, useBadSites = True):
        lat = self.lat
        lng = self.lng
        warningLog = self.warningLog
        streamGraph = self.streamGraph
        siteIDManager = self.siteIDManager

        streamGraph.setAssignBadSitesStatus(useBadSites)

        #typically lat/long are switched to fit the x/y order paradigm 
        point = (lng, lat)
        
        story = ""
        newID = ""
        huc = ""

        #create the json that gets resturned
        def getResults (siteID = "unknown", story = "See warning log", failed=False):
            if not failed:
                siteNameContext = self.getSiteNameContext(lat, lng, streamGraph, self.baseData)

                if Failures.isFailureCode(siteNameContext):
                    nameResults = {"suggestedNames":["unknown"], "context":{}}
                else:
                    nameResults = self.getSiteNameInfo(siteNameContext)
                    nameResults["context"] = [] #don't need this feature now
            else:
                nameResults = {"suggestedNames":["unknown"], "context":{}}

            results = dict()
            results["id"] = siteID

            snapLatFormatted = Helpers.getFloatTruncated(lat, 7)
            snapLngFormatted = Helpers.getFloatTruncated(lng, 7)
            storyHeader = "Requested site info at " + str(snapLatFormatted) + ", " + str(snapLngFormatted) + ". "
            useBadSitesStory = ("Using " if useBadSites else "Not using ") + "incorrect IDs. "
            results["story"] = storyHeader + useBadSitesStory + story
            results["log"] = warningLog.getJSON()
            results["nameInfo"] = nameResults
            return results

        if Failures.isFailureCode(self.baseData):
            return getResults(failed = True)

        #snap query point to a segment
        snapablePoint = SnapablePoint(point = point, name = "", id = "")
        snapInfo = snapPoint(snapablePoint, self.baseData, snapCutoff = 1) #get the most likely snap
        if Failures.isFailureCode(snapInfo):
            if __debug__:
                print ("could not snap")
            warningLog.addWarning(WarningLog.HIGH_PRIORITY, snapInfo)
            return getResults(failed = True)

        feature = snapInfo[0].feature
        segmentID = str(feature["properties"]["OBJECTID"])
        distAlongSegment = snapInfo[0].distAlongFeature
        #get the segment ID of the snapped segment
        graphSegment = streamGraph.getCleanedSegment(segmentID)

        snappedPoint = streamGraph.segments[segmentID].getPointOnSegment(distAlongSegment)

        if __debug__:
            SnapSites.visualize(self.baseData, [])
            streamGraph.visualize(customPoints=[snappedPoint], showSegInfo = True)
            streamGraph.visualize(customPoints=[snappedPoint], showSegInfo = False)

        #build a navigator object
        #we want to terminate the search each time a query happens
        #this allows us to stagger upstream and downstream searches
        #although this means repeating parts of the search multiple times, searching a already constructed
        #graph takes practically no time at all
        navigator = StreamGraphNavigator(streamGraph, terminateSearchOnQuery = True)

        upstreamSite = None
        downstreamSite = None
        endOfUpstreamNetwork = False
        endOfDownstreamNetwork = False
        secondaryQueries = 0
        primaryQueries = 0

        #each iteration extends the graph by one query worth of data
        # in this step we try to find an upstream and downstream site
        while (upstreamSite is None or downstreamSite is None) and secondaryQueries < MAX_SECONDARY_SITE_QUERIES and primaryQueries < MAX_PRIMARY_QUERIES and (endOfUpstreamNetwork is False or endOfDownstreamNetwork is False):
            if upstreamSite is None and endOfUpstreamNetwork is False:
                #we haven't found upstream yet
                upstreamReturn = navigator.getNextUpstreamSite(graphSegment, distAlongSegment)
                if upstreamReturn == Failures.END_OF_BASIN_CODE:
                    endOfUpstreamNetwork = True
                if Failures.isFailureCode(upstreamReturn) is not True and upstreamReturn is not None:
                    upstreamSite = upstreamReturn

            if downstreamSite is None and endOfDownstreamNetwork is False:
                #we haven't found downstream yet
                downstreamReturn = navigator.getNextDownstreamSite(graphSegment, distAlongSegment)
                if downstreamReturn == Failures.END_OF_BASIN_CODE:
                    endOfDownstreamNetwork = True
                if Failures.isFailureCode(downstreamReturn) is not True and downstreamReturn is not None:
                    downstreamSite = downstreamReturn

            if upstreamSite is not None or downstreamSite is not None:
                #we've found at least one site
                secondaryQueries += 1
            else:
                primaryQueries += 1
        
        #add warnings from found sites, collect HUC
        if upstreamSite is not None:
            siteAssignment = upstreamSite[0]
            for warning in siteAssignment.generalWarnings:
                warningLog.addWarningTuple(warning)
            for warning in siteAssignment.assignmentWarnings:
                warningLog.addWarningTuple(warning)

            huc = siteAssignment.huc
        
        if downstreamSite is not None:
            siteAssignment = downstreamSite[0]
            for warning in siteAssignment.generalWarnings:
                warningLog.addWarningTuple(warning)
            for warning in siteAssignment.assignmentWarnings:
                warningLog.addWarningTuple(warning)

            huc = siteAssignment.huc
        
        for warning in streamGraph.currentAssignmentWarnings:
            warningLog.addWarningTuple(warning)

        #handle all combinations of having an upstream site and/or a downstream site (also having neither)
        
        #~~~~~~~~~~~~~~~~~~~UPSTREAM AND DOWNSTREAM SITES FOUND CASE~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if upstreamSite is not None and downstreamSite is not None:
            #we have an upstream and downstream

            upstreamSiteID = upstreamSite[0].siteID
            downstreamSiteID = downstreamSite[0].siteID
            partCode = upstreamSiteID[0:2]

            if Helpers.siteIDCompare(downstreamSiteID, upstreamSiteID) < 0:
                message = "The found upstream site is larger than found downstream site. ADONNIS output almost certainly incorrect."
                warningLog.addWarning(WarningLog.HIGH_PRIORITY, message)

            fullUpstreamSiteID = Helpers.getFullID(upstreamSiteID)
            fullDownstreamSiteID = Helpers.getFullID(downstreamSiteID)

            upstreamSiteIdDsnStr = fullUpstreamSiteID[2:]
            downstreamSiteIdDsnStr = fullDownstreamSiteID[2:]

            #get the downstream number portion of the ID
            upstreamSiteIdDsn = int(upstreamSiteIdDsnStr)
            downstreamSiteIdDsn = int(downstreamSiteIdDsnStr)

            totalAddressSpaceDistance = upstreamSite[1] + downstreamSite[1]
            newSitePercentage = downstreamSite[1] / totalAddressSpaceDistance

            newDon = int(downstreamSiteIdDsn * (1 - newSitePercentage) + upstreamSiteIdDsn * newSitePercentage)

            newID = Helpers.buildFullID(partCode, newDon)
            newID = self.beautifyID(newID, downstreamSiteID, upstreamSiteID)
            story = "Found a upstream site " + Helpers.formatID(upstreamSiteID) + " and a downstream site " + Helpers.formatID(downstreamSiteID) + ". New site is the weighted average of these two sites."

            if __debug__:
                print ("found upstream is " + upstreamSiteID)
                print ("found downstream is " + downstreamSiteID)
                streamGraph.visualize(customPoints=[snappedPoint])
                SnapSites.visualize(self.baseData, [])

        #~~~~~~~~~~~~~~~~~~~UPSTREAM SITE FOUND ONLY CASE~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
        elif upstreamSite is not None:
            upstreamSiteID = upstreamSite[0].siteID
            partCode = upstreamSiteID[:2]
            fullUpstreamID = Helpers.getFullID(upstreamSiteID)

            foundSiteNeighbors = siteIDManager.getNeighborIDs(upstreamSiteID, huc)
            if Failures.isFailureCode(foundSiteNeighbors):
                nextSequentialDownstreamSite = None
            else:
                nextSequentialDownstreamSite = foundSiteNeighbors[1]

            upstreamSiteDSN = int(fullUpstreamID[2:])
            upstreamSiteDistance = upstreamSite[1]

            #calculate offset. If we have a sequential downstream use that as a bound
            siteIDOffset = math.ceil(upstreamSiteDistance / MIN_SITE_DISTANCE)
            if nextSequentialDownstreamSite is not None:
                #if we have the sequential downstream bound, don't let the new site get added any closer than halfway between
                siteIDOffset = min(siteIDOffset, Helpers.getSiteIDOffset(upstreamSiteID, nextSequentialDownstreamSite)/2)
            
            newSiteIDDSN = upstreamSiteDSN + siteIDOffset

            #allowed wiggle room in the new site. Depending on how much distance is between the found site
            #we allow for a larger range in the final ID. Has to be at least 10% within the rule of min_site_distance
            #at most 5 digits up or down. At least, 0
            allowedError = math.floor(max(1, min(siteIDOffset / 10, 5)))

            upperBound = Helpers.buildFullID(partCode, upstreamSiteDSN + siteIDOffset + allowedError)
            lowerBound = Helpers.buildFullID(partCode, upstreamSiteDSN + siteIDOffset - allowedError)
            
            newID = Helpers.buildFullID(partCode, newSiteIDDSN)
            newID = self.beautifyID(newID, lowerBound, upperBound)
            offsetAfterBeautify = Helpers.getSiteIDOffset(newID, fullUpstreamID)
            
            if nextSequentialDownstreamSite is None:
                story = "Only found a upstream site (" + upstreamSiteID + "). New site ID is based on upstream site while allowing space for " + str(offsetAfterBeautify) + " sites between upstream site and new site"
                warningLog.addWarning(WarningLog.HIGH_PRIORITY, "No downstream bound on result. Needs verification!")
            else:
                story = "Found an upstream site " + Helpers.formatID(upstreamSiteID) + ". Based on list of all sites, assume that " + Helpers.formatID(nextSequentialDownstreamSite) + " is the nearest sequential downstream site. New ID is based on the upstream site and bounded by the sequential downstream site"
                warningLog.addWarning(WarningLog.LOW_PRIORITY, "Found upstream and downstream bound. But, downstream bound is based on list of sequential sites and may not be the true downstream bound. This could result in site ID clustering.")

            if __debug__:
                    print("found upstream, but not downstream")
                    print("upstream siteID is " + str(upstreamSiteID))
                    streamGraph.visualize(customPoints=[snappedPoint])
                    SnapSites.visualize(self.baseData, [])
        
        #~~~~~~~~~~~~~~~~~~~DOWNSTREAM SITE ONLY CASE~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        elif downstreamSite is not None:
            downstreamSiteID = downstreamSite[0].siteID
            partCode = downstreamSiteID[:2]
            fullDownstreamID = Helpers.getFullID(downstreamSiteID)

            foundSiteNeighbors = siteIDManager.getNeighborIDs(downstreamSiteID, huc)
            if Failures.isFailureCode(foundSiteNeighbors):
                nextSequentialUpstreamSite = None
            else:
                nextSequentialUpstreamSite = foundSiteNeighbors[0]

            downstreamSiteDSN = int(fullDownstreamID[2:])
            downstreamSiteDistance = downstreamSite[1]

            siteIDOffset = math.ceil(downstreamSiteDistance / MIN_SITE_DISTANCE)

            if nextSequentialUpstreamSite is not None:
                #if we have the sequential upstream bound, don't let the new site get added any closer than halfway between
                siteIDOffset = min(siteIDOffset, Helpers.getSiteIDOffset(downstreamSiteID, nextSequentialUpstreamSite)/2)

            newSiteIDDSN = downstreamSiteDSN - siteIDOffset

            allowedError = math.floor(max(1, min(siteIDOffset / 10, 5)))

            upperBound = Helpers.buildFullID(partCode, downstreamSiteDSN - siteIDOffset + allowedError)
            lowerBound = Helpers.buildFullID(partCode, downstreamSiteDSN - siteIDOffset - allowedError)
            
            newID = Helpers.buildFullID(partCode, newSiteIDDSN)
            newID = self.beautifyID(newID, lowerBound, upperBound)
            offsetAfterBeautify = Helpers.getSiteIDOffset(newID, fullDownstreamID)
            
            if nextSequentialUpstreamSite is None:
                story = "Only found a downstream site " + Helpers.formatID(downstreamSiteID) + ". New site ID is based on downstream site while allowing space for " + str(offsetAfterBeautify) + " sites between downstream site and new site"
                warningLog.addWarning(WarningLog.HIGH_PRIORITY, "No upstream bound on result. Needs verification!")
            else:
                story = "Found a downstream site " + Helpers.formatID(downstreamSiteID) + ". Based on list of all sites, assume that " + Helpers.formatID(nextSequentialUpstreamSite) + " is the nearest sequential upstream site. New ID is based on the downstream site and bounded by the sequential upstream site"
                warningLog.addWarning(WarningLog.LOW_PRIORITY, "Found upstream and downstream bound. But, upstream bound is based on list of sequential sites and may not be the true upstream bound. This could result in site ID clustering.")
            
            if  __debug__:
                print("found downstream, but not upstream")
                print("downstream siteID is " + str(downstreamSiteID))
                streamGraph.visualize(customPoints=[snappedPoint])
                SnapSites.visualize(self.baseData, [])
        
        #~~~~~~~~~~~~~~~~~~~NO SITES FOUND CASE~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        else:
            # get huge radius of sites:
            sitesInfo = GDALData.loadSitesFromQuery(lat, lng, 30)
            if Failures.isFailureCode(sitesInfo):
                warningLog.addWarning(WarningLog.HIGH_PRIORITY, sitesInfo)
                return getResults(failed = True)
            
            sites = []
            for site in sitesInfo:
                siteNumber = site["properties"]["site_no"]
                siteHUC = site["properties"]["huc_cd"]
                sitePoint = site["geometry"]["coordinates"]
                fastDistance = Helpers.fastMagDist(sitePoint[0], sitePoint[1], point[0], point[1])
                sites.append((siteNumber, sitePoint, fastDistance, siteHUC))
            
            sortedSites = sorted(sites, key=lambda site: site[2])

            huc = sortedSites[0][3]

            oppositePairA = None
            oppositePairB = None
            foundOppositePair = False
            i = 1
            while foundOppositePair is False:
                curSite = sortedSites[i]
                curPartCode = curSite[0][:2]
                curSitePoint = curSite[1]
                curDirection = Helpers.normalize(curSitePoint[0] - point[0], curSitePoint[1] - point[1])
                for cmpSite in sortedSites[:i]:
                    cmpSitePoint = cmpSite[1]
                    cmpDirection = Helpers.normalize(cmpSitePoint[0] - point[0], cmpSitePoint[1] - point[1]) 
                    cmpPartCode = cmpSite[0][:2]
                    dot = Helpers.dot(curDirection[0], curDirection[1], cmpDirection[0], cmpDirection[1])
                    
                    #check if these two directions are mostly opposite
                    # dot < 0 means they are at least perpendicular
                    if dot < 0.4 and curPartCode == cmpPartCode:
                        foundOppositePair = True
                        oppositePairA = cmpSite
                        oppositePairB = curSite
                i += 1
            
            partCode = oppositePairA[0][:2]

            fullIDA = Helpers.getFullID(oppositePairA[0])
            fullIDB = Helpers.getFullID(oppositePairB[0])

            dsnA = int(fullIDA[2:])
            dsnB = int(fullIDB[2:])

            distA = oppositePairA[2]
            distB = oppositePairB[2]

            totalAddressSpaceDistance = distA + distB
            newSitePercentage = distA / totalAddressSpaceDistance

            newDsn = int(dsnA * (1 - newSitePercentage) + dsnB * newSitePercentage)

            newID = Helpers.buildFullID(partCode, newDsn)
            newID = self.beautifyID(newID, fullIDA, fullIDB)

            story = "Could not find any sites on the network. Estimating based on " + Helpers.formatID(oppositePairA[0]) + " and " + Helpers.formatID(oppositePairB[0]) + "."
            
            if __debug__:
                print("no sites found nearby. Estimating new ID based on nearby sites")
                print ("new estimate based on " + oppositePairA[0] + " and " + oppositePairB[0])
                print ("estimation is " + newID)
                streamGraph.visualize()
                SnapSites.visualize(self.baseData, [])

        return getResults(siteID = newID, story = story) 

    def beautifyID (self, siteID, lowerBound, upperBound):
        warningLog = self.warningLog
        siteID = str(siteID)
        shortenedID = siteID[:7]
        DSN = int(Helpers.getFullID(siteID)[2:])
        partCode = siteID[:2]

        lowerBoundDSN = int(Helpers.getFullID(lowerBound)[2:])
        upperBoundDSN = int(Helpers.getFullID(upperBound)[2:])
        
        roundingPrecisions = [100, 50, 20, 10, 5, 2, 1]

        #now check if this number exists already
        idsInfo = GDALData.getSiteIDsStartingWith(shortenedID)
        if Failures.isFailureCode(idsInfo):
            warningLog.addWarning(WarningLog.LOW_PRIORITY, "Cannot verify if this site number already exists(" + idsInfo + "). Ensure this step is manually completed.")
            return siteID
        
        siteLayer = idsInfo

        existingNumbers = set()
        for site in siteLayer:
            siteNumber = site["properties"]["site_no"]
            existingNumbers.add(siteNumber)
        
        for roundTo in roundingPrecisions:
            roundedDSN = Helpers.roundTo(DSN, roundTo)
            fullRounded = Helpers.buildFullID(partCode, roundedDSN)
            if fullRounded not in existingNumbers and Helpers.betweenBounds(roundedDSN, lowerBoundDSN, upperBoundDSN):
                return Helpers.shortenID(fullRounded)

        #if we haven't returned yet we have a problem.
        idMinusExtension = siteID[:8]

        #as a last ditch effort, try all extensions to find one that's unique
        if len(existingNumbers) > 0:
            #if the ID we want is taken, try all possible extensions until one is free
            for i in range(0, 100):
                testExtension = str(i)

                if len(testExtension) == 1:
                    testExtension = "0" + testExtension

                testNewID = idMinusExtension + testExtension

                testNewDSN = int(testNewID[2:])

                if testNewID not in existingNumbers and Helpers.betweenBounds(testNewDSN, lowerBoundDSN, upperBoundDSN):
                    return testNewID
        
        warningLog.addWarning(WarningLog.MED_PRIORITY, "Failed to find gap in ID space for new ID. This ID already exists.")
        return siteID    

if __name__ == "__main__":
    useBadSites = True
    latlngArgs = sys.argv[1]
    if len(sys.argv) > 2:
        useBadSitesArgs = sys.argv[2]
        if useBadSitesArgs == "False":
            useBadSites = False

    lat,lng = latlngArgs.split(",")

    lat = float(lat)
    lng = float(lng)

    siteInfoCreator = SiteInfoCreator(lat, lng)
    dictResults = siteInfoCreator.getSiteID(useBadSites = useBadSites)

    print (json.dumps(dictResults))

    """ if Failures.isFailureCode(siteInfo):
        res = {'Results': str(siteInfo), 'Story': "Could not produce story.", 'Log': ""}
        results = json.dumps(res)
        print(results)
    else:
        res = {'Results': str(siteInfo[0]), 'Story': str(siteInfo[1])}
        results = json.dumps(res)
        print(results) """
