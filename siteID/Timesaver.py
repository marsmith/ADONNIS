from GDALCode import *
import multiprocessing as mp

def recoverReturn(longg,latt,folderPath,siteLayerName,lineLayerName,returnDict):
    try:
        returnDict["data"] = determineNewSiteID(longg,latt,folderPath,siteLayerName,lineLayerName)
    except Exception as e:
        returnDict["exception"] = e


def determineNewSiteID_Timely(longg,latt,folderPath,siteLayerName,lineLayerName,numSecAllowed=30):
    '''
    Attempts to calculate a new siteID with the given data information in a certain number of seconds
    Raises RuntimeError if the process goes over the specified time limit
    longg [Number]: Longitude in decimal degree (float) notation
    latt [Number]: Latitude in decimal degree (float) notation
    folderPath [String]: Path where the shapefile folders are
    siteLayerName [String]: Folder name where the site shapefile is. (1)
    lineLayerName [String]: Folder name where the line shapefile is. (2)
    numSecAllowed [Number]: Number of seconds to complete the siteID finding process (3)

    Returns [SiteID]: The SiteID object to be calculated at the specified longg latt. (4)

    *(1) The site shapefile must be the same name as the folder it is in
    *(2) The line shapefile must be the sname name as the folder it is in
    *(3) If the process completes under the time limit, the method will not wait the full time period
        i.e. if we complete in 5 sec but allow for 30, we will exit out of the method in 5 sec, not 30
    *(4) The longg and latt MUST be snapped on or within 1 meter of the lines.

    '''
    
    man = mp.Manager()
    rD = man.dict()
    x = mp.Process(target=recoverReturn,args=(longg,latt,folderPath,siteLayerName,lineLayerName,rD),daemon=True)
    
    timeSlept = 0
    x.start()
    while timeSlept < numSecAllowed:
        if x.is_alive():
            time.sleep(0.1)
        else:
            break
            time.sleep(0.1)
        timeSlept += 0.1
    if x.is_alive():
        x.terminate()
    if "data" in rD.keys():
        return rD["data"]
    elif "exception" in rD.keys():
        raise rD["exception"]
    else:
        raise RuntimeError("determineNewSiteID_Timely() [Error]: Could not determine ID in time")


# if __name__ == "__main__":
    # folderPath = "C:\\Users\\mpanozzo\\Desktop\\GDAL_DATA_PR"
    # siteLayerName = "ProjectedSites"
    # lineLayerName = "NHDFlowline_Project_SplitLin3"
    # longg = -73.52481561 #-76.3612354
    # latt = 41.1930218#43.4810611 
    # try:
    #     newID = determineNewSiteID_Timely(longg,latt,folderPath,siteLayerName,lineLayerName,1) 
    #     print(newID)
    # except Exception as e:
    #     print(e)
   
    