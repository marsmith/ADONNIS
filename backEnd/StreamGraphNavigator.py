import sys
import Failures
#a class that has various functionality to navigate the graph of a stream graph. Will autoexpand the graph 
#at edges when a search runs into the edge of the graph
class StreamGraphNavigator (object):

    def __init__(self, streamGraph, terminateSearchOnQuery = False, debug = False):
        self.streamGraph = streamGraph
        self.terminateSearchOnQuery = terminateSearchOnQuery
        self.debug = debug

    #navigate downstream until a path with lower streamlevel is found. This function returns the first segment
    #directly upstream from the junction of the main path and the tributary that 'segment' is on
    def findNextLowerStreamLevelPath (self, segment, expand=True):
        tribLevel = segment.streamLevel

        queue = []
        queue.append(segment)

        nextMainPath = None
        while len(queue) > 0:
            current = queue.pop(0)
            if current.streamLevel < tribLevel:
                #if we find a lower stream level it is downstream from the trib we started on
                # so to find the next main stream path, we have to go up from this segment along the matching streamlevel neighbor
                upstreamNeighbors = current.upStreamNode.getUpstreamNeighbors()
                for neighbor in upstreamNeighbors:
                    if neighbor.streamLevel == current.streamLevel:
                        nextMainPath = neighbor
                        break
            else:
                downstreamPoint = current.downStreamNode.position
                if not self.streamGraph.pointWithinSafeDataBoundary (downstreamPoint) and expand:
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
            foundSite = upstreamSites[0] #get the first upstream site / distance tuple

        if foundSite is not None:#we found a site. Great! return it
            #return (siteID, distance upstream to site)
            return (foundSite[0], foundSite[1])
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
                return (foundSite, site.distDownstreamAlongSegment - downstreamPositionOnSegment)

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
            return (foundSite, summedDistance)
        else:
            #we searched downstream and found no sites. If we terminated without error thus far it means we reached the end of the network
            return Failures.END_OF_BASIN_CODE


    def getNamedTribMouths (self):
        mouths = []
        for segment in self.streamGraph.segments.values():
            if segment.streamName == "":
                continue
            downstreamNeighbors = segment.downStreamNode.getDownstreamNeighbors()
            isMouth = False
            for neighbor in downstreamNeighbors:
                if neighbor.streamLevel < segment.streamLevel:
                    isMouth = True
                    break
            if isMouth:
                mouths.append((segment.streamName, segment.downStreamNode.position))
        return mouths