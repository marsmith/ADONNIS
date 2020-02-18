#!/usr/bin/python3.6


from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdal_array
from osgeo import gdalconst
import os
import sys
import csv
import time
import threading
import multiprocessing
from Timesaver import *
from GDALData import *
from Precompiler import *
from net_tracer import net_tracer

# Program Constants

UC_BUFFER_MIN = 5000 # 5 km (What is the minimum size circle to draw)
UC_BUFFER_MAX = 30000 # 30 km (What is the maximum size circle to draw)
NY_STATE_AREA = 141299400000 # m^2 (Aprox. Area of the state)
MAX_CLUMP_FACTOR = 10 # Maximum clump factor allowed 
INITIAL_UCLICK_SWEEP = 5 # 1m (How many meters away from the line can our USER_CLICK be)
USER_CLICK_X = -1.0
USER_CLICK_Y = -1.0

#os.environ['GDAL_DATA'] = 'C:/Users/marsmith/miniconda/envs/adonnis/Library/share/gdal'
#os.environ['PROJ_LIB'] = 'C:/Users/marsmith/miniconda/envs/adonnis/Library/share/proj'

def determineOptimalSearchRadius(stateArea = NY_STATE_AREA,numberOfSites=None,clumpFactor=1):
    '''
    Gives an optimal radius for searching based on average sites per square meter in the state
    clumpFactor [Number]: How clumpy are sites. 1 +; 1 being sites are evenly distributed, while higher numbers mean sites are less
                            evenly distributed
    '''
    rat = numberOfSites / stateArea
    r = numpy.sqrt((1 / rat) / numpy.pi) * clumpFactor
    return r

def getFirstFourDigitFraming(gdalData):
    '''
    Finds the first four digit series of ID's that are avaliable and have no entries
    folderPath [String]: Folder path of shapefile data (not including shapefile folder)
    siteLayerName [String]: Name of Shapefile Folder/Shapefile
    '''
    siteLayer = gdalData.siteLayer
    siteNumber_index = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
    ffDict = {} # Stores the first four 
    for site in siteLayer:
        ff = site.GetFieldAsString(siteNumber_index)[0:4]
        if ff in ffDict.keys():
            continue 
        else:
            ffDict[ff] = "4dseries"
    return list(ffDict.keys())
def getFirstFourDigitFraming_Existing(gdalData, interSites):
    siteLayer = gdalData.siteLayer
    ffDict = {}
    for sentry in interSites:
        siteGe = sentry[0]
        siteNumber_index = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
        ff = siteGe.GetFieldAsString(siteNumber_index)[0:4]
        if ff in ffDict.keys():
            continue
        else:
            ffDict[ff] = "4dseries"
    return list(ffDict.keys())
