# ADONNIS
<img src="/images/logoRob.png" width="200"/>

## Purpose
The motivation for the ADONNIS Project was to improve the process of creating new identification number and names for new water guages. A site identification number is a 8 to 10 digit long number which is given to each groundwater site for purposes of tracking it. Historically, numbers were assigned by hand. Based on the given watershed area the site is on and its neighbors, a new site id was assigned to leave enough room for future sites; similar to giving street addresses while trying leaving enough room for more houses on the street, even though this street branches off into multiple different directionsPrior to the creation of this software, creating new IDs and names was a timely process that was done visually and had the potential for error. ADONNIS advances the site naming and numbering process by using weighted networks and a proportional site naming and ID numbering algorithm which increasing the accuracy and efficiency. 

## Back end info

  ### Prerequisites

  - data folder containing a NHDFlowline shapefile
  - data folder containing a NY_Site shapefile
  - X coordinate (latitude in decimal degrees)
  - Y coordinate (longitude in decimal degrees)


  Please note: X,Y must be snapped or within 1 meter to a flowline
  Both the shapefiles must be pre-projected to NAD 1983 UTM 18N (projected coordinate system)


## How the Algorithm Works
  0. Import all data pertinent to MAX_BUFFER_SIZE allowed using GDAL (how big will our search area possibly get)
  1. Draw a circle geometry around the x,y provided using GDAL
  2. Isolate a network based on the lines in the circle and the line clicked with x,y (even though there may be many lines in
  the circle, only those connected to the targetare selected)
	  * If the circle previous was too small, we will expand the circle until either reaching the recommended size
	  * or until we exceed max size.
  3. If there are no existing sites on the network selected, goto step 9. If there is one, go to step 4,
  if there are more than one, go to step 7
  
  ### Single Real Site
  4. Perform the iSNA algorithm to identify "fake-site" SiteID objects for all nodes from the click line to
	the sink (or outlet,outflow,etc). Return an ordered list of these "fake-sites" we encountered
  5. Perform a pSNA algorithm on each iSNA "fake-site" encountered. After this the tree is populated
	6. Interpolate the SiteID based on start line in network (and return the new SiteID we want, hopefully)
  
  ### Multiple Real Sites
  7. Do a "testFlight" runthrough of the network, starting from the base (or outlet,outflow,etc.). Keep track
  of when we encounter each object in the network (Site,Flow). If we encounter a real site, mark its index in the list
  If we encounter the start line (clicked by x,y), mark that index as well
  8. Determine the scenario of real sites around the clicked line.
  	
	SCENARIO A: <>---***---<> Real Sites surrounding the start line (any distance away)
	Perform a special version of pSNA where we only populate the network's "fake-sites" from the downstream site relative
	to the start line and the upstream site realtive to the start line.
	After this, go to step 6.
	
	SCENARIO B: <>---***--- Real Sites only before the start line
	Run pSNA as usual but start one node up and do the calculation for the initial flowline manually
	After this, got to step 6
	
	SCENARIO C: -----***---<> Real Sites only after the start line
	Go to step 5
  
  ### No Real Sites
  9. Run the isolateNetwork algorithm again (steps 1-3), with an expanded search radius (increasing the clump factor)
  If there are still no sites in range to base off of, then go to 10
  10. Calculate a new first four digit number series, either in a gap that exists in the NY_Sitefile or create one after the
  highest four digit number series. Then, concatenate this with 5000 to get the new number (mathematically, multiply the first
  four digits by 10,000 then add 5,000
  
