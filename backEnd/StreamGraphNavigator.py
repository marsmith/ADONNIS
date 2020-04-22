#from StreamGraph import UPSTREAM, DOWNSTREAM
from collections import namedtuple 
import sys
import Failures
#a class that has various functionality to find / expand a StreamGraph


StreamSearch = namedtuple('StreamSearch', 'id openSegments')

class StreamGraphNavigator (object):

    def __init__(self, streamGraph, terminateSearchOnQuery = False, debug = False):
        self.streamGraph = streamGraph
        self.activeSearches = {}
        self.nextSearchId = 0
        self.terminateSearchOnQuery = terminateSearchOnQuery
        self.debug = debug
        streamGraph.addGraphListener(self)

    #open a new search and get a new StreamSearch tuple
    def openSearch(self):
        openSegs = [] #list of segments pending action in our search
        streamSearch = StreamSearch(id = self.nextSearchId, openSegments = openSegs)
        self.activeSearches[streamSearch.id] = streamSearch
        self.nextSearchId += 1
        return streamSearch
    def closeSearch(self, id):
        del self.activeSearches[id]

    #navigate downstream until a path with lower streamlevel is found. This function returns the first segment
    #directly upstream from the junction of the main path and the tributary that 'segment' is on
    def findNextLowerStreamLevelPath (self, segment):
        tribLevel = segment.streamLevel

        queue = []
        queue.append(segment)

        nextMainPath = None
        while len(queue) > 0:
            current = queue.pop(0)
            if current.streamLevel < tribLevel:
                #if we find a lower stream level it is downstream from the trib we started on
                # so to find the next main stream path, we have to go up from this segment along the matching streamlevel neighbor
                upstreamNeighbors = current.upStreamNode.getUpstreamNeighbors()#getCodedNeighbors(UPSTREAM)
                for neighbor in upstreamNeighbors:
                    if neighbor.streamLevel == current.streamLevel:
                        nextMainPath = neighbor
                        break
            else:
                downstreamPoint = current.downStreamNode.position
                if not self.streamGraph.pointWithinSafeDataBoundary (downstreamPoint):
                    graphExpansion = self.streamGraph.expandGraph(downstreamPoint[1], downstreamPoint[0])
                    
                    if Failures.isFailureCode(graphExpansion):
                        return graphExpansion
                    elif self.terminateSearchOnQuery is True:
                        return Failures.QUERY_TERMINATE_CODE
                    
                nextSegments = current.downStreamNode.getDownstreamNeighbors()#getCodedNeighbors(DOWNSTREAM)#most likely only one such segment unless there is a fork in the river
                queue.extend(nextSegments)
        
        if nextMainPath is not None:
            return nextMainPath
        else:
            return Failures.END_OF_BASIN_CODE

    # get a sorted list of all upstream sites from 'segment'
    # list is sorted such that sites with higher IDS (closer to the mouth of the river) are first
    # returns either an error code or a tuple (upstream sites, collectedUpstreamDistance)
    def collectSortedUpstreamSites (self, segment, downStreamPositionOnSegment, siteLimit = 1, autoExpand = True):
        # contains tuples of the form (site, dist to site)
        foundSites = []

        # reverse order of segment.sites since normally it is ordered upstream->downstream
        # since we are collecting sites from downstream->upstream
        for site in reversed(segment.sites):
            if site.distDownstreamAlongSegment < downStreamPositionOnSegment and len(foundSites) < siteLimit:
                foundSites.append((site, downStreamPositionOnSegment - site.distDownstreamAlongSegment)) 

        if len(foundSites) >= siteLimit:
            #return the list of found sites and the distance upstream of the last site found
            return (foundSites, foundSites[-1][1])

        #get upstream tributaries of this path
        stack = []
        stack.append(segment)

        summedDistance = 0
        firstSegment = True
        
        while len(stack) > 0:
            thisSegment = stack.pop()

            # if there was a site on the first segment, we would catch it in 
            # our first case at the beginning
            # we avoid this if passing on a site below our query on the first segment by checking
            # if this is the first segment we are looking at
            if firstSegment is False:
                for site in reversed(thisSegment.sites):
                    if len(foundSites) < siteLimit:
                        foundSites.append((site, summedDistance + (thisSegment.length - site.distDownstreamAlongSegment)))
                    else:
                        break
                summedDistance += thisSegment.length
            else:
                summedDistance += downStreamPositionOnSegment
            
            if len(foundSites) >= siteLimit:
                break

            #reverse the list. We want the lowest priority tribs to be looked at first
            newBranches = thisSegment.upStreamNode.getSortedUpstreamBranches()
            stack.extend(reversed(newBranches))
            
            #expand graph if necessary 
            thisSegmentPosition = thisSegment.upStreamNode.position
            #if during navigation, we reach edge of safe data boundary, expand with new query
            if autoExpand is True and not self.streamGraph.pointWithinSafeDataBoundary(thisSegmentPosition):
                graphExpansion = self.streamGraph.expandGraph(thisSegmentPosition[1], thisSegmentPosition[0])
                if Failures.isFailureCode(graphExpansion):
                    return graphExpansion
                elif self.terminateSearchOnQuery is True:
                    return Failures.QUERY_TERMINATE_CODE
            
            firstSegment = False

        return (foundSites, summedDistance)
    
    #assume our graph is clean and loop free
    #returns a tuple (siteID, distance traversed to find site)
    # or None if no site is found
    def getNextUpstreamSite (self, segment, downstreamPositionOnSegment):        
        #get the first upstream site
        upstreamSitesInfo = self.collectSortedUpstreamSites(segment, downstreamPositionOnSegment, siteLimit = 1)
        
        #if this failed, return failure code now
        if Failures.isFailureCode(upstreamSitesInfo):
            return upstreamSitesInfo

        upstreamSites = upstreamSitesInfo[0]
        # we are only looking for one upstream site here, but, we only need this distance variable in the case
        # where we don't find any upstream sites and have to backtrack. Thus, in that case, collectSortedUp... will have explored all of the graph
        # upstream from segment
        totalDistance = upstreamSitesInfo[1]

        foundSite = None
        if upstreamSites is not None and len(upstreamSites) > 0:
            foundSite = upstreamSites[0] 

        if foundSite is not None:#we found a site. Great! return it
            #return (siteID, distance upstream to site)
            return (foundSite[0].siteID, foundSite[1])
            #return (foundSite.siteID, summedDistance)
        else:#no site found upstream...
            #find the next major branch by backtracking
            nextUpstreamSegment = self.findNextLowerStreamLevelPath(segment)

            if Failures.isFailureCode(nextUpstreamSegment):
                return nextUpstreamSegment
            else:#we found a mainstream branch!
                if self.debug:
                    print ("successful backtrack. Found next main branch")
                #recursively call this function again starting at the first node of the next mainstream branch
                #the next mainstream branch should be the continuation of our trib in ID space
                #self.streamGraph.visualize()
                newSearch = self.getNextUpstreamSite(nextUpstreamSegment, nextUpstreamSegment.length)
                if Failures.isFailureCode(newSearch):
                    return newSearch
                else:#we found a site in the new search!
                    #we want to return the new site and the distance to it plus the distance upstream along our trib
                    return (newSearch[0], newSearch[1] + totalDistance)

    def getNextDownstreamSite (self, segment, downstreamPositionOnSegment):
        foundSite = None

        for site in segment.sites:
            if site.distDownstreamAlongSegment > downstreamPositionOnSegment:
                foundSite = site
                return (foundSite.siteID, site.distDownstreamAlongSegment - downstreamPositionOnSegment)

        queue = []
        queue.append(segment)

        summedDistance = 0
        firstSegment = True
        while len(queue) > 0:
            current = queue.pop(0)
            currentStreamLevel = current.streamLevel
            
            if firstSegment is False:
                #check to see if the site is on our branch
                if len(current.sites) > 0:
                    foundSite = current.sites[0]
                    summedDistance += current.sites[0].distDownstreamAlongSegment
                    break
                else:
                    #if not, add distance of this segment to total sum
                    summedDistance += current.length
            else:
                #only for first segment: add up length but subtract our relativel position on segment
                summedDistance += current.length - downstreamPositionOnSegment

            adjacentUpstreamPaths = current.downStreamNode.getUpstreamNeighbors()
            higherLevelNeighbors = [] # this means this junction has a trib. Since we're on the main path, we have to explore all the way up the trib
            #get a list of all valid upstream paths. Normally there will only be one
            #but in certain cases there are 3 upstream paths from a node
            for neighbor in adjacentUpstreamPaths:
                if neighbor is current:
                    continue
                if neighbor.streamLevel > currentStreamLevel:
                    higherLevelNeighbors.append(neighbor)
        
            if len(higherLevelNeighbors) > 0:
                totalTribLength = 0
                nearestTribSite = None
                nearestDistUpTrib = 0

                higherLevelNeighborsTribLengths = []
                #find the trib with the nearest site. 
                for higherLevelNeighbor in higherLevelNeighbors:
                    #collect all sites on this tributary
                    tribSitesInfo = self.collectSortedUpstreamSites(higherLevelNeighbor, higherLevelNeighbor.length, siteLimit = sys.maxsize)
                    
                    if Failures.isFailureCode(tribSitesInfo):
                        return tribSitesInfo
                    else:
                        tribSites = tribSitesInfo[0]
                        tribLength = tribSitesInfo[1]
                        higherLevelNeighborsTribLengths.append(tribLength)
                        #find which site is the closest upstream
                        if len(tribSites) > 0:
                            foundSiteInfo = tribSites[-1] #return the highest site on the trib
                            distUpTrib = foundSiteInfo[1]
                            #the farther the site is up the trib, the nearer it is to the main branch in ID space
                            if distUpTrib > nearestDistUpTrib:
                                nearestDistUpTrib = distUpTrib
                                nearestTribSite = foundSiteInfo[0]
                                totalTribLength = tribLength
                            #distance of streams that are higher in the network than the highest site on the trib
                #if there was a site on one of the tribs, break and return
                if nearestTribSite is not None:
                    #distance of streams above the highest site that could have sites higher than nearestTribSite
                    foundSite = nearestTribSite
                    #distUpTrib is the address space distance.. 
                    distanceAboveSite = totalTribLength - distUpTrib
                    summedDistance += distanceAboveSite
                    break
                else:#otherwise, sum total distance of tribs
                    for neighborLength in higherLevelNeighborsTribLengths:
                        summedDistance += neighborLength

            #expand graph, catch failures
            downstreamPoint = current.downStreamNode.position
            if not self.streamGraph.pointWithinSafeDataBoundary(downstreamPoint):
                graphExpansion = self.streamGraph.expandGraph(downstreamPoint[1], downstreamPoint[0])
                if Failures.isFailureCode(graphExpansion):
                    return graphExpansion
                elif self.terminateSearchOnQuery is True:
                    return Failures.QUERY_TERMINATE_CODE

            nextSegments = current.downStreamNode.getDownstreamNeighbors()#getCodedNeighbors(DOWNSTREAM)#most likely only one such segment unless there is a fork in the river
            queue.extend(nextSegments)
            firstSegment = False
            
        if foundSite is not None:
            return (foundSite.siteID, summedDistance)
        else:
            #we searched downstream and found no sites. If we terminated without error thus far it means we reached the end of the network
            return Failures.END_OF_BASIN_CODE

    #get comulative error in site snaps 
    #error is defined by number of times a site that is farther upstream
    #is listed before a site that is farther downstream
    #this error is attributed to bad snaps
    def getGraphSiteIDError (self):
        cumulativeError = 0
        sinks = self.streamGraph.getSinks()
        for sink in sinks:
            upstreamPaths = sink.getUpstreamNeighbors()#getCodedNeighbors(UPSTREAM)
            for path in upstreamPaths:
                #collect all upstream sites without expanding the graph
                #we do verification and error checking only on the part of the graph that has
                #been expanded thus far
                upstreamSites = self.collectSortedUpstreamSites(path, path.length, siteLimit = sys.maxsize, autoExpand = False)[0]
                prevNumber = sys.maxsize
                for site in upstreamSites:
                    #we have to index this with [0] since collectSortedUpst.. returns a tuple like (siteID, distUpstream)
                    siteID = site[0].siteID
                    #normalize siteID to full 10 digits
                    if len(siteID) < 10:
                        siteID += "00"
                    #get int representing the downstream address
                    downStreamNumber = int(siteID[2:])
                    if downStreamNumber > prevNumber:
                        cumulativeError += 1
                    prevNumber = downStreamNumber 
        return cumulativeError

    #update in progress stream searches based on a change to the graph
    #If we don't do this step, as we expand the graph mid-search, the graph cleaning process will remove 
    # segments we may be actively looking at. These removed segments no longer will have connections to our graph
    # thus terminating the search early. 
    def notify(self, update):
        for search in self.activeSearches.values():
            openSegs = search.openSegments
            for i, segment in enumerate(openSegs):
                if update.fromSeg is segment:
                    openSegs[i] = update.toSeg
            #remove duplicates
            for i, segment in reversed(list(enumerate(openSegs))):
                if openSegs.index(segment) != i:
                    openSegs.pop(i)

