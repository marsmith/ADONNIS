

SITE_ORDER_ERROR = "[medium priority] INCORRECT SITE NUMBERS"
MISSING_STREAM_SEGMENT_ERROR = "[medium priority] MISSING NHD DATA"
FATAL_ERROR = "FATAL ERROR"
DISTANT_SNAP_WARNING = "[low priority] DISTANT SNAPS"
SITE_CONFLICT_INVOLVEMENT = "[high priority] INCORRECT SITE NUMBERS INVOLVED IN RESULTS"

GENERIC_FLAG = "[low priority] WARNINGS"

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