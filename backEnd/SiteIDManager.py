import Helpers
import GDALData
import Failures


#SITE_INFO_PATH = Path("siteInfo")
# this should be replaced mostly with a sql database at some point.. 
class SiteIDManager (object):

    def __init__(self):
         self.ids = {}# dict of huc codes

    def getNeighborIDs (self, siteID, huc):
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

    """ def loadPartCode (self, code):
        sitesPath = Path(__file__).parent.absolute() / SITE_INFO_PATH / (str(code) + ".txt")
        try:
            sitesString = sitesPath.read_text()
            siteList = sitesString.split("\n")
            siteIDs = []
            for site in siteList:
                siteSplit = site.split("\t")
                siteID = siteSplit[0]
                siteIDs.append(siteID)
            self.ids[code] = siteIDs
            return True
        except:
            return False """
    
    def loadHucWeb (self, code):
        if code in self.ids:
            return True
        ids = GDALData.loadHUCSites(code)
        if Failures.isFailureCode(ids):
            return ids

        self.ids[code] = sorted(ids, key=lambda id: Helpers.getFullID(id))

        return True
        