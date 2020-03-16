from collections import namedtuple
from GDALData import GDALData, RESTRICTED_FCODES, QUERYDATA
from Helpers import *
from SnapSites import Snap, SnappedSite
import ogr
import matplotlib.pyplot as plt
import random
import sys

#constants for neighbor relationships
UNKNOWN = 0         #000
UPSTREAM = 1        #001 a one in the one's place means upstream
UPSTREAMTRIB = 3    #011 contains a one in the one's place, but also contains a 1 in the two's place, indicating upstream and a trib
DOWNSTREAM = 4      #100 contains a one in the four's place indicating a downstream site 




#tuples used
NeighborRelationship = namedtuple('NeighborRelationship', 'segment relationship')
SiteOnSegment = namedtuple('SiteOnSegment', 'distDownstreamAlongSegment siteID')
GraphUpdate = namedtuple('GraphUpdate', 'fromSeg toSeg')#an update to the graph. 'from' is replaced with 'to' 

#a stream node 
class StreamNode (object):
    def __init__(self, position, instanceID = 0):
        #streamNodes get 1 appended on the FID to ensure uniqueness
        self.neighbors = []
        self.position = position
        self.instanceID = instanceID        

    def addNeighbor (self, segment, relationship = UNKNOWN):
        self.neighbors.append(NeighborRelationship(segment=segment, relationship=relationship))

    def neighborHasRelationShip(self, neighborTuple, relationship):
        if neighborTuple.relationship & relationship == relationship:
            return True
        return False

    def getCodedNeighbors (self, relationshipCode):
        results = []
        for neighbor in self.neighbors:
            #does the relationship contain this flag
            if self.neighborHasRelationShip(neighbor, relationshipCode):
                results.append(neighbor.segment)
        return results

    # returns a list of upstream branches of this node sorted by arbolate sum (upstream distance) 
    # the order will be:
    # lowest arbolate sum first, followed by the mainstream branch
    def getSortedUpstreamBranches (self):
        tribs = []
        minStreamLevel = float("inf")
        for neighbor in self.neighbors:
            if self.neighborHasRelationShip(neighbor, UPSTREAM) and neighbor.segment.streamLevel < minStreamLevel:
                minStreamLevel = neighbor.segment.streamLevel
        mainStreamPathSegment = None
        #once we determine the minimum segment stream level, all stream levels > are tribs
        for neighbor in self.neighbors:
            if self.neighborHasRelationShip(neighbor, UPSTREAM):
                if neighbor.segment.streamLevel > minStreamLevel:
                    tribs.append(neighbor.segment)
                else:
                    mainStreamPathSegment = neighbor.segment

        sortedTribs = sorted(tribs, key=lambda tribSegment: tribSegment.arbolateSum)
        #catch case when there is no upstream path at all
        if mainStreamPathSegment is not None:
            sortedTribs.append(mainStreamPathSegment)

        return sortedTribs
    
    #removes the neighbor with neighborID if it exists. Return true if removed successfully
    def removeNeighbor (self, segment):
        for i, neighbor in enumerate(self.neighbors):
            if neighbor.segment.segmentID == segment.segmentID:
                self.neighbors.pop(i)
                return True
        return False

    def numNeighbors(self):
        return len(self.neighbors)

