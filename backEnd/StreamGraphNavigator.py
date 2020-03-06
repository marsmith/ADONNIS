from StreamGraph import StreamNode, StreamSegment, StreamGraph, UPSTREAM, DOWNSTREAM
from collections import namedtuple 

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

    def findNextLowerStreamLevel (self, segment):
        currentLevel = segment.streamLevel

    #assume our graph is clean and loop free
    #returns a tuple (siteID, distance traversed to find site)
    # or None if no site is found
    def getNextUpstreamSite (self, segment, downStreamPositionOnSegment):
        #catch cases when next node is simply on this node
        foundSite = segment.getSiteAbove(downStreamPositionOnSegment) 
        #if there is a site on this segment, simply return it
        if foundSite is not None:
            return (foundSite.siteID, downStreamPositionOnSegment - foundSite.distDownstreamAlongSegment) 

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
            if len(thisSegment.sites) > 0 and firstSegment is False:
                #the site we want is the farthest downstream on this segment
                siteInfo = thisSegment.sites[-1]
                foundSite = siteInfo
                summedDistance += thisSegment.length - siteInfo.distDownstreamAlongSegment
                break
            else:
                summedDistance += thisSegment.length
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

        if foundSite is not None:
            return (foundSite.siteID, summedDistance)
        else:
            return None

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

