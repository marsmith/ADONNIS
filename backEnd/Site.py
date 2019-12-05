#!/usr/bin/python3.6


from LatLong import *
from SiteID import *

DOWNSTREAM_CON = 1
UPSTREAM_CON = 2

class Site(object):
    '''
    Description
    ---------------------------------------------------------------------------
    Represents the endpoint of a Flow. The "Nodes" of a Network. Stored
    in the SitesTable of the Network. Multiple sites may exist on the same point
    but all should have a unique ID

    Class Variables
    ---------------------------------------------------------------------------
    id [number] : Site's ID
    latLong [LatLong] : The location of the Site 
    z [number] : Unused
    h [number] : Unused
    flowsCon [list] : List of flows connected to the Site
    assignedID [number] : Assigned Site ID
    pendingUpstream : Number of flows that have yet to be processed, -1 if none
    downwardRefID [number] : Downward reference ID for the Site, None if there isn't any

    Usage
    ---------------------------------------------------------------------------

    '''
    def __init__(self,id,lat,long,h=0,z=0,flC = None,isl = False):
        '''
        Constructs a new Site object

        id [number]: id (0 to 9999)
        lat [float] : Valid latitude for the Site
        long [float] : Valid longitude for the Site
        h [number] : Unused
        z [number] : Unused (default = 0)
        flC [list] : List will hold the flows connected to the Site (default = None)
        isReal [bool]: Is this site a real site with real data yet
        '''
        self.id = id
        self.latLong = LatLong(lat,long)
        self.z = z
        self.h = h
        self.isReal = isl
        self.extraVar = 0 # Used in the dryRun algorithm
        if flC == None:
            self.flowsCon = []
        self.assignedID = -1 # This is what is assigned via algorithm
        self.pendingUpstream = -1
        self.downwardRefID = None # This is what is stored as reference to the next downstream ID
                                    # For resolving assignments in the Plotter
    
    def __eq__(self,other):
        '''
        Performs a '==' comparison between the calling Site and other

        other [Site]: The other side of the '==' to compare to

        Returns [bool]: True if self is equal to other. False otherwise.
        '''
        return self.id == other.id
    def __lt__(self,other):
        '''
        Performs a '<' comparison between the calling Site and other

        other [Site]: The other side of the '<' to compare to

        Returns [bool]: True if self is less than or equal to other. False otherwise.
        '''
        return self.id < other.id
    def __gt__(self,other):
        '''
        Performs a '>' comparison between the calling Site and other

        other [Site] : The other side of the '>' to compare to

        Returns [bool] : True if self is greater than to other. False otherwise.
        '''
        return self.id > other.id
    def isConfluence(self):
        '''
        Returns [Bool]: Is this Site a confluence or not?
        '''
        cs = self.connectedSites()
        numUp = 0
        numDown = 0
        for e in cs:
            if e[1] == UPSTREAM_CON:
                numUp += 1
            elif e[1] == DOWNSTREAM_CON:
                numDown += 1
        return numUp != 1 and numDown != 1
        
    def calculatePendingUpstream(self):
        '''
        Calculates the number of pending upstreams a site has

        Updates class variable "pendingUpstream"
        '''
        cs = self.connectedSites()     
        cntr = 0   
        for e in cs:
            if e[1] == UPSTREAM_CON:
                cntr += 1
                
        self.pendingUpstream = cntr

    def emptyCopy(self):
        '''
        Will create a clone of the Site object but without flowConInfo

        Returns [Site] copy (in separte memory) of this object
        '''        
        s2 = Site(self.id,self.latLong.lat,self.latLong.long,self.h,self.z)
        return s2

    def hasAssignedIDEquality(self,other):
        '''
        Performs an ID comparison between the calling Site and other

        other [Site] : The other side of the '==' to compare to

        Returns [bool] : True if self.self.assignedID is the same as other.self.assignedID. False otherwise.
        '''
        return self.assignedID == other.assignedID
    def hasPositionalEquality(self,other):
        '''
        Performs an LatLong comparison between the calling Site and other

        other [Site] : The other side of the '==' to compare to

        Returns [bool] : True if self.latlong is the same as other.latlong. False otherwise.
        '''
        return self.latLong == other.latLong
    def __str__(self):
        '''
        Returns a string version of the Site
        Returns [str]
        '''
        return "Site <{0}> {1}".format(self.id,self.latLong)
    def addFlow(self,flow):
        '''
        Adds a flow to the list of flows the Site is connected to 

        flow [Flow] : The flow object that is to be added to self.flowsCon

        '''
        self.flowsCon.append(flow)
    def isProperNode(self):
        '''
        Performs a check on the Site. Ensures that it is a proper Site.

        A proper Site has at either 1 or 3 flows connected. 

        Returns [bool] : True if it's a proper Site. False otherwise. 
        '''
        # Return if there is either one line connected (source or sink) or is a confluence (three)
        # Will return false if this site is intermediately on a line
        return len(self.flowsCon) >= 1 and len(self.flowsCon) <= 3 and not len(self.flowsCon) == 2
    
    def removeInvolvedFlows(self,site):
        '''
        DO NOT USE OUTSIDE FO PRECONFIGURATION

        Used it RemoveUseless() function. Deletes the flows that were connected
        to removed Sites. 

        '''
        i = 0        
        while i in range(len(self.flowsCon)):
            f = self.flowsCon[i]
            if f.upstreamSite == site or f.downstreamSite == site:
                self.flowsCon.pop(i)
            else:
                i += 1 
    

    def connectedSites(self):
        '''
        Creates a list of connected sites and provides them with important information
        to reduce look up time.

        Adds connected Sites to the list in a tuple with format : (Site, "DOWNSTREAM_CON"/"UPSTREAM_CON", flow)

        Returns [List((Site, Dir, Flow))] : Returns the list of connected sites. 
        '''
        csl = []
        for f in self.flowsCon:
            us = f.upstreamSite
            ds = f.downstreamSite
            if us == self:
                csl.append((ds,DOWNSTREAM_CON,f))
            elif ds == self:
                csl.append((us,UPSTREAM_CON,f))
        return csl
    
    def getUpstream(self):
        '''
        Creates a list of all upstream Sites from one Site

        Returns [List(Site)] : list of all upstream Sites
        '''
        ups = []
        cs = self.connectedSites()
        for con in cs:
            if con[1] == UPSTREAM_CON:
                ups.append(con[0])
        return ups

    def getDownstream(self):
        '''
        Creates a list of all downstream Sites from one Site

        Returns [List(Site)] : list of all downstream Sites
        '''
        down = []
        cs = self.connectedSites()
        for con in cs:
            if con[1] == DOWNSTREAM_CON:
                down.append(con[0])
        return down
    __repr__ = __str__