#a segment connecting two points
class StreamSegment (object):
    def __init__(self, upStreamNode, downStreamNode, ID, length, streamLevel, arbolateSum):
        #streamSegments get 0 appended on the FID to ensure uniqueness
        self.upStreamNode = upStreamNode
        self.downStreamNode = downStreamNode
        self.segmentID = ID
        self.sites = []
        self.length = length
        self.streamLevel = streamLevel
        self.arbolateSum = arbolateSum

    #we assume that this site position is indeed on our segment. 
    #distAlongSegment = 0 would imply that the site is located at upStreamNode
    #similarly, distAlongSegment = self.length wouold imply it is located at downStreamNode
    def addSite (self, siteID, distAlongSegment):
        if distAlongSegment > self.length:
            print ("Site added to segment on point that exceeds segment length. This shouldn't happen!")
            print (self.segmentID)

        self.sites.append(SiteOnSegment(siteID = siteID, distDownstreamAlongSegment = distAlongSegment))
        self.sites = sorted(self.sites, key=lambda site: site.distDownstreamAlongSegment)

    #gets the nearest site ID on THIS segment above 'distanceDownSegment' if it exists. return none otherwise 
    def getSiteAbove (self, distanceDownSegment):
        #list sites by order downstream to upstream
        reverseSortedSites = reversed(self.sites)
        #the first site we find in the above list that is farther upstream than 'distanceDownSegment' is a match
        for site in reverseSortedSites:
            if site.distDownstreamAlongSegment < distanceDownSegment:
                return site
        return None
    
    def getPointOnSegment (self, distDownstreamAlongSegment):
        percent = distDownstreamAlongSegment / self.length

        pointX = percent * self.downStreamNode.position[0] + (1 - percent) * self.upStreamNode.position[0]
        pointY = percent * self.downStreamNode.position[1] + (1 - percent) * self.upStreamNode.position[1]

        return (pointX, pointY)

