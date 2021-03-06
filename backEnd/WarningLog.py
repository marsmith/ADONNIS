import collections

SITE_ORDER_ERROR = "[medium priority] INCORRECT SITE NUMBERS"
MISSING_STREAM_SEGMENT_ERROR = "[medium priority] MISSING NHD DATA"
FATAL_ERROR = "FATAL ERROR"
DISTANT_SNAP_WARNING = "[low priority] DISTANT SNAPS"
SITE_CONFLICT_INVOLVEMENT = "[high priority] INCORRECT SITE NUMBERS INVOLVED IN RESULTS"

GENERIC_FLAG = "[low priority] WARNINGS"

LOW_PRIORITY = "lowPriority"
MED_PRIORITY = "mediumPriority"
HIGH_PRIORITY = "highPriority"

Warning = collections.namedtuple('Warning', 'priority message responsibleSite implicatedSites')

class WarningLog (object):

    def __init__(self, lat, lng):
        self.basicInfo = "SiteID requested at " + str(lat) + ", " + str(lng)
        self.warningInfo = {LOW_PRIORITY:[], MED_PRIORITY:[], HIGH_PRIORITY:[]}

    def resetWarnings (self, warningCode):
        """ For a particular warningCode, reset all warnings associated with it. """
        self.warningInfo[warningCode] = []

    def addWarningTuple (self, warning):
        """ Add a warning in the form of a Warning tuple. """
        priority = warning.priority
        message = warning.message
        responsibleSite = warning.responsibleSite
        implicatedSites = warning.implicatedSites
        self.addWarning(priority, message, responsibleSite, implicatedSites)

    def addWarning (self, priority, warningBody, responsibleSite = None, implicatedSites = None):
        """ Add a warning without a warning tuple. """
        priorityClass = self.warningInfo[priority]
        warning = {"body":warningBody, "responsibleSite":responsibleSite, "implicatedSites":implicatedSites}
        priorityClass.append(warning)
        """ if warningCode in priorityDict:
            priorityDict[warningCode].append(warningBody)
        else:
            priorityDict[warningCode] = [warningBody] """
    
    def getFormattedMessage (self):
        """ Get a formatted string representing the warning log. Used for debug printing. """
        output = self.basicInfo + "\n\n"
        for priority in self.warningInfo:
            numMessages = len(self.warningInfo[priority])
            if numMessages > 0:
                output += priority + "\n"
                for message in self.warningInfo[priority]:
                    output += "\t " + message + "\n"
            
        return output

    def getJSONStruct (self):
        """ Get a copy of the json representation of the warning log. """
        return self.warningInfo.copy()