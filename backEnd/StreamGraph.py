from collections import namedtuple
from GDALData import RESTRICTED_FCODES, BaseData, loadFromQuery
from Helpers import *
from SnapSites import snapPoint, SnapablePoint, Snap, getSiteSnapAssignment
import ogr
import matplotlib.pyplot as plt
import sys
import copy
import Failures

#constants for neighbor relationships
UNKNOWN = 0         #000
UPSTREAM = 1        #001 a one in the one's place means upstream
UPSTREAMTRIB = 3    #011 contains a one in the one's place, but also contains a 1 in the two's place, indicating upstream and a trib
DOWNSTREAM = 4      #100 contains a one in the four's place indicating a downstream site 


#tuples used
NeighborRelationship = namedtuple('NeighborRelationship', 'segment relationship')
GraphSite = namedtuple('GraphSite', 'distDownstreamAlongSegment siteID segmentID snapDist nameMatch generalWarnings assignmentWarnings')

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

    def getUpstreamNeighbors(self):
        return self.getCodedNeighbors(UPSTREAM)

    def getDownstreamNeighbors(self):
        return self.getCodedNeighbors(DOWNSTREAM)

    def getCodedNeighbors (self, relationshipCode):
        results = []
        for neighbor in self.neighbors:
            #does the relationship contain this flag
            if self.neighborHasRelationShip(neighbor, relationshipCode):
                results.append(neighbor.segment)
        return results

    # returns a list of upstream branches of this node sorted by stream level 
    # the order will be:
    # tribs, sorted by arbolate sum first, followed by the mainstream branch
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
    def __init__(self, upStreamNode, downStreamNode, ID, length, streamLevel, arbolateSum, streamName):
        #streamSegments get 0 appended on the FID to ensure uniqueness
        self.upStreamNode = upStreamNode
        self.downStreamNode = downStreamNode
        self.segmentID = ID
        self.sites = []
        self.length = length
        self.streamLevel = streamLevel
        self.arbolateSum = arbolateSum
        self.streamName = streamName

    #we assume that this site position is indeed on our segment. 
    #distAlongSegment = 0 would imply that the site is located at upStreamNode
    #similarly, distAlongSegment = self.length wouold imply it is located at downStreamNode
    def addSite (self, siteID, distAlongSegment):

        self.sites.append(GraphSite(siteID = siteID, distDownstreamAlongSegment = distAlongSegment, segmentID = self.segmentID, snapDist = 0))
        self.sites = sorted(self.sites, key=lambda site: site.distDownstreamAlongSegment)
    
    def addGraphSite(self, graphSite):
        self.sites.append(graphSite)
        self.sites = sorted(self.sites, key=lambda site: site.distDownstreamAlongSegment)


    def isNeighbor (self, otherSegmentID):
        isNeighbor = False
        upstreamConnections = self.upStreamNode.neighbors
        downstreamConnections = self.downStreamNode.neighbors
        for neighbor in upstreamConnections:
            segment = neighbor.segment
            if segment.segmentID == otherSegmentID:
                isNeighbor = True
                break
        if isNeighbor is True:
            return True
        
        for neighbor in downstreamConnections:
            segment = neighbor.segment
            if segment.segmentID == otherSegmentID:
                isNeighbor = True
                break
        if isNeighbor is True:
            return True
        return False
        
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

    def __init__(self, withheldSites = [], debug = False, warningLog = None):
        self.segments = {}
        self.nodes = []
        self.safeDataBoundary = [] #gdal geometry objects. Points inside should have all neighboring segments stored

        self.removedSegments = {}#cleaned segments. keep track to prevent duplicates. The dict values point to the segment that replaced this segment, if it exists
        self.siteSnaps = {}#list of sites that have already been added
        self.nextNodeID = 0#local ID counter for stream nodes. Just a simple way of keeping track of nodes. This gets incremented
        self.withheldSites = withheldSites
        self.debug = debug
        self.warningLog = warningLog
        self.currentAssignmentWarnings = []

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
            plt.arrow(startPt[0], startPt[1], dx, dy, width=0.000001, head_width = 0.00001, color='blue', length_includes_head=True)

            plt.plot(x,y, lineWidth=0.5, color='blue')

            midPoint = (startPt[0]/2 + endPt[0]/2, startPt[1]/2 + endPt[1]/2)

            #plt.text(midPoint[0], midPoint[1], streamSeg.streamLevel, fontsize = 8)
            #plt.text(midPoint[0], midPoint[1]-100, streamSeg.arbolateSum, fontsize = 8)

            for i, sites in enumerate(streamSeg.sites):
                percentAlongSegment = sites.distDownstreamAlongSegment / streamSeg.length
                percentAlongSegmentInverse = 1 - percentAlongSegment

                position = (startPt[0] * percentAlongSegmentInverse + endPt[0] * percentAlongSegment, startPt[1] * percentAlongSegmentInverse + endPt[1] * percentAlongSegment)
                sitesX.append(position[0])
                sitesY.append(position[1])
                plt.text(position[0], position[1] + 0.00001 * i, sites.siteID, fontsize = 8, color = 'red')

            segmentInfo = streamSeg.streamLevel
            if showSegInfo is True:
                segmentInfo = str(streamSeg.segmentID) + "\n" + str(round(streamSeg.length, 2)) + "\n" + str(streamSeg.streamLevel) + "\n" + str(streamSeg.arbolateSum)
            plt.text(midPoint[0], midPoint[1], segmentInfo, fontsize = 8)
        
        """ x = []
        y = []
        for streamNode in self.nodes:
            x.append(streamNode.position[0])
            y.append(streamNode.position[1])
            #plt.text(streamNode.position[0], streamNode.position[1], streamNode.instanceID, fontsize = 8)
        plt.scatter(x,y, color='green') """

        plt.scatter(sitesX, sitesY, color='red')


        x = []
        y = []

        for pt in customPoints:
            x.append(pt[0])
            y.append(pt[1])
            plt.text(pt[0], pt[1], "CUSTOM PT", fontsize=10, color = 'black')

        plt.scatter(x,y, color='black')

        x = []
        y = []

        sinks = self.getSinks()
        for sink in sinks:
            x.append(sink.position[0])
            y.append(sink.position[1])
        plt.scatter(x,y, color='green')

        #display safe boundary polygon
        for j, geom in enumerate(self.safeDataBoundary):
            for ring in geom:
                numPoints = ring.GetPointCount()
                x = []
                y = []
                for i in range(0, numPoints):
                    point = ring.GetPoint(i)
                    x.append(point[0])
                    y.append(point[1])
                if j == 0:
                    plt.plot(x,y, lineWidth=1.5, color='green')
                else:
                    plt.plot(x,y, lineWidth=1, color='red')

        plt.show()

    #expand the graph at x,y with queried data. Return true if successful
    def expandGraph (self, lat, lng):
        if self.debug:
            print ("Expanding graph!")
        baseData = loadFromQuery(lat, lng)    
        if Failures.isFailureCode(baseData):
            if self.debug:
                print ("could not expand graph")
            return baseData
        self.addGeom(baseData)
        return True

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
    def addSegment (self, upstreamNode, downstreamNode, segmentID, length, streamLevel, arbolateSum, streamName):
        newSegment = StreamSegment(upstreamNode, downstreamNode, segmentID, length, streamLevel, arbolateSum, streamName)    
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

    def addSiteSnaps (self, siteID, snapInfo):
        if siteID not in self.siteSnaps and siteID not in self.withheldSites:
            #snapInfo is a list of possible snaps. Each element is of type snap from SnapSites.py
            self.siteSnaps[siteID] = snapInfo

    def addSite (self, segmentID, siteID, distDownstreamAlongSegment):
        self.segments[segmentID].addSite(siteID, distDownstreamAlongSegment)
    
    def addGraphSite (self, graphSite):
        self.segments[graphSite.segmentID].addGraphSite(graphSite)

    #given a list of assignments (siteID, snapInfo), clear/update all segments
    def refreshSiteSnaps (self, snapAssignments):
        #collections.namedtuple('Snap', 'featureObjectID snapDistance distAlongFeature')
        #start by removing old sites
        for segment in self.segments.values():
            segment.sites.clear()

        #add sites to segments
        for assignment in snapAssignments:
            self.addGraphSite(assignment)
            
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
    
    #checks if a point is within a safe distance from the center of some query
    def pointWithinSafeDataBoundary (self, point):
        pointGeo = ogr.Geometry(ogr.wkbPoint)
        pointGeo.AddPoint(point[0], point[1])
        for geo in self.safeDataBoundary:
            if pointGeo.Within(geo):
                return True
        return False

    #removes loops in the graph
    def removeLoops (self):
        #close all loops upstream of 'sinkNode'
        #do a breadth first search from a sink
        #all nodes must be upstream of SOME sink. So, running BFS from all sinks covers all nodes
        # logic: run BFS, if we ever encounter a node that we've already seen, this is a loop, so we disconnect the segment that 
        # connects the segment in question to the node we've already seen. Thus closing the loop

        def closeDownstreamJunctions ():
            for node in self.nodes:
                downstreamConnections = node.getDownstreamNeighbors()
                sortedDownstreamConnections = sorted(downstreamConnections, key=lambda seg: seg.streamLevel)
                for segment in sortedDownstreamConnections[1:]:
                    downstreamPoint = segment.downStreamNode.position
                    upstreamPoint = segment.upStreamNode.position
                    newEndPointNodePos = ((downstreamPoint[0] + upstreamPoint[0])/2, (downstreamPoint[1] + upstreamPoint[1])/2)
                    newEndPointNode = self.addNode(newEndPointNodePos)
                    
                    newEndPointNode.addNeighbor(segment, DOWNSTREAM) # our segment is downstream from the new node
                    
                    node.removeNeighbor(segment)
                    segment.upStreamNode = newEndPointNode

        def closeLoops (sinkNode):
            frontier = [sinkNode]
            discovered = [sinkNode]
            while len(frontier) > 0:
                nextNode = frontier.pop()                             
                #we get sorted upstream branches to promote determinism. We're doing a depth first search along the main path
                #secondary paths will come afterwards. Whenever a secondary path intersects a main path it will cut itself off
                sortedNeighbors = list(reversed(nextNode.getSortedUpstreamBranches()))

                newFrontier = []
                # sort in reverse since within this loop we may remove a segment. Since we are looping over segments that can cause trouble
                for neighbor in sortedNeighbors:
                    #this neighbor has an upstream relationship
                    upstreamNode = neighbor.upStreamNode
                    if upstreamNode not in discovered:
                        #insert at beginning. This makes this a depth first search following priority of stream level
                        #the traversal will follow the lowest stream level path until its conclusion 
                        #then follow the next higher streamlevel paths until the entire tree is searched
                        newFrontier.insert(0, upstreamNode)
                        discovered.append(upstreamNode)
                    else:
                        # this neighbor branch takes us to a node we've already seen
                        # so disconnect this edge from that node to remove loop
                        thisPosition = nextNode.position
                        connectionPosition = neighbor.upStreamNode.position
                        newEndPointNodePos = ((thisPosition[0] + connectionPosition[0])/2, (thisPosition[1] + connectionPosition[1])/2)
                        newEndPointNode = self.addNode(newEndPointNodePos)
                        newEndPointNode.addNeighbor(neighbor, DOWNSTREAM) # our segment is downstream from the new segment
                        neighbor.upStreamNode.removeNeighbor(neighbor)
                        neighbor.upStreamNode = newEndPointNode
                frontier.extend(newFrontier)

        """ sinks = self.getSinks()
        #remove loops
        for sink in sinks:
            closeLoops(sink) """
        closeDownstreamJunctions()


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
            name = downstreamSegment.streamName

            newSegment = self.addSegment(newSegmentUpstreamNode, newSegmentDownstreamNode, newID, newLength, newStreamLevel, newArbolateSum, name)    

            #add the sites to the new segment
            for site in upstreamSegment.sites:
                newSegment.addSite(site.siteID, site.distDownstreamAlongSegment) 
            #for the downstream segment, we must add the length of the upstream segment to get an accurate distance downstream segment number
            for site in downstreamSegment.sites:
                newSegment.addSite(site.siteID, site.distDownstreamAlongSegment + upstreamSegment.length) 

            #remove the segment and nodes from the actual graph
            for neighbor in reversed(node.neighbors):
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
    def addGeom(self, baseData):
        lineLayer = baseData.lineLayer
        objectIDIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("OBJECTID")
        lengthIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("LENGTHKM")
        nameIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("GNIS_NAME")

        fCodeIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("FCode")
        streamLevelIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("STREAMLEVE")
        arbolateSumIndex = baseData.lineLayer.GetLayerDefn().GetFieldIndex("ARBOLATESU")

        for line in lineLayer:
            #don't add duplicates
            segmentID = line.GetFieldAsString(objectIDIndex)
            length = float(line.GetFieldAsString(lengthIndex))
            fCode = int(line.GetFieldAsString(fCodeIndex))
            streamLevel = int(line.GetFieldAsString(streamLevelIndex))
            arbolateSum = float(line.GetFieldAsString(arbolateSumIndex))
            streamName = line.GetFieldAsString(nameIndex)
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

            self.addSegment(upstreamNode, downstreamNode, segmentID, length, streamLevel, arbolateSum, streamName)

        siteLayer = baseData.siteLayer
        siteNumberIndex = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
        siteNameIndex = siteLayer.GetLayerDefn().GetFieldIndex("station_nm")

        self.safeDataBoundary.append(baseData.dataBoundary)
        self.removeLoops()
        
        testCount = siteLayer.GetFeatureCount()
        #for each site, get a list of potential snaps and store them
        for site in siteLayer:
            siteID = site.GetFieldAsString(siteNumberIndex)
            siteName = site.GetFieldAsString(siteNameIndex)
            pt = site.GetGeometryRef().GetPoint(0)
            #don't try to add sites that aren't within the safe data boundary
            if not self.pointWithinSafeDataBoundary(pt):
                continue
            snapablePoint = SnapablePoint(point = pt, name = siteName, id = siteID)
            snaps = snapPoint(snapablePoint, baseData)
            #build a list of graphSites
            #graphSite is similar to Snap, but stores a reference to segmentID instead of feature
            #we assume that the feature reference itself isn't stable once the GDAL object gets
            #removed by the garbage collector
            if len(snaps) > 0:
                potentialGraphSites = [GraphSite(siteID = siteID, segmentID = snap.feature.GetFieldAsString(objectIDIndex), snapDist = snap.snapDistance, distDownstreamAlongSegment = snap.distAlongFeature, nameMatch = snap.nameMatch, generalWarnings = snap.warnings, assignmentWarnings = []) for snap in snaps]
                self.addSiteSnaps(siteID, potentialGraphSites)

        #refresh all site snaps given the new site data
        if self.debug:
            print("refreshing site snaps")
        assignmentInfo = getSiteSnapAssignment(self, debug = self.debug)
        assignments = assignmentInfo[0]
        warnings = assignmentInfo[1]
        self.refreshSiteSnaps(assignments)
        #since we reload assignments, we reload warnings stored
        self.currentAssignmentWarnings = warnings
        #self.cleanGraph()