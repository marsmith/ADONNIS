import math
#approximates the number of degrees latitude or longitude equivilant to km kilometers
def approxKmToDegrees (km):
        return (1/111) * km

#check if two points are relatively equal. 
def pointsEqual (p1, p2):
    threshold = 1
    if abs(p1[0]-p2[0]) + abs(p1[1] - p2[1]) < threshold:
        return True
    else:
        return False

def dist (x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)