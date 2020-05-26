import math
#approximates the number of degrees latitude or longitude equivilant to km kilometers
def approxKmToDegrees (km):
        return (1/111) * km

def metersToMiles (meters):
    return float(meters) * 0.000621371

# generally used geo measurement function
# https://stackoverflow.com/questions/639695/how-to-convert-latitude-or-longitude-to-meters
def degDistance(lat1, lon1, lat2, lon2):
    R = 6378.137 # Radius of earth in KM
    dLat = lat2 * math.pi / 180 - lat1 * math.pi / 180
    dLon = lon2 * math.pi / 180 - lon1 * math.pi / 180
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    return d * 1000 # meters


#check if two points are relatively equal. 
def pointsEqual (p1, p2):
    threshold = approxKmToDegrees(1/1000)
    if abs(p1[0]-p2[0]) + abs(p1[1] - p2[1]) < threshold:
        return True
    else:
        return False

def dist (x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

#a faster distance to compare relative distances between things (i.e which of these two things is closer)
#same as regular distance but omits the sqrt function
def fastMagDist (x1, y1, x2, y2):
    return (x2 - x1)**2 + (y2 - y1)**2

#given an ID, gets the full 10 digit ID by appending zeros until 10 digits is reached
def getFullID (id):
    newID = str(id)

    missingDigits = 10-len(newID)

    return newID + "0" * missingDigits

#from point1 to point2
def getCardinalDirection (point1, point2):
    offset = (point2[0] - point1[0], point2[1] - point1[1])
    angle = (math.atan2(offset[1], offset[0]) % (math.pi*2))
    angle = angle / (math.pi*2)
    angle = angle * 360

    adjustedAngle = (angle + 22.5) % (360)

    directions = ["east", "northeast", "north", "northwest", "west", "southwest", "south", "southeast"]
    
    directionIndex = int((adjustedAngle / 360) * 7)

    return directions[directionIndex]

# if a is larger than b: returns > 0
# if a is equal to b: returns 0
# if a is less than b: returns < 0
def siteIDCompare (a, b):
    fullA = getFullID(a)
    fullB = getFullID(b)

    aDSN = int(fullA[2:])
    bDSN = int(fullB[2:])

    return aDSN - bDSN

#get's the difference betwen two site IDs
def getSiteIDOffset (a, b):
    fullA = getFullID(a)
    fullB = getFullID(b)

    aDSN = int(fullA[2:])
    bDSN = int(fullB[2:])

    return abs(aDSN - bDSN)

#get the full ID given the downstream number (DSN) and a partcode (first two digits)
#some cases the DSN starts with leading zeros. Like: 01035342 <- (partcode:01, DSN:035342)
#So this function adds leading zeros when necessary. This fuction assumes that there 
#the DSN with leading zeros will be a full 8 digits by itself and will prepend enough zeros to ensure that
def buildFullID (partCode, DSNwithExtension):
    #we expect the DNS with extension to be at least 8 digits
    #but, if the leading numbers of the DSN are 0s then this will be fewer digits when converted to an int
    intDSN = int(DSNwithExtension)
    missingLeadingZeros = 8 - len(str(intDSN))

    return str(partCode) + missingLeadingZeros*"0" + str(intDSN)

def dot (x1, y1, x2, y2):
    return x1*x2 + y1*y2

def normalize (x, y):
    mag = math.sqrt(x*x + y*y)

    return (x/mag, y/mag)

#utility for testing. Removes string formatting for CSV files
def flattenString (string):
    string = string.replace("\n", " ")
    string = string.replace("\t", " ")
    string = string.replace(",", " ")
    return string

#round num to m digits (ex: num = 30.23. m = 0.1, return:30.2)
def roundTo (num, m):
    return math.floor(float(num)/m + 0.5) * m

#gets the string rep of a float with numDigits digits after the decimal point
def getFloatTruncated (number, numDigits):
    numString = str(number)
    decimalIndex = numString.index(".")
    return numString[0:min(len(numString), decimalIndex + numDigits)]


#check if n is between a and b
def betweenBounds (n, a, b):
    upperBound = max(a, b)
    lowerBound = min(a, b)

    if n > lowerBound and n < upperBound:
        return True
    else:
        return False

#get's the shortened version of an ID
def shortenID (siteID):
    if len(siteID) > 8:
        trailingDigits = siteID[-2:]
        if trailingDigits == "00":
            return siteID[:8]
    return siteID


#this format allows the frontend to make hyperlinks out of site IDs
#relatively arbitrary, but needs to match the front end regex
def formatID (siteID):
    return "_" + str(siteID) + "_"