import Helpers
import GDALData
import Failures

class SiteIDManager (object):

    def __init__(self):
         self.ids = {}# dict of huc codes

    def getNeighborIDs (self, siteID, huc):
        """ Get the two nearest sequential neighbors to a siteID.

        Upstream neighbor meaning the site with the next lower DSN number than the input ID. 
        
        :param siteID: The siteID.
        :param huc: The 2 digit huc code that the site is within.
        
        :return: (upstream neighbor, downstream neighbor) """
        hucCode = huc[:2]

        loadResults = self.loadHucWeb(hucCode)
        if Failures.isFailureCode(loadResults):
            return loadResults
        
        matchIndex = self.ids[hucCode].index(siteID)

        if matchIndex == -1:
            return Failures.MISSING_SITEID_CODE

        numIds = len(self.ids[hucCode])
        if matchIndex < numIds-1:
            downstreamNeighbor = self.ids[hucCode][matchIndex+1]
            if downstreamNeighbor[:2] != siteID[:2]:
                #if this neighbor is a different part code it's not valid
                downstreamNeighbor = None
        if matchIndex > 0:
            upstreamNeighbor = self.ids[hucCode][matchIndex-1]
            if upstreamNeighbor[:2] != siteID[:2]:
                upstreamNeighbor = None
        #lower neighbor is lower in number, not in terms of downstream, vice versa
        return (upstreamNeighbor, downstreamNeighbor)   


    def getXNeighborIDs (self, siteID, huc, numNeighbors):
        """ Get numNeighbors neighboring IDs above and below siteID
    
        :param siteID: The siteID.
        :param huc: The 2 digit huc code that the site is within.
        :param numNeighbors: The number of neighbors to get above and below siteID.

        :return: A list of all site IDs within the range. """

        hucCode = huc[:2]

        loadResults = self.loadHucWeb(hucCode)
        if Failures.isFailureCode(loadResults):
            return loadResults

        numIds = len(self.ids[hucCode])

        matchIndex = numIds-1
        for i, thisID in enumerate(self.ids[hucCode]):
            if thisID[:2] == siteID[:2]:
                if thisID == siteID or Helpers.siteIDCompare(thisID, siteID) > 0:
                    testcmp = Helpers.siteIDCompare(thisID, siteID)
                    matchIndex = i
                    break

        minIndex = max(0, matchIndex - numNeighbors)
        upperIndex = min(numIds-1, matchIndex + numNeighbors)

        return self.ids[hucCode][minIndex:upperIndex]  
    
    def loadHucWeb (self, code):
        """ Load all sites from a given huc code into the manager object.
        
        :param code: The HUC code being loaded. """
        if code in self.ids:
            return True
        ids = GDALData.loadHUCSites(code)
        if Failures.isFailureCode(ids):
            return ids

        self.ids[code] = sorted(ids, key=lambda id: Helpers.getFullID(id))

        return True
        