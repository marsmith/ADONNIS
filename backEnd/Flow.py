DOWNSTREAM_CON = 1
UPSTREAM_CON = 2

class Flow(object):
    '''
    Description
    ---------------------------------------------------------------------------
    Represents a flowline which connects two sites (either fake or real)
    Has unique ID to be updated in precompilation; contains reach code
    and length attributes as well as reference to which sites are the
    endpoints (these should be found in the sitesTable of the Network() object)

    Class Variables
    ---------------------------------------------------------------------------
    upstreamSite [Site] : The upstream Site of the flow
    downstreamSite [Site] : The downstream Site of the flow
    id [number] : The flow's Id number
    reachCode [number] : The flow's reach code 
    name [String] : The GNIS Name of the flow 
    length [float] : The length of the flow segment
    thisAndUpstream [float]: The length of the current flow segment + the distance to the "sink" Site.
    unadressable [bool] : Bool that represents if a flow has no allocated address space and must be ignored

    Usage
    ---------------------------------------------------------------------------

    '''
    def __init__(self,id,startSite,endSite,length,reachCode = -1,name=None):
        '''
        Constructs a new Flow object

        id [number]: id (0 to 9999)
        startSite [Site]: The upstream site of the flow
        endSite [Site]: The downstream site of the flow
        length [number] : The length of the flow
        reachCode [number] : The reach code of the flow (default = -1)
        name [String] : The name of the flow (default = None)
        '''
        self.upstreamSite = startSite
        self.downstreamSite = endSite
        self.id  = id
        self.reachCode = reachCode
        self.name = name
        self.length = length
        self.thisAndUpstream = self.length # This and upstream length
        self.unadressable = False # If a flow leads to a site which has already been ID'd, it must be part of the closing flow of a loop
                                # It has no allocated address space and must be ignored
        self.straihler = -1
    def __lt__(self,other):
        '''
        Performs an Flow priority comparision between the calling Site and other

        other [Site] : The other flow that will be compared

        Returns [bool] : True if self has a lower priority than other. False otherwise.
        '''
        return self.hasHigherPriority(other)
    def getSiteByID(self,id):
        '''
        Attempts to return either the upstream or downstream site if it matches the ID given
        id [SiteID]: Comparison Object

        Retuns [SiteID] or None: Depends on if there is a match
        '''
        if self.upstreamSite.id == id:
            return self.upstreamSite
        elif self.downstreamSite.id == id:
            return self.downstreamSite
        return None
    def emptyCopy(self):
        '''
        Return a new Flow object based on 1st level data
        (The connections between objects are not stored)
        '''
        fl2 = Flow(self.id,self.upstreamSite.emptyCopy(),self.downstreamSite.emptyCopy(),self.length,self.reachCode,self.name)
        return fl2

    def hasHigherPriority(self,otherFlow):
        '''
        Determines which flow to go to first

        Return [bool] : True if self has a higher priority than other. False otherwise.
        '''

        # Returns true if this is
        if self.name is None:
            if otherFlow.name is None:
                # Compare based on .thisAndUpstream
                return self.thisAndUpstream < otherFlow.thisAndUpstream
            else:
                return False # Other has higher priority bc it is named
        else:
            if otherFlow.name is None:
                return True # Self is named and other is not
            else:
                # Both are named, go by distance
                return self.thisAndUpstream < otherFlow.thisAndUpstream

    def __le__(self,other):
        '''
        Performs an Flow priority comparision between the calling Site and other

        other [Site] : The other flow that will be compared

        Returns [bool] : True if self has a lower priority than other or if they're equal to eachother. False otherwise.
        '''
        return self.hasHigherPriority(other) or self.__eq__(other)

    def __gt__(self,other):
        '''
        Performs an Flow priority comparision between the calling Site and other

        other [Site] : The other flow that will be compared

        Returns [bool] : True if self has a higher priority than other. False otherwise.
        '''
        return not self.__le__(other) 
    def __eq__(self,other):
        '''
        Compares this flow to 'other' Flow

        Returns [bool]: True if both Flow's reach codes are the same or have the same ID
        Precondition: 'other' must be a Flow object
        '''
        return self.reachCode == other.reachCode or self.id == other.id
    def __str__(self):
        '''
        Returns a string representation of the Flow, following this format:
        Flow <flow #> upstream is {upstreamSite.id}, downstream is {downstreamSite.id}
        (Note: upstreamSite.id refers to the associative number (0,1,2,3), NOT the SiteID's (10019999,...))

        Returns [string]: String representation
        '''
        return "Flow <{0}> upstream is {1}, downstream is {2}".format(self.id,self.upstreamSite.id,self.downstreamSite.id)
    __repr__ = __str__