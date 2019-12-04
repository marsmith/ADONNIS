# Site-Maker-Back-End

<b> Introduction </b>

This Repository contains code which is the back end for the Site-Maker project, called Addonis

<b> Prerequisites</b>
<ol>
Folder containing a NHDFlowline shapefile
Folder containing a NY_Site shapefile
Folder containing these two folders inside of it
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

