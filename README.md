# ADONNIS

<b> Back end info: </b>

<b> Prerequisites</b>
<ol>
data folder containing a NHDFlowline shapefile
data folder containing a NY_Site shapefile
X coordinate (latitude in decimal degrees)
Y coordinate (longitude in decimal degrees)


</ol>
Please note: X,Y must be snapped or within 1 meter to a flowline
Both the shapefiles must be pre-projected to NAD 1983 UTM 18N (projected coordinate system)


<b> Execution </b>

from GDALCode import determineNewSiteID

newID = determineNewSiteID(x,yfolderPath,sitefileName,linefileName)

<b> Details </b>
For more information, see the Documentation Folder