def isolateNetwork(gdalData,x,y,minDist = UC_BUFFER_MIN,maxDist= None,clFactor=2):
    '''
    Will attempt to isolate a Network from the geospatial data provided
    Raises Exception if there is a failure in parsing or invalid data
    ** This is meant to be in a series of methods **

    gdalData [GDALData]: gdal data instance to use
    x [Number]: Longitude in decimal degree (float) notation
    y [Number]: Latitude in decimal degree (float) notation
    minDist [Number]: Minimum search buffer size (Default UC_BUFFER_MIN)
    maxDist [Number]: Maximum search buffer size (Default UC_BUFFER_MAX)
    clFactor [Number]: Clump Factor for optimal radius calculation (Default 2)

    Returns [[Network,Point Geometry,Vector Layer Entry (Line),
    Flow,Vector Layer(Sites),List(Of Vector Layer Entry(Site)),Number]]
    0 - Network Isolated
    1 - Projected Input Point
    2 - Starting Line (User Clicked Line)
    3 - Starting Flow (User Clicked Flow)
    4 - Site Layer
    5 - List of Site Entries in Site Layer inside the bubble
    6 - Number of Entries in the Site Layer
    '''
    # Create vars for return information
    global USER_CLICK_X
    global USER_CLICK_Y
    starterFlow = None
     
    # Buffer around userClick
    
    oRef = osr.SpatialReference()
    oRef.ImportFromEPSG(4326)

    # Reproject
    targRef = osr.SpatialReference()
    targRef.ImportFromEPSG(26918) # NY State Projection; consider a check from the provided site dataset instead
    
    # Create point from x,y and targRef
    ctran = osr.CoordinateTransformation(oRef,targRef)
    [p_lng,p_lat,z] = ctran.TransformPoint(x,y)
    USER_CLICK_X = p_lng
    USER_CLICK_Y = p_lat
    inputPointProj = ogr.Geometry(ogr.wkbPoint)
    inputPointProj.SetPoint_2D(0,p_lng,p_lat)
    r_ctran = osr.CoordinateTransformation(targRef,oRef)
    # Load Sites
    siteLayer = gdalData.siteLayer
    ctran = osr.CoordinateTransformation(siteLayer.GetSpatialRef(),targRef)

    dist = minDist
    interSites = []
    numSites = len(siteLayer)

    if maxDist is None:
        # If max distance is not provided, then we can use the 
        # optimal solution
        maxDist = determineOptimalSearchRadius(numberOfSites=numSites,clumpFactor=clFactor)

    shpdriver = ogr.GetDriverByName('ESRI Shapefile')
    linesLayer = gdalData.lineLayer
    gg = inputPointProj.Buffer(UC_BUFFER_MAX)
    linesLayer.SetSpatialFilter(gg)
    i = 0
    # Get certain info about line attributes
    lineName_index = linesLayer.GetLayerDefn().GetFieldIndex("GNIS_NAME")
    lineRC_index = linesLayer.GetLayerDefn().GetFieldIndex("ReachCode")
    lineLength_index = linesLayer.GetLayerDefn().GetFieldIndex("LengthKM")
    lineID_index = linesLayer.GetLayerDefn().GetFieldIndex("GNIS_ID")
    lineFCode_index = linesLayer.GetLayerDefn().GetFieldIndex("FCode")
    
    '''
    # Split lines automatically on existing sites if not done so already? (BROKEN)
    while i < len(linesLayer):
        l_geom = linesLayer[i].GetGeometryRef()
        for s in sl:
            sbuff = s.GetGeometryRef().Buffer(2)
            ldiff = None
            if l_geom.Intersects(sbuff):
                ldiff = l_geom.Difference(sbuff)
            if ldiff is None or ldiff.GetGeometryCount() == 0:
                # We dont need to remove and add two
                pass
            elif ldiff.GetGeometryCount() == 2:
                # Need to remove and add 2
                lentry1 = ogr.Feature(linesLayer.GetLayerDefn())
                lentry2 = ogr.Feature(linesLayer.GetLayerDefn())

                name = linesLayer[i].GetFieldAsString(lineName_index)
                lentry1.SetField("GNIS_NAME",name); lentry2.SetField("GNIS_NAME",name)
                rc = linesLayer[i].GetFieldAsString(lineRC_index)
                lentry1.SetField("ReachCode",rc); lentry2.SetField("ReachCode",rc)
                gnisID = linesLayer[i].GetFieldAsString(lineID_index)
                lentry1.SetField("GNIS_ID",gnisID); lentry2.SetField("GNIS_ID",gnisID)
                fcodeee = linesLayer[i].GetFieldAsString(lineFCode_index)
                lentry1.SetField("FCode",fcodeee); lentry2.SetField("FCode",fcodeee)

                # Determine what fraction of LengthKM goes to each feature
                totalLen = float(linesLayer[i].GetFieldAsString(lineLength_index))
                g1 = ldiff.GetGeometryRef(0)
                g2 = ldiff.GetGeometryRef(1)
                fracLentry1 = g1.Length() / l_geom.Length()
                fracLentry2 = 1.0 - fracLentry1

                lentry1.SetGeometry(g1)
                lentry2.SetGeometry(g2)
                lentry1.SetField("LengthKM",totalLen * fracLentry1); lentry2.SetField("LengthKM",totalLen * fracLentry2)
                # Remove the old line entry and add in the two new ones in its index
                linesLayer.DeleteFeature(linesLayer[i].GetFID())
                linesLayer.CreateFeature(lentry1)
                linesLayer.CreateFeature(lentry2)
                print("Just split line on existing site!")
                i -= 1
                break
            else:
                print("Weird SplitLineOnPOint result!")
                
        i += 1 # Increment line counter
    '''
    #increase the distance until we either max out on distance OR
    #until we find (in this case), 2 preexisting sites 
    while len(interSites) < clFactor and dist < maxDist:
        geomBuffer = inputPointProj.Buffer(dist) # Buffer around the geometry  
            
        # Intersect of BUFFER and SITES        
        for site in siteLayer:
            # Grab information on the first four digits of the site          

            ingeom_site = site.GetGeometryRef()
            if ingeom_site.Within(geomBuffer):
                # This site is inside the buffer!
                interSites.append((site,ingeom_site.Buffer(1)))

        siteLayer.ResetReading()
        if len(interSites) < clFactor:
            dist += 1000 # Expand by 2km           

    linesLayer.SetSpatialFilter(geomBuffer)    
    # Get certain info about site attributes
    siteNumber_index = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
    stationName_index = siteLayer.GetLayerDefn().GetFieldIndex("station_nm")    
    siteCounter = 0
    interLines = []
    # Intersect of BUFFER and LINES
    for line in linesLayer:        
        interLines.append(line)   
    # Buffer all Lines
    lBufferStore = {} # Stores line entry, Bool flag)    
    sitesStore = {}# Stores Site object (fake site)
    flowList = [] # Stores Flowline object (flow)
    lL = []    
    # Create Buffer polygon where user clicked    
    # Find line which ucBuff intersects
    ucBuff = inputPointProj.Buffer(1)
    i = 0
    startingIndex = None
    startingLine = None
    for line in interLines:       
        e = (line.GetGeometryRef().Buffer(INITIAL_UCLICK_SWEEP),False)
        lBufferStore[line] = e[1] # Original Line, Buffered Geometry 
        if ucBuff.Intersects(e[0]):
            startingLine = line            
        i += 1
        
    if startingLine is None:        
        raise RuntimeError("isolateNetwork() [Error]: User Click was not snapped to line!")
    
    queue = [] # Stores keys
    queue.append(startingLine)    
    counter = 0
    while len(queue) > 0:
        # Visualize the lines in stages       
        e = queue.pop(0) # This will be the line
        lL.append(e)        
        if lBufferStore[e] == True:
            # We have already visited this
            continue
        else:
            # Check to make sure e does not have a restricted FCode
            # Restricted FCodes are 42807
            fCode = int(e.GetFieldAsString(lineFCode_index))
            if fCode == 42807 or fCode == 33600:
                continue # Skip this line, ignore it completely
            
            _npt = e.GetGeometryRef().GetPointCount()#number of points
            upPt = ogr.Geometry(ogr.wkbPoint)#up stream point - wkb point is the code for point based geometry
            p_ = e.GetGeometryRef().GetPoint(0)
            upPt.AddPoint(p_[0],p_[1])
            
            upBuff = upPt.Buffer(1)
            downPt = ogr.Geometry(ogr.wkbPoint)
            p_ = e.GetGeometryRef().GetPoint(_npt - 1)
            downPt.AddPoint(p_[0],p_[1])
            downBuff = downPt.Buffer(1)
            # See if any of the sites are also that endpoint
            b_f = [False,False]
            upSite = None
            downSite = None
            
            # Check if any real sites exist at the endpoint
            for s in interSites: #for all sites (up to 2) in the search area ...
                s_geom = s[1]
                
                if s_geom.Intersects(upPt):
                    # Found existing upper extent
                    b_f[0] = True
                    foundExistingSiteGeom = False
                    for k,v in sitesStore.items():
                        if k.Intersects(s_geom):
                            # Use the existing entry as site
                            foundExistingSiteGeom = True
                            upSite = sitesStore[k]                            
                            
                    if not foundExistingSiteGeom:
                        # Need to create our own an add it to the table
                        # print(upPt.GetX())
                        # print(USER_CLICK_X)
                        # print(upPt.GetY())
                        # print(USER_CLICK_Y)
                        xdiff = abs(upPt.GetX() - USER_CLICK_X)
                        ydiff = abs(upPt.GetY() - USER_CLICK_Y)
                        if xdiff <= .01 and ydiff <= .01:
                            upSite =  None
                        
                        else:
                            sid = SiteID(s[0].GetFieldAsString(siteNumber_index))
                            #print("made unique Site {0}".format(sid))
                            s = Site(siteCounter,upPt.GetX(),upPt.GetY(),0,isl=True)
                            s.assignedID = sid
                            sitesStore[s_geom] = s
                            upSite = s     
                            siteCounter += 1                 
                  
                elif s_geom.Intersects(downPt):
                    # Found existing lower extent
                    b_f[1] = True
                    foundExistingSiteGeom = False
                    for k,v in sitesStore.items():
                        if k.Intersects(s_geom):
                            # Use the existing entry as site
                            foundExistingSiteGeom = True
                            downSite = sitesStore[k]                            
                            
                    if not foundExistingSiteGeom:
                        # print(upPt.GetX())
                        # print(USER_CLICK_X)
                        # print(upPt.GetY())
                        # print(USER_CLICK_Y)
                        xdiff = abs(upPt.GetX() - USER_CLICK_X)
                        ydiff = abs(upPt.GetY() - USER_CLICK_Y)
                        if xdiff <= .01 and ydiff <= .01:
                            downSite = None
                        
                        else:
                            # Need to create our own an add it to the table
                            sid = SiteID(s[0].GetFieldAsString(siteNumber_index))
                            #print("made unique Site {0}".format(sid))
                            s = Site(siteCounter,downPt.GetX(),downPt.GetY(),0,isl=True)
                            sitesStore[s_geom] = s
                            siteCounter += 1
                            s.assignedID = sid
                            downSite = s
                 
                
            # Find out which lines intersect on that point
            for k,v in lBufferStore.items():
                if k == e:
                    continue
                else:
                    k_geom = k.GetGeometryRef()
                    if k_geom.Intersects(upBuff) and not b_f[0]:
                        # Found an upstream flowline
                        queue.append(k)
                    elif k_geom.Intersects(downBuff) and not b_f[1]:
                        # Found a downstream flowline
                        queue.append(k)
            # Declare we have now visited and added this line
            lBufferStore[e] = True
            # Say our flowline has connections to each node, then,
            
            # If no real sites intersect at this point, maybe there are fake
            # ones which do already
            if upSite is None:
                # Try and find site in existing table or create it
                foundExisting = False
                for k,v in sitesStore.items():                    
                    if k.Intersects(upPt):
                        foundExisting = True
                        upSite = sitesStore[k]
                if not foundExisting:
                    s = Site(siteCounter,upPt.GetX(),upPt.GetY(),0)

                    sitesStore[upPt.Buffer(1)] = s
                    upSite = s
                    siteCounter += 1
                
            if downSite is None:
                # Try and find site in existing table or create it
                foundExisting = False
                for k,v in sitesStore.items():
                    if k.Intersects(downPt):
                        foundExisting = True
                        downSite = sitesStore[k]
                if not foundExisting:
                    s = Site(siteCounter,downPt.GetX(),downPt.GetY(),0)

                    downSite = s
                    sitesStore[downPt.Buffer(1)] = s
                    siteCounter += 1
                    
            fid = counter
            flen = float(e.GetFieldAsString(lineLength_index))
            fName = e.GetFieldAsString(lineName_index)
            fCode = e.GetFieldAsString(lineFCode_index)
            fRC = int(e.GetFieldAsString(lineRC_index)) # Go 1676!!
            f = Flow(fid,upSite,downSite,flen,fRC)
            counter +=1
            if e == startingLine:
                starterFlow = f
            # Line has been constructed, add to the table
            upSite.flowsCon.append(f)
            downSite.flowsCon.append(f)
            flowList.append(f)
            
    # From the stored sites and flows, derive the network structure
    netti = Network(flowList,list(sitesStore.values()))
    starterFlow = removeUseless(netti,True,starterFlow) # Pass in starterFlow so we can re-assign it
    
    return [netti,inputPointProj,startingLine,starterFlow,siteLayer,interSites,len(siteLayer)]
    
    #dataFolder,siteLayerName

