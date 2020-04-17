from pathlib import Path


SITE_INFO_PATH = Path("siteInfo")
# this should be replaced mostly with a sql database at some point.. 
class SiteIDManager (object):

    def __init__(self):
         self.ids = {}# dict of part codes

    def getNeighborIDs (self, siteID):
        partCode = siteID[:2]

        if partCode not in self.ids:
            if self.loadPartCode(partCode) is False:
                #failed to load part code data
                print ("Failed to load data for " + partCode)
                return None
        
        matchIndex = self.ids[partCode].index(siteID)
        numIds = len(self.ids[partCode])
        if matchIndex < numIds-1:
            upperNeighbor = self.ids[partCode][matchIndex+1]
        if matchIndex > 0:
            lowerNeighbor = self.ids[partCode][matchIndex-1]
        #lower neighbor is lower in number, not in terms of downstream, vice versa
        return (lowerNeighbor, upperNeighbor)        

    def loadPartCode (self, code):
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
            return False
            print("could not load data for this partCode")
        