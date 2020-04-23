

SITE_ORDER_ERROR = "INCORRECT SITE NUMBERS"
MISSING_STREAM_SEGMENT_ERROR = "MISSING NHD DATA"
FATAL_ERROR = "FATAL ERROR"



class WarningLog (object):

    def __init__(self, lat, lng):
        self.basicInfo = "SiteID requested at " + str(lat) + ", " + str(lng)
        self.warningInfo = dict()

    def resetWarnings (self, warningCode):
        self.warningInfo[warningCode] = []

    def addWarning (self, warningCode, warningBody):
        if warningCode in self.warningInfo:
            self.warningInfo[warningCode].append(warningBody)
        else:
            self.warningInfo[warningCode] = [warningBody]
    
    def getFormattedMessage (self):
        output = self.basicInfo + "\n\n"
        for warningType in self.warningInfo:
            messages = self.warningInfo[warningType]
            if len(messages) > 0:
                output += str(warningType) + "\n"
                for warningMessage in self.warningInfo[warningType]:
                    output += "\t " + warningMessage + "\n"
                output += "\n"
            
        return output