def determineNewSiteID(x,y,gdalData,cf=2,VIS=False,isTest=False):
    '''
    Attempts to calculate a new siteID with the given data information.

    Raises Exception if any step along the way fails

    longg [Number]: Longitude in decimal degree (float) notation
    latt [Number]: Latitude in decimal degree (float) notation
    gdalData [GDALData]: data object to use
    cf [Number]: Clump Factor for optimal radius calculation (Default 2)
    VIS [Bool]: Should we launch the visualizer (Default False)
    isTest [Bool]: Are we operating in test mode? (Default True)

    Returns [SiteID]: The SiteID object to be calculated at the specified longg latt. (3)

    *(1) The site shapefile must be the same name as the folder it is in
    *(2) The line shapefile must be the sname name as the folder it is in
    *(3) The longg and latt MUST be snapped on or within 1 meter of the lines.

    '''
    [net,ucPoint,startingLine,startFlow,siteLayer,interSites,numSites] = isolateNetwork(gdalData,x,y,UC_BUFFER_MIN,None,cf)
    net.calculateUpstreamDistances()    
    net.calcStraihler()    
    reals = net.getRealSites()

    def return_site(newSite, gdalData):
        if newSite.extension:
            extension_flag = True
            siteLayer = gdalData.siteLayer
            siteNumber_index = siteLayer.GetLayerDefn().GetFieldIndex("site_no")
            oRef = osr.SpatialReference()
            oRef.ImportFromEPSG(4326)
            # Reproject
            targRef = osr.SpatialReference()
            targRef.ImportFromEPSG(26918)
            cTran = osr.CoordinateTransformation(targRef,oRef)
            for site in siteLayer:
                siteID = site.GetFieldAsString(siteNumber_index)
                siteID = SiteID(siteID)
                if siteID.value == newSite.value:
                    extension_flag = False
                    break

            if extension_flag:
                newSite.extension = None
                newSite.id = newSite.value
                newSite.fullID = newSite.id
                return newSite
            else:
                return newSite     
        else:
            return newSite
    def find_with_no_sites(gdalData,minStartFour=None):
        # We have no reference to base off of, select a new first four digit series and select the middle
            digitBasis = getFirstFourDigitFraming(gdalData)
            digitBasis.sort()
            # Find a gap in the numbers
            before = None
            minStartID = None
            for digits in digitBasis:
                if before is None:
                    if minStartID is None:
                        before = digits
                        continue
                    else:
                        if int(digits) > int(minStartFour):
                            before = digits
                            continue
                if int(digits) - int(before) > 1:
                    # We have a gap
                    break
                else:
                    before = digits     
            if before is None:
                raise RuntimeError("find_with_no_sites [Error]: minStartFour provided too high")       
            newHighest = (int(before) + 1) * 10000 + 5000
            newHighest = "%08d" %(newHighest)
            newSiteID = SiteID(newHighest)
            return return_site(newSiteID, gdalData)

    def interpolateLine(isTesting = isTest):

        '''
        Will compute the ID for the new site based on ambient data in this surrounding function
        '''
        if (isTesting):
            if startFlow.downstreamSite.id == 0:
                return startFlow.downstreamSite.assignedID
            else:
                return startFlow.upstreamSite.assignedID
        cs = startFlow.downstreamSite.connectedSites()
        ups = startFlow.upstreamSite

        otherBranch = None
      
        for con in cs:
            if con[1] == UPSTREAM_CON and con[0] != ups:
                otherBranch = con[2]

        upstreamID = startFlow.upstreamSite.assignedID
        downstreamID = None
        if otherBranch is None:
            # We are at a loop head or at a sink -> node point. Just use the upstream and downstream     
            downstreamID = startFlow.downstreamSite.assignedID        
        else:
            if startFlow < otherBranch:
                downstreamID = startFlow.downstreamSite.assignedID
            else:
                downstreamID = startFlow.downstreamSite.downwardRefID

        # Find out how far along the line the x,y click is
        l_geom = startingLine.GetGeometryRef()
        ucBuff = ucPoint.Buffer(1)
        ldiff = l_geom.Difference(ucBuff)
        assert(ldiff.GetGeometryCount() == 2)

        ucToLower_Frac = ldiff.GetGeometryRef(1).Length() / l_geom.Length()
        lengthP = startFlow.length * ucToLower_Frac
        
        YAY = downstreamID - lengthP
        
        return return_site(YAY, gdalData)

    # -------- DIFFERENT REAL SITE CASES -------------------------
    #------------------------------------------------------------
    #Visualizer.visualize(net)
    
    def foundSomething():
        if len(reals) == 1:
            sinks = net.calculateSink()
            if len(sinks) > 1:
                min_len = 100000
                min_sink = None
                for sink in sinks:
                    temp = testFlight(net, startFlow, sink)
                    if len(temp) < min_len and len(temp) != 1:
                        min_len = len(temp)
                        min_sink = sink
                sink = min_sink
            else:
                sink = sinks[0]
            if reals[0] == sink:
                # We should run pSNA from the site upstream from the sink
                uSiteID = sink.assignedID - sink.flowsCon[0].length

                pSNA(net,uSiteID,sink.flowsCon[0].upstreamSite)

            else:
                rsc = net_tracer(net)    
                # Next, run the normal algorithm but do not overwrite the calculated ones
                assert(len(rsc) == 1)
                iSNA(net,rsc[0])
                if VIS:
                    newSite = interpolateLine()
                    Visualizer.visualize(net, USER_CLICK_X, USER_CLICK_Y, newSite)
            
            newSite = interpolateLine() 
            return return_site(newSite, gdalData)      
        
        else:
            # We must conform to the SiteTheory Standard for multiple sites
            # Determine order of execution            
            orderedList = testFlight(net,startFlow)
            
            fIndex = -1 #index where the starter flow is
            lIndex = -1 # Index of lower site (a site below the target flow)
            uIndex = -1 # Index of upper site (a site above the target flow)
            for i in range(len(orderedList)):
                obj = orderedList[i]
                if isinstance(obj,Flow) and obj == startFlow:
                    fIndex = i
                elif isinstance(obj,Site) and (obj.assignedID > 0):
                    # We have a real site
                    if fIndex == -1:
                        lIndex = i
                    else:
                        uIndex = i
                        break # Weve found the upper index, break
            # Determine the scenario 
            if uIndex == -1 and (lIndex > -1 and fIndex > -1):
                # Scenario <>---...---- (target flow)
                # Run PSNA from the lower site
                #pSNA(net,orderedList[lIndex].assignedID,orderedList[lIndex])
                rsc = net_tracer(net)    
                # Next, run the normal algorithm but do not overwrite the calculated ones
                #Visualizer.visualize(net)
                rsc.sort(key=lambda chain: len(chain),reverse=False)
                for chain in rsc:
                    iSNA(net,chain)
                
                if VIS:
                    newSite = interpolateLine()
                    Visualizer.visualize(net, USER_CLICK_X, USER_CLICK_Y, newSite)           
                newSite = interpolateLine()
                return return_site(newSite, gdalData)

            elif (uIndex > -1 and fIndex > -1) and lIndex == -1:
                # Scenario ---- (target flow) ---...---<>
                # Run iSNA as if we had a single site
                rsc = net_tracer(net)    
                # Next, run the normal algorithm but do not overwrite the calculated ones
                rsc.sort(key=lambda chain: len(chain),reverse=False)
                for chain in rsc:
                    iSNA(net,chain) 
                
                if VIS:
                    newSite = interpolateLine()
                    Visualizer.visualize(net, USER_CLICK_X, USER_CLICK_Y, newSite)
                newSite = interpolateLine()
                return return_site(newSite, gdalData)
            elif str(orderedList[lIndex].assignedID)[0:4] != str(orderedList[uIndex].assignedID)[0:4]:
                # We have two different series on the same line. Just use the downstream ID and work from
                # there only
                raise RuntimeError("Error: Unimplemented conflicting series check!")
            else:
                # Scenario <>-- ... -- (target flow) --- ... ---<>
                # Only isolate a network from lIndex to uIndex
                nettL = orderedList[lIndex:uIndex + 1] # (becacuse slicing isnt inclusive in python)
                sl = []
                fl = []

                for obj in nettL:
                    if isinstance(obj,Site):
                        sl.append(obj)
                    elif isinstance(obj,Flow):
                        fl.append(obj)

                netti = Network(fl,sl)
                
                
                netti.recalculateTotalLength()
                #Visualizer.visualize(netti)
                # Calculate the new UnitLength based on:
                diff = sl[0].assignedID - sl[len(sl) - 1].assignedID # A SiteID - SiteID should give me a decimal number or something
                UL = diff / netti.totalSize 

                if abs(UL) != UL:
                    # We have an error in SiteID's. The downstream ID is lower than the upstream ID
                    # Revert to case where we have one real upstream ID only
                    rsc = net_tracer(net,nettL[len(nettL) - 1])    # Force the origin of net_tracer to the upstream ID
                    # Next, run the normal algorithm but do not overwrite the calculated ones
                    iSNA(net,rsc[0])

                    if VIS:
                        newSite = interpolateLine()
                        Visualizer.visualize(net, USER_CLICK_X, USER_CLICK_Y, newSite)
                    newSite = interpolateLine()
                    return return_site(newSite, gdalData)
                    
                else:
                    # We have a valid UL, now compute the ID from the bottom ID, and theoretically everything
                    # should work out, in theory!
                    netti.unitLength = UL

                    uSiteID = sl[0].assignedID - (sl[0].flowsCon[0].length * UL)
                    # Go based on the orderedList Now, since basing off of a new would be a disaster
                    # (i.e.) due to the removal process, some things will be disconnected or 
                    # unreachable
                    distAccum = 0
                    deltaD = 0
                    currID = None
                    for i in range(lIndex,uIndex):
                        obj = orderedList[i]
                        if isinstance(obj,Site):                        
                            if currID is None:
                                currID = obj.assignedID
                                continue # First iteration, no counting
                            else:
                                # Try to compute a new ID for this object
                                # Since the ordered list is essentially a linearized network, we can
                                # just subtract each time
                                currID = currID - (deltaD * UL)
                            if obj.assignedID < 0 or obj.assignedID is None:
                                # We dont have an obj ID yet, assign
                                obj.assignedID = currID
                        elif isinstance(obj,Flow):
                            if obj.downstreamSite.assignedID < 0:
                                # Lets pretend were using the reference ID (the currID)
                                obj.downstreamSite.assignedID = currID

                            deltaD = obj.length
                            distAccum += obj.length                
                    # Here we must do our own interpolate line because we have a
                    # special disjointed network case
                    if isTest:
                        if startFlow.downstreamSite.id == 0:
                            return startFlow.downstreamSite.assignedID
                        else:
                            return startFlow.upstreamSite.assignedID
                    else:
                        l_geom = startingLine.GetGeometryRef()
                        ucBuff = ucPoint.Buffer(1)
                        ldiff = l_geom.Difference(ucBuff)
                        if ldiff.GetGeometryCount() != 2:
                            ucToLower_Frac = ldiff.Length() / l_geom.Length()
                        else:
                            ucToLower_Frac = ldiff.GetGeometryRef(1).Length() / l_geom.Length()

                        lengthP = orderedList[fIndex].length * ucToLower_Frac
                        
                        YAY = orderedList[fIndex].downstreamSite.assignedID - (lengthP * UL)
                        if VIS:
                            Visualizer.visualize(net, USER_CLICK_X, USER_CLICK_Y, YAY)
                        
                        return return_site(YAY, gdalData)
    if len(reals) < 1:
        # We need to base our siteID off of the length of the networks which the other
        # next numbered sites sharing the first four numbers are on.      
        
        # Try running again but this time go to the extreme,
        # based on the site density of the state
        prev = determineOptimalSearchRadius(NY_STATE_AREA,numSites,3)
        r = min(determineOptimalSearchRadius(NY_STATE_AREA,numSites,5),UC_BUFFER_MAX)

        reals = []
        if r <= UC_BUFFER_MAX:
            # Radius recommended does not exceed upper bounds! Execute again
            [net,ucPoint,startingLine,startFlow,siteLayer,interSites, length] = isolateNetwork(gdalData,x,y,prev,r)    
            net.calculateUpstreamDistances()    
            net.calcStraihler()    
            reals = net.getRealSites()

        if len(reals) == 0:
            if len(interSites) < 1:
                id = find_with_no_sites(gdalData)
                if VIS:
                    Visualizer.visualize(net, USER_CLICK_X, USER_CLICK_Y, id)
                return return_site(id, gdalData)
            else:
                # Try and guess based off of the next highest in that local area
                ff = getFirstFourDigitFraming_Existing(gdalData, interSites)
                ff.sort(reverse=True)
                assert(len(ff) > 0)
                id = find_with_no_sites(gdalData,ff[0])
                if VIS:
                    Visualizer.visualize(net, USER_CLICK_X, USER_CLICK_Y, id)
                return return_site(id, gdalData)
        else:
            return foundSomething()
    else:
        return foundSomething()
    
