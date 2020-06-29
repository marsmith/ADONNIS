import math

def nearestPointOnSegment(vx, vy, wx, wy, px, py):
    """ Gets the nearest point on a segment (v, w) to a given point (p).
    
    :param vx: X of p1.
    :param vy: Y of p1.
    :param wx: X of p2.
    :param wy: Y of p2.
    
    
    :return: ((x,y), t), where t is the relative position on the segment (0-1) """
    l2 = fastMagDist(vx, vy, wx, wy)
    if (l2 == 0):
        return fastMagDist(vx, vy, px, py)

    t = ((px - vx) * (wx - vx) + (py - vy) * (wy - vy)) / l2;
    t = max(0, min(1, t))
    return (vx + t * (wx - vx), vy + t * (wy - vy)), t

def formatList (list):
    """ Return a pretty formatted string for a list. Adds Oxford comma and commas when needed.
    
    :param list: A list of anything. """
    if len(list) == 1:
        return list[0]
    formatedString = ""
    oxfordComma = len(list) > 2
    for i in range(0, len(list)-1):
        formatedString += str(list[i])
        if i < len(list)-2:
            formatedString += ", "
    if oxfordComma:
        formatedString += ","
    formatedString += " and " + str(list[-1])
    return formatedString

def approxKmToDegrees (km):
    """ Approximates the number of degrees latitude or longitude equivilant to some number of kilometers.
    
    :param km: kilometers.
    
    :return: The approximate number of decimal degrees lat or lng equivilant to the surface distance of km. """
    return (1/111) * km

def metersToMiles (meters):
    """ Simple conversion. """
    return float(meters) * 0.000621371

def degDistance(lat1, lon1, lat2, lon2):
    """ Surface distance between two lat/lng pairs.
    
        Credit to: https://stackoverflow.com/questions/639695/how-to-convert-latitude-or-longitude-to-meters """
    R = 6378.137 # Radius of earth in KM
    dLat = lat2 * math.pi / 180 - lat1 * math.pi / 180
    dLon = lon2 * math.pi / 180 - lon1 * math.pi / 180
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    return d * 1000 # meters
 
def pointsEqual (p1, p2):
    """ heck if two points are relatively equal. 
    :param p1: A tuple x,y.
    :param p2: A tuple x,y.
    
    :return: bool"""
    threshold = approxKmToDegrees(1/1000)
    if abs(p1[0]-p2[0]) + abs(p1[1] - p2[1]) < threshold:
        return True
    else:
        return False

def dist (x1, y1, x2, y2):
    """ Simple dist function. """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def fastMagDist (x1, y1, x2, y2):
    """ Equivilant to dist^2. This can be used to compare the relative closeness of things while avoid the slow sqrt function. """
    return (x2 - x1)**2 + (y2 - y1)**2

def getFullID (id):
    """ given an ID, gets the full 10 digit ID by appending zeros until 10 digits is reached
    
    :return: string representation of siteID """
    newID = str(id)

    missingDigits = 10-len(newID)

    return newID + "0" * missingDigits

#from point1 to point2
def getCardinalDirection (point1, point2):
    """ Gets cardinal direction between two points.
    
    :param point1: A tuple x,y 
    :param point2: A tuple x,y 
    :return: A string like 'east', 'north', etc."""

    offset = (point2[0] - point1[0], point2[1] - point1[1])
    angle = (math.atan2(offset[1], offset[0]) % (math.pi*2))
    angle = angle / (math.pi*2)
    angle = angle * 360

    adjustedAngle = (angle + 22.5) % (360)

    directions = ["east", "northeast", "north", "northwest", "west", "southwest", "south", "southeast"]
    
    directionIndex = int((adjustedAngle / 360) * 7)

    return directions[directionIndex]


def siteIDCompare (a, b):
    """ if a is larger than b: returns > 0

        if a is equal to b: returns 0
        
        if a is less than b: returns < 0 """
    fullA = getFullID(a)
    fullB = getFullID(b)

    aDSN = int(fullA[2:])
    bDSN = int(fullB[2:])

    return aDSN - bDSN


def getSiteIDOffset (a, b):
    """ Gets the difference in DSN (downstream number) of two site IDs 
    
    :return: int"""
    fullA = getFullID(a)
    fullB = getFullID(b)

    aDSN = int(fullA[2:])
    bDSN = int(fullB[2:])

    return abs(aDSN - bDSN)

def buildFullID (partCode, DSNwithExtension):

    """ Get the full ID given the downstream number (DSN) and a partcode (first two digits).
    
    :param DSNwithExtension: The full 8 digit DSN string.
    :param partCode: The 2 digit part code.  
    """

    #we expect the DNS with extension to be at least 8 digits
    #but, if the leading numbers of the DSN are 0s then this will be fewer digits when converted to an int
    intDSN = int(DSNwithExtension)
    missingLeadingZeros = 8 - len(str(intDSN))

    return str(partCode) + missingLeadingZeros*"0" + str(intDSN)

def dot (x1, y1, x2, y2):
    """ Dot product of two vectors. """
    return x1*x2 + y1*y2

def normalize (x, y):
    """ Normalize the vector. """
    mag = math.sqrt(x*x + y*y)

    return (x/mag, y/mag)

def flattenString (string):
    """ Remove new line, tab and commas for easy addition to a CSV file. """
    string = string.replace("\n", " ")
    string = string.replace("\t", " ")
    string = string.replace(",", " ")
    return string


def roundTo (num, m):
    """ Round num to m digits (ex: num = 30.23. m = 0.1, return:30.2) """
    return math.floor(float(num)/m + 0.5) * m

#gets the string rep of a float with numDigits digits after the decimal point
def getFloatTruncated (number, numDigits):
    numString = str(number)
    decimalIndex = numString.index(".")
    return numString[0:min(len(numString), decimalIndex + numDigits)]

def betweenBounds (n, a, b):
    """ Check if n is between a and b """
    upperBound = max(a, b)
    lowerBound = min(a, b)

    if n > lowerBound and n < upperBound:
        return True
    else:
        return False

#get's the shortened version of an ID
def shortenID (siteID):
    """ Remove the trailing two zeros of a 10 digit ID if they exist. """
    if len(siteID) > 8:
        trailingDigits = siteID[-2:]
        if trailingDigits == "00":
            return siteID[:8]
    return siteID



def formatID (siteID):
    """ This format allows the frontend to make hyperlinks out of site IDs.

    Relatively arbitrary, but needs to match the front end regex """
    return "_" + str(siteID) + "_"