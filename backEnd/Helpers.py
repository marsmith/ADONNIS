import math
#approximates the number of degrees latitude or longitude equivilant to km kilometers
def approxKmToDegrees (km):
        return (1/111) * km

#check if two points are relatively equal. 
def pointsEqual (p1, p2):
    threshold = approxKmToDegrees(1/1000)
    if abs(p1[0]-p2[0]) + abs(p1[1] - p2[1]) < threshold:
        return True
    else:
        return False

def dist (x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def fastMagDist (x1, y1, x2, y2):
    return (x2 - x1)**2 + (y2 - y1)**2

def getFullID (id):
    newID = id + ""
    if len(id) < 10:
        newID += "00"
    return newID

# if a is larger than b: returns > 0
# if a is equal to b: returns 0
# if a is less than b: returns < 0
def siteIDCompare (a, b):
    fullA = getFullID(a)
    fullB = getFullID(b)

    aDSN = int(fullA[2:])
    bDSN = int(fullB[2:])

    return aDSN - bDSN


def dot (x1, y1, x2, y2):
    return x1*x2 + y1*y2

def normalize (x, y):
    mag = math.sqrt(x*x + y*y)

    return (x/mag, y/mag)

def flattenString (string):
    string = string.replace("\n", " ")
    string = string.replace("\t", " ")
    string = string.replace(",", " ")
    return string


def roundTo (num, m):
    return math.floor(float(num)/m + 0.5) * m

def betweenBounds (n, a, b):
    upperBound = max(a, b)
    lowerBound = min(a, b)

    if n > lowerBound and n < upperBound:
        return True
    else:
        return False

def shortenID (siteID):
    if len(siteID) > 8:
        trailingDigits = siteID[-2:]
        if trailingDigits == "00":
            return siteID[:8]
    return siteID