from StreamGraph import StreamNode, StreamSegment, StreamGraph, UPSTREAM, DOWNSTREAM
from collections import namedtuple 
from sys import maxsize
#a class that has various functionality to find / expand a StreamGraph

StreamSearch = namedtuple('StreamSearch', 'id openSegments')

class StreamGraphNavigator (object):

    def __init__(self, streamGraph):
        self.streamGraph = streamGraph
        self.activeSearches = {}
        self.nextSearchId = 0
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
        #request a new safe array that will respond to updates in the stream graph
        streamSearch = self.openSearch()
        queue = streamSearch.openSegments
        queue.append(segment)

        nextMainPath = None

        while len(queue) > 0:
            current = queue.pop(0)
            if current.streamLevel < tribLevel:
                #if we find a lower stream level it is downstream from the trib we started on
                # so to find the next main stream path, we have to go up from this segment along the matching streamlevel neighbor
                upstreamNeighbors = current.upStreamNode.getCodedNeighbors(UPSTREAM)
                for neighbor in upstreamNeighbors:
                    if neighbor.streamLevel == current.streamLevel:
                        nextMainPath = neighbor
                        break
            else:
                downstreamPoint = current.downStreamNode.position
                if not self.streamGraph.pointWithinSafeDataBoundary (downstreamPoint):
                    self.streamGraph.expandGraph(downstreamPoint)
                nextSegments = current.downStreamNode.getCodedNeighbors(DOWNSTREAM)#most likely only one such segment unless there is a fork in the river
                queue.extend(nextSegments)
        
        # close this search
        self.closeSearch(streamSearch.id)

        return nextMainPath

    # get a sorted list of all upstream sites from 'segment'
    # list is sorted such that sites with higher IDS (closer to the mouth of the river) are first
    # if there are no upstreamSites, returns (None, lengthOfUpstreamSegments)
    def collectSortedUpstreamSites (self, segment, downStreamPositionOnSegment, siteLimit = 1):
        # contains tuples of the form (site, dist to site)
        foundSites = []

        # reverse order of segment.sites since normally it is ordered upstream->downstream
        # since we are collecting sites from downstream->upstream
        for site in reversed(segment.sites):
            if site.distDownstreamAlongSegment < downStreamPositionOnSegment and len(foundSites) < siteLimit:
                foundSites.append((site, downStreamPositionOnSegment - site.distDownstreamAlongSegment)) 

        if len(foundSites) >= siteLimit:
            return foundSites

        #get upstream tributaries of this path
        streamSearch = self.openSearch()
        stack = streamSearch.openSegments
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
            if not self.streamGraph.pointWithinSafeDataBoundary(thisSegmentPosition):
                self.streamGraph.expandGraph(thisSegmentPosition)
            
            firstSegment = False

        # close this search
        self.closeSearch(streamSearch.id)


        return foundSites
        """ if len(foundSites) == 0:
            foundSites.append((None, summedDistance)) """
    
    #assume our graph is clean and loop free
    #returns a tuple (siteID, distance traversed to find site)
    # or None if no site is found
    def getNextUpstreamSite (self, segment, downstreamPositionOnSegment):        
        #get the first upstream site
        upstreamSites = self.collectSortedUpstreamSites(segment, downstreamPositionOnSegment, siteLimit = 1)

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
            if nextUpstreamSegment is None:#there is no other mainstream branches. We are currently on a segment that terminates
                print ("no paths whatsoever upstream")
                return None
            else:#we found a mainstream branch!
                print ("successful backtrack. Found next main branch")
                #recursively call this function again starting at the first node of the next mainstream branch
                #the next mainstream branch should be the continuation of our trib in ID space
                #self.streamGraph.visualize()
                newSearch = self.getNextUpstreamSite(nextUpstreamSegment, nextUpstreamSegment.length)
                if newSearch is not None:#we found a site in the new search!
                    #we want to return the new site and the distance to it plus the distance upstream along our trib
                    return (newSearch[0], newSearch[1] + segment.arbolateSum - (segment.length - downstreamPositionOnSegment))
                else:#no sites found on that path either. Return None for real
                    return None
            return None

    def getNextDownstreamSite (self, segment, downstreamPositionOnSegment):

        foundSite = None

        for site in segment.sites:
            if site.distDownstreamAlongSegment > downstreamPositionOnSegment:
                foundSite = site
                return foundSite


        streamSearch = self.openSearch()
        queue = streamSearch.openSegments
        queue.append(segment)

        while len(queue) > 0:
            current = queue.pop(0)
            currentStreamLevel = current.streamLevel
            adjacentUpstreamPaths = current.downStreamNode.getCodedNeighbors(UPSTREAM)
            higherLevelNeighbor = None # this means this junction has a trib. Since we're on the main path, we have to explore all the way up the trib
            for neighbor in adjacentUpstreamPaths:
                if neighbor is current:
                    continue
                if neighbor.streamLevel > currentStreamLevel:
                    higherLevelNeighbor = neighbor
            
            if higherLevelNeighbor is not None:
                tribSites = collectSortedUpstreamSites(higherLevelNeighbor, higherLevelNeighbor.length, siteLimit = sys.maxsize)
                if len(tribSites) > 0:
                    return 

            downstreamPoint = current.downStreamNode.position
            if not self.streamGraph.pointWithinSafeDataBoundary (downstreamPoint):
                self.streamGraph.expandGraph(downstreamPoint)
            nextSegments = current.downStreamNode.getCodedNeighbors(DOWNSTREAM)#most likely only one such segment unless there is a fork in the river
            queue.extend(nextSegments)
        
        # close this search
        self.closeSearch(streamSearch.id)

        return nextMainPath

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

