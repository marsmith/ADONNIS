import unittest
from StreamGraph import StreamGraph
from StreamGraphNavigator import StreamGraphNavigator
from GDALData import DataBoundary

class GraphNavigatorTests (unittest.TestCase):

    def test_siteDownstreamOnSegment (self):
        streamGraph = StreamGraph()
        node1 = streamGraph.addNode((0,0))
        node2 = streamGraph.addNode((0,-1))
        segment = streamGraph.addSegment (node1, node2, "1", 1, 1, 1)
        streamGraph.addSite ("site1", "1", 0.1)
        streamGraph.addSite ("site2", "1", 0.9)
        streamGraph.addSite ("site3", "1", 1)

        navigator = StreamGraphNavigator(streamGraph)
        
        downstreamSite = navigator.getNextDownstreamSite(segment, 0.5)
        foundSiteID = downstreamSite[0]
        foundSiteDist = downstreamSite[1]

        self.assertEqual(foundSiteID, "site2")
        self.assertEqual(foundSiteDist, 0.4)

    #test if a site downstream on the same segment is properly identified
    #in this test, there is a site farther down and a site above the query point on the same segment
    def test_findUpstreamSiteWithBacktrack (self):
        streamGraph = StreamGraph()
        node1 = streamGraph.addNode((0,0))
        node2 = streamGraph.addNode((0,-1))
        node3 = streamGraph.addNode((1,0))

        segment1 = streamGraph.addSegment (node1, node2, "1", 1, 2, 1)#trib of segment2 path
        segment2 = streamGraph.addSegment (node3, node2, "2", 1, 1, 1)
        streamGraph.addSite ("site1", "2", 0.2)
        dataBoundary = DataBoundary(point = (0,0), radius=10)

        streamGraph.safeDataBoundary.append(dataBoundary)

        navigator = StreamGraphNavigator(streamGraph)
        
        downstreamSite = navigator.getNextUpstreamSite(segment1, 0.5)
        foundSiteID = downstreamSite[0]
        foundSiteDist = downstreamSite[1]

        self.assertEqual(foundSiteID, "site1")
        self.assertEqual(foundSiteDist, 1.3)

    def test_siteUpstreamOnSegment (self):
        streamGraph = StreamGraph()
        node1 = streamGraph.addNode((0,0))
        node2 = streamGraph.addNode((0,-1))
        segment = streamGraph.addSegment (node1, node2, "1", 1, 1, 1)
        streamGraph.addSite ("site1", "1", 0.1)
        streamGraph.addSite ("site2", "1", 0.9)
        streamGraph.addSite ("site3", "1", 1)

        navigator = StreamGraphNavigator(streamGraph)
        
        downstreamSite = navigator.getNextUpstreamSite(segment, 0.5)
        foundSiteID = downstreamSite[0]
        foundSiteDist = downstreamSite[1]

        self.assertEqual(foundSiteID, "site1")
        self.assertEqual(foundSiteDist, 0.4)






    
    #find upstream site on same segment
    #find upstream site requiring graph expand
    #find upstream site requiring backtrack

    #find downstream site on same segment
    #find downstream site requiring backtrack
    #find downstream site on trib