class StreamGraph (object):

    def __init__(self):
        self.segments = {}
        self.nodes = []
        self.safeDataBoundary = [] #gdal geometry objects. Points inside should have all neighboring segments stored

        self.removedSegments = {}#cleaned segments. keep track to prevent duplicates. The dict values point to the segment that replaced this segment, if it exists
        self.addedSites = set()#list of sites that have already been added
        self.nextNodeID = 0#local ID counter for stream nodes. Just a simple way of keeping track of nodes. This gets incremented
        self.listeners = []

    def addGraphListener(self, listener):
        self.listeners.append(listener)

    #make sure that all listeners have a notify method
    #notify listeners of a single update
    def notifyListeners(self, update):
        for listener in self.listeners:
            listener.notify(update)

    #visualize the graph using matplotlib
    def visualize(self, showSegInfo = False, customPoints = []):
        sitesX = []
        sitesY = []
        for streamSeg in self.segments.values():
            startPt = streamSeg.upStreamNode.position
            endPt = streamSeg.downStreamNode.position

            x = [startPt[0], endPt[0]]
            y = [startPt[1], endPt[1]]
            dx = endPt[0] - startPt[0]
            dy = endPt[1] - startPt[1]
            plt.arrow(startPt[0], startPt[1], dx, dy, width=0.00001, head_width = 0.0001, color='blue', length_includes_head=True)

            plt.plot(x,y, lineWidth=1, color='blue')

            midPoint = (startPt[0]/2 + endPt[0]/2, startPt[1]/2 + endPt[1]/2)

            #plt.text(midPoint[0], midPoint[1], streamSeg.streamLevel, fontsize = 8)
            #plt.text(midPoint[0], midPoint[1]-100, streamSeg.arbolateSum, fontsize = 8)

            for i, sites in enumerate(streamSeg.sites):
                percentAlongSegment = sites.distDownstreamAlongSegment / streamSeg.length
                percentAlongSegmentInverse = 1 - percentAlongSegment

                position = (startPt[0] * percentAlongSegmentInverse + endPt[0] * percentAlongSegment, startPt[1] * percentAlongSegmentInverse + endPt[1] * percentAlongSegment)
                sitesX.append(position[0])
                sitesY.append(position[1])
                plt.text(position[0] + 0.0001, position[1] + 0.001 + i * 0.001, sites.siteID, fontsize = 8, color = 'red')

            segmentInfo = streamSeg.streamLevel
            if showSegInfo is True:
                segmentInfo = str(streamSeg.segmentID) + "\n" + str(round(streamSeg.length, 2)) + "\n" + str(streamSeg.streamLevel)
            plt.text(midPoint[0], midPoint[1], segmentInfo, fontsize = 8)
        
        x = []
        y = []
        for streamNode in self.nodes:
            x.append(streamNode.position[0])
            y.append(streamNode.position[1])
            #plt.text(streamNode.position[0], streamNode.position[1], streamNode.instanceID, fontsize = 8)
        plt.scatter(x,y, color='green')

        plt.scatter(sitesX, sitesY, color='red')


        x = []
        y = []

        for pt in customPoints:
            x.append(pt[0])
            y.append(pt[1])

        plt.scatter(x,y, color='black')

        #display safe boundary polygon
        for geom in self.safeDataBoundary:
            for ring in geom:
                numPoints = ring.GetPointCount()
                x = []
                y = []
                for i in range(0, numPoints):
                    point = ring.GetPoint(i)
                    x.append(point[0])
                    y.append(point[1])
                plt.plot(x,y, lineWidth=1, color='red')

        plt.show()

    #expand the graph at x,y with queried data 
    def expandGraph (self, point):
        print ("Expanding graph!")
        gdalData = GDALData(point[1], point[0], loadMethod = QUERYDATA)
        self.addGeom(gdalData)

    """ #assume our graph is clean and loop free
    #returns a tuple (siteID, distance traversed to find site)
    # or None if no site is found
    def getNextUpstreamSite (self, segment, downStreamPositionOnSegment):
        #catch cases when next node is simply on this node
        foundSite = segment.getSiteAbove(downStreamPositionOnSegment) 
        #if there is a site on this segment, simply return it
        if foundSite is not None:
            return (foundSite.siteID, downStreamPositionOnSegment - foundSite.distDownstreamAlongSegment) 

        #get upstream tributaries of this path
        stack = [segment]
        summedDistance = 0
        firstSegment = True
        while len(stack) > 0:
            thisSegment = stack.pop()
            if thisSegment.segmentID == "9281127CC":
                print("test")

            thisSegmentPosition = thisSegment.downStreamNode.position
            #if during navigation, we reach edge of safe data boundary, expand with new query
            if not self.pointWithinSafeDataBoundary(thisSegmentPosition):
                self.expandGraph(thisSegmentPosition) 
            
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
            stack.extend(reversed(thisSegment.upStreamNode.getSortedUpstreamBranches()))
            firstSegment = False

        if foundSite is not None:
            return (foundSite.siteID, summedDistance)
        else:
            return None """


    #safely remove a segment from the graph
    def removeSegment (self, segment, replacedBy = None):
        segmentID = segment.segmentID
        if segmentID in self.segments:
            segment.upStreamNode.removeNeighbor(segment)
            segment.downStreamNode.removeNeighbor(segment)
            #for neighbor in segment
            del self.segments[segmentID]
            self.removedSegments[segmentID] = replacedBy
    
    #add a segment to the graph
    def addSegment (self, upstreamNode, downstreamNode, segmentID, length, streamLevel, arbolateSum):
        newSegment = StreamSegment(upstreamNode, downstreamNode, segmentID, length, streamLevel, arbolateSum)    
        #add the new segment to the dictionary
        self.segments[segmentID] = newSegment
        #from the perspective of the upstream node, this segment is downstream and vice versa
        upstreamNode.addNeighbor(newSegment, DOWNSTREAM)
        downstreamNode.addNeighbor(newSegment, UPSTREAM)

        return newSegment

    def addNode (self, position):
        newNode = StreamNode(position, self.nextNodeID)
        self.nodes.append(newNode)
        self.nextNodeID += 1
        return newNode

    def addSite (self, siteID, segmentID, distAlongSegment):
        if siteID not in self.addedSites:
            self.segments[segmentID].addSite(siteID, distAlongSegment)
            self.addedSites.add(siteID)
    #has this graph ever contained this segment?
    #used when adding new segments to prevent duplicates
    def hasContainedSegment (self, segmentID):
        if segmentID in self.segments or segmentID in self.removedSegments:
            return True
        else:
            return False

    #Get a list of nodes that have no downstream connection. A lot of these nodes will be outside of the safe zone, but they can be used to traverse 
    #the entire graph since every node must be upstream from a sink
    def getSinks (self):
        sinks = []
        for node in self.nodes:
            if len(node.getCodedNeighbors(DOWNSTREAM)) == 0:
                sinks.append(node)
        return sinks
    
    def pointWithinSafeDataBoundary (self, point):
        pointGeo = ogr.Geometry(ogr.wkbPoint)
        pointGeo.AddPoint(point[0], point[1])
        for geo in self.safeDataBoundary:
            if pointGeo.Within(geo):
                return True
        return False


    def removeLoops (self):
        #close all loops upstream of 'sinkNode'
        #do a breadth first search from a sink
        #all nodes must be upstream of SOME sink. So, running BFS from all sinks covers all nodes
        # logic: run BFS, if we ever encounter a node that we've already seen, this is a loop, so we disconnect the segment that 
        # connects the segment in question to the node we've already seen. Thus closing the loop

        def closeLoops (sinkNode):
            frontier = [sinkNode]
            discovered = [sinkNode]
            while len(frontier) > 0:
                nextNode = frontier.pop(0)
                # skip nodes that aren't within the safe data boundary. These nodes could be missing neighbors
                # thus causing our algo to potentially not be deterministic 
                """ if not self.pointWithinSafeDataBoundary(nextNode.position):
                    continue """
                #we want to use a formal parameter to sort neighbor priority to make sure this algorithm is deterministic 
                sortedNeighbors = sorted(nextNode.neighbors, key=lambda neighbor: neighbor.segment.length)

                # sort in reverse since within this loop we may remove a segment. Since we are looping over segments that can cause trouble
                for neighbor in reversed(sortedNeighbors):
                    #this neighbor has an upstream relationship
                    if nextNode.neighborHasRelationShip(neighbor, UPSTREAM):
                        upstreamNode = neighbor.segment.upStreamNode
                        if upstreamNode not in discovered:
                            frontier.append(upstreamNode)
                            discovered.append(upstreamNode)
                        else:
                            # this neighbor branch takes us to a node we've already seen
                            # so disconnect this edge from that node to remove loop
                            thisPosition = nextNode.position
                            connectionPosition = neighbor.segment.upStreamNode.position
                            newEndPointNodePos = ((thisPosition[0] + connectionPosition[0])/2, (thisPosition[1] + connectionPosition[1])/2)
                            newEndPointNode = self.addNode(newEndPointNodePos)
                            newEndPointNode.addNeighbor(neighbor.segment, DOWNSTREAM) # our segment is downstream from the new segment
                            neighbor.segment.upStreamNode.removeNeighbor(neighbor.segment)
                            neighbor.segment.upStreamNode = newEndPointNode

        sinks = self.getSinks()
        #remove loops
        for sink in sinks:
            closeLoops(sink)

    #collapse redundant nodes with only two neighbors
    def cleanGraph (self):
        queue = []
        for node in self.nodes:
            hasUpstream = len(node.getCodedNeighbors(UPSTREAM)) > 0
            hasDownstream = len(node.getCodedNeighbors(DOWNSTREAM)) > 0
            #ensure that the node only hs two neighbors, one upstream, one downstream,
            if node.numNeighbors() == 2 and hasUpstream and hasDownstream and self.pointWithinSafeDataBoundary(node.position):
                queue.append(node)  
        
        while len(queue) > 0:
            node = queue.pop()
            #getCodedNeighbors returns an array since you can have multiple tributaries
            #but in this case, there are only two, so it must only be a single upstream and downstream
            upstreamSegment = node.getCodedNeighbors(UPSTREAM)[0]
            downstreamSegment = node.getCodedNeighbors(DOWNSTREAM)[0]

            newSegmentUpstreamNode = upstreamSegment.upStreamNode
            newSegmentDownstreamNode = downstreamSegment.downStreamNode   

            


            #calculate new segment properties
            newLength = upstreamSegment.length + downstreamSegment.length
            # concat IDs to get a new unique ID
            newID = str(downstreamSegment.segmentID) + "C"
            #the two segments being collapsed should have the same stream level
            newStreamLevel = downstreamSegment.streamLevel
            #since arbolate sum is distance upstream from the most downstream point of a segment, 
            #choosing arbolate sum of downstream segment is accurate for the collapsed segment
            newArbolateSum = downstreamSegment.arbolateSum

            newSegment = self.addSegment(newSegmentUpstreamNode, newSegmentDownstreamNode, newID, newLength, newStreamLevel, newArbolateSum)    

            #add the sites to the new segment
            for site in upstreamSegment.sites:
                newSegment.addSite(site.siteID, site.distDownstreamAlongSegment) 
            #for the downstream segment, we must add the length of the upstream segment to get an accurate distance downstream segment number
            for site in downstreamSegment.sites:
                newSegment.addSite(site.siteID, site.distDownstreamAlongSegment + upstreamSegment.length) 

            #remove the segment and nodes from the actual graph
            for neighbor in reversed(node.neighbors):
                #update listeners about this simplification. The two removed segments now will be replaced
                # with the simplified segment in any active searches
                self.notifyListeners(GraphUpdate(fromSeg = neighbor.segment, toSeg=newSegment))
                self.removeSegment(neighbor.segment, replacedBy = newSegment)
                
            self.nodes.remove(node)

    
    #get a segment from the graph or if it was deleted, get the segment that replaced it
    def getCleanedSegment (self, segmentID):
        if segmentID in self.segments:
            return self.segments[segmentID]
        elif segmentID in self.removedSegments:
            return self.getCleanedSegment(self.removedSegments[segmentID].segmentID)
        else:
            return None

    #use for testing to remove a site and re add it
    def removeSite (self, siteID):
        for segment in self.segments.values():
            for site in segment.sites:
                if site.siteID == siteID:
                    del segment.sites[site]


    #Adds the geometry stored in the gdalData object
    #gdalData: ref to a gdalData object
    #guaranteedNetLineIndex a streamline feature that is definitely on the network we are interested in
    def addGeom(self, gdalData):
        lineLayer = gdalData.lineLayer
        objectIDIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")
        lengthIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("LENGTHKM")
        fCodeIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("FCode")
        streamLevelIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("STREAMLEVE")
        arbolateSumIndex = gdalData.lineLayer.GetLayerDefn().GetFieldIndex("ARBOLATESU")

        for line in lineLayer:
            #don't add duplicates
            segmentID = line.GetFieldAsString(objectIDIndex)
            length = float(line.GetFieldAsString(lengthIndex))
            fCode = int(line.GetFieldAsString(fCodeIndex))
            streamLevel = int(line.GetFieldAsString(streamLevelIndex))
            arbolateSum = float(line.GetFieldAsString(arbolateSumIndex))
            if self.hasContainedSegment(segmentID) or fCode in RESTRICTED_FCODES:
                continue

            geom = line.GetGeometryRef()

            upstreamPt = geom.GetPoint(0)
            numPoints = geom.GetPointCount()
            downstreamPt = geom.GetPoint(numPoints-1)

            upstreamNode = None
            downstreamNode = None

            #see if existing nodes exist that connect to this segment
            for node in self.nodes:
                if pointsEqual (upstreamPt, node.position):
                    upstreamNode = node
                elif pointsEqual (downstreamPt, node.position):
                    downstreamNode = node
            
            #create new nodes if non were found
            if upstreamNode == None:
                upstreamNode = self.addNode(upstreamPt)
            if downstreamNode == None:
                downstreamNode = self.addNode(downstreamPt)

            self.addSegment(upstreamNode, downstreamNode, segmentID, length, streamLevel, arbolateSum)

        siteLayer = gdalData.siteLayer
        siteNumberIndex = siteLayer.GetLayerDefn().GetFieldIndex("site_no")

        snapped = Snap(gdalData)

        for siteSnap in snapped:
            snapPosition = siteSnap.snappedLocation
            snapFeature = siteSnap.snappedFeature
            featureSegmentID = snapFeature.GetFieldAsString(objectIDIndex)
            siteIDIndex = siteSnap.site.GetFieldAsString(siteNumberIndex)
            
            self.addSite(siteIDIndex, featureSegmentID, siteSnap.distAlongFeature)

        self.safeDataBoundary.append(gdalData.safeDataBoundary)


        self.removeLoops()
        #self.cleanGraph()