if __name__ == "__main__":
    # Set a time limit on execution of this module to 30 seconds
    #multiprocessing.set_start_method('spawn', True)
    print("started")
    BASE_DIR = os.path.join( os.path.dirname(os.path.dirname( __file__ )))
    #folderPath = BASE_DIR + '/data/'
    #arguments = sys.argv[1]
    #a = arguments.split(",")
    x = -74.3254918    #Long Lake
    y =  44.0765791
    a = [x,y]
    gdalData = GDALData()
    gdalData.loadFromData()
    gdalData.loadFromQuery(x, y)
    #newSite = determineNewSiteID_Timely(float(a[0]),float(a[1]),gdalData,60)
    newSite = determineNewSiteID(float(a[0]),float(a[1]),gdalData,60)
    res = {'Results': str(newSite)}
    results = json.dumps(res)
    print("results = " + results)
    
    '''

       _____           _    _               
      |_   _|         | |  (_)              
        | |  ___  ___ | |_  _  _ __    __ _ 
        | | / _ \/ __|| __|| || '_ \  / _` |
        | ||  __/\__ \| |_ | || | | || (_| |
        \_/ \___||___/ \__||_||_| |_| \__, |
                                       __/ |
                                       |___/ 
 
    '''
    # path_sites = str(folderPath) + "/" + str(siteLayerName) + "/" + str(siteLayerName) + ".shp"

    # file = open("GeneratedSiteTests.csv", "w")
    # writer = csv.writer(file)
    # writer.writerow(["Human", "Algorithm", "Runtime"])
    # sitesDataSource = ogr.Open(path_sites)
    # sl = sitesDataSource.GetLayer()
    # siteNumber_index = sl.GetLayerDefn().GetFieldIndex("site_no")
    # counter = 0
    # oRef = osr.SpatialReference()
    # oRef.ImportFromEPSG(4326)
    # # Reproject
    # targRef = osr.SpatialReference()
    # targRef.ImportFromEPSG(26918)
    # cTran = osr.CoordinateTransformation(targRef,oRef)
    # newSeriesCntr = 0
    # regCntr = 0
    # for site in sl:
    #     siteID = site.GetFieldAsString(siteNumber_index)
    #     sgeom = site.GetGeometryRef()
    #     x = sgeom.GetX()
    #     y = sgeom.GetY()
    #     [longg,latt,z] = cTran.TransformPoint(x,y)
    #     try:
    #         before = time.time()
    #         newSite = determineNewSiteID_Timely(longg,latt,folderPath,siteLayerName,lineLayerName,60)
    #        #newSite = determineNewSiteID(longg, latt, folderPath, siteLayerName, lineLayerName)
    #         print("RAN!")
    #         after = time.time()
    #         writer = csv.writer(file)
    #         writer.writerow([str(siteID), str(newSite), after-before])
    #         if newSite == SiteID("00345000"):
    #             newSeriesCntr += 1
    #         else:
    #             regCntr += 1
    #     except Exception as e:
    #         writer = csv.writer(file)
    #         writer.writerow([str(siteID), "ERROR: " + str(e), "NaN"])
    #         print("Error on finding")
    #     # if newSeriesCntr + regCntr > 100:
    #     #     break
    # file.close()
