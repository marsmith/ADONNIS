import collections

SITE_ORDER_ERROR = "[medium priority] INCORRECT SITE NUMBERS"
MISSING_STREAM_SEGMENT_ERROR = "[medium priority] MISSING NHD DATA"
FATAL_ERROR = "FATAL ERROR"
DISTANT_SNAP_WARNING = "[low priority] DISTANT SNAPS"
SITE_CONFLICT_INVOLVEMENT = "[high priority] INCORRECT SITE NUMBERS INVOLVED IN RESULTS"

GENERIC_FLAG = "[low priority] WARNINGS"

LOW_PRIORITY = "low priority"
MED_PRIORITY = "medium priority"
HIGH_PRIORITY = "high priority"

Warning = collections.namedtuple('Warning', 'priority message')

class WarningLog (object):

    def __init__(self, lat, lng):
        self.basicInfo = "SiteID requested at " + str(lat) + ", " + str(lng)
        self.warningInfo = {LOW_PRIORITY:[], MED_PRIORITY:[], HIGH_PRIORITY:[]}

    def resetWarnings (self, warningCode):
        self.warningInfo[warningCode] = []

    def addWarningTuple (self, warning):
        priority = warning.priority
        message = warning.message
        self.addWarning(priority, message)

    def addWarning (self, priority, warningBody):
        priorityClass = self.warningInfo[priority]
        priorityClass.append(warningBody)
        """ if warningCode in priorityDict:
            priorityDict[warningCode].append(warningBody)
        else:
            priorityDict[warningCode] = [warningBody] """
    
    def getFormattedMessage (self):
        output = self.basicInfo + "\n\n"
        for priority in self.warningInfo:
            numMessages = len(self.warningInfo[priority])
            if numMessages > 0:
                output += priority + "\n"
                for message in self.warningInfo[priority]:
                    output += "\t " + message + "\n"
            
        return output

    def getJSON (self):
        return self.warningInfo