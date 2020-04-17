#!/usr/bin/python3.6

import json
import numpy
import sys
import Dijkstra
import copy
import test
import Visualizer
from LatLong import *
from SiteID import *
from Flow import *
from Site import *
from Network import *

degree_sign= u'\N{DEGREE SIGN}'


   
# Will return the site which either has positional eq with "site" or site itself
def peq(siteList,site):
    '''
    Will returns the site that has positional equality with 'site' argument or
    the provided 'site' variable itself.

    siteList [List(Of Site)]: List of sites to compare site with
    site [Site]: Site to compare with

    Returns [Site]: The site that has positional equality with 'site' argument or
    the provided 'site' variable itself.
    '''
    for e in siteList:
        if e.hasPositionalEquality(site):
            return e
    return site
    



def removeUseless(net,addLengths=False,ucFlow=None,removeReals=False):
    ''' 
    Will remove sites from the network with only two neighbors (1 up 1 down)
    Will then merge the two flows together into one flow, keeping the length
    of 1 of the deleted flows. (This is done to resolve MultiLineString) entries in
    geoJSON files.

    net [Network]: Network to operate on

    Returns [None]
    Notes: Do NOT run this method if you want to take loops into account as this
    method will break the runtime if loops are present!
    '''
    i = 0
    sf = ucFlow
    while i in range(len(net.siteTable)):
        sit = net.siteTable[i]
        if sit.isReal and not removeReals:
            i += 1
            continue
        cs = sit.connectedSites()        
        if len(cs) == 2 and cs[0][2].reachCode == cs[1][2].reachCode:
            # This site is deletable
            coni0 = cs[0]
            coni1 = cs[1]
            
                
            if addLengths:
                newLen = coni0[2].length + coni1[2].length
            else:
                assert(coni0[2].length == coni1[2].length)
                newLen = coni0[2].length
            fl2Add = None
            if coni0[1] == DOWNSTREAM_CON:
                # coni0 is downstream of deletable site ('sit')
                # coni1 is upstream
                fl2Add = Flow(coni0[2].id,coni1[0],coni0[0],newLen,coni0[2].reachCode)  
            else:
                # coni0 is upstream of 'sit'
                # coni1 is downstream
                fl2Add = Flow(coni1[2].id,coni0[0],coni1[0],newLen,coni1[2].reachCode) 
            if not sf is None:
                if sf.downstreamSite == sit or sf.upstreamSite == sit:
                    sf = fl2Add
            net.removeInvolvedFlows(sit)
            coni0[0].removeInvolvedFlows(sit)
            coni1[0].removeInvolvedFlows(sit)
            
            net.siteTable.remove(sit)
            coni0[0].flowsCon.append(fl2Add)
            coni1[0].flowsCon.append(fl2Add)
            net.flowTable.append(fl2Add)
            if i > 0:
                i -= 1
        else:
            i += 1

    return sf
            

def testFlight(net,ucFlow,sinkSite = None):
    '''
    Will run a lite version of pSNA (Will not alter any ID's at all).
    Usefull for getting the "order of execution" for an entire network
    
    uCFlow [Flow]: The flowline the user wants to start from

    sinkSite [Site]: The bottom of the network (the outflow, the root)

    Returns [List(Of Site or Flow)]: List of elements encountered (IN ORDER)
    while running testFlight
    '''
    if sinkSite is None:
        sinkSite = net.calculateSink()[0]
    
    orderedEncounter = []
    
    queue = []  
    starterTuple = (sinkSite,None,None)  
    queue.append(starterTuple)
    # Step 1: Starting from the sink site, assign the site.assignedID field
    
    while len(queue) >= 1:
        # Pop out the tuple
        t = queue.pop(0)
        u = t[0]
        f = t[2]
        u.extraVar = 1        
        if not f is None:
            orderedEncounter.append(f)
        orderedEncounter.append(u)
        
        cs = u.connectedSites()
        lifechoices = [] # The upstream paths we may choose              
        for theCon in cs:
            if theCon[1] == UPSTREAM_CON and theCon[0].extraVar == 0:
                # The connection is upstream and has not been assigned yet
                lifechoices.append(theCon)
            elif theCon[1] == UPSTREAM_CON:
                # This has been assigned already, seems like we are on a loop
                pass
        lifechoices.sort(key= lambda conTup1: conTup1[2],reverse=False)
        # Add these future explorations into the queue in order
        if len(cs) > 1:
            # Confluence, append to the begining of queue
            # but preserve the order of lifechoices in the queue as well        
            # Standard procedure
            iIns = 0
            for conTup in lifechoices:
                queue.insert(iIns,conTup)
                iIns += 1
            
        elif len(cs) == 1:
            # Non-Confluence, append to the end of the queue
            # This is to handle special cases such as loops
            if cs[0][0].extraVar == 0:
                # Not assgned yet!
                queue.append(cs[0])
        else:
            # Select the upstream node to go on
            assert(len(lifechoices) == 1)
            queue.append(lifechoices[0])
        
    return orderedEncounter
            
# --------------------------------------------------

def pSNA(net,maxDownstreamID,sinkSite = None,strict=False):
    '''
    Will assign real ID's to the fake nodes via the Proportional Site Naming Algorithm
    1km is the mininum distance to generate unique 8 digit ID's. 
    pSNA will NOT shift down ID's if one exists already. This is a theoretical model
    pSNA WILL generate 10 digit ID's if the distance accumulated between two sites is less than the
    unit length (1km by default)

    net [Network]: Network to perform algorithm on.

    maxDownstreamID [SiteID]: The maximal ID for the network. (This is what the sinksite will be)

    sinkSite [Site]: [Optional!] The lowermost site in the network. Parent to all. If not provided, will be computed

    strict [Boolean]: [Optional!] Determines if alg will allow for already ID'd nodes in the network. If False, will only look for
    downwardsRefID's and skip if there is one

    Returns [SiteID]: The last SiteID assigned to a part of the network by the algorithm.
    '''
    def alg(idBefore,leng,unitDist = 1): 
        ''' 
        Internal core algorithm. (Basically using the subtraction operator for a SiteID and Number)

        idBefore [SiteID]: What the ID was before

        leng [number]: Length to be computed with

        unitDist [number]: How long before the value portion of an ID ticks down to -1
        of the previous
        '''       
        return idBefore - (leng * unitDist)
    #---------------------------------------------------------------------

    # Use bitwise or to format final values
    if sinkSite is None:
        sinkSite = calculateSink(net)
    queue = []  
    starterTuple = (sinkSite,None,None)  
    queue.append(starterTuple)
    # Step 1: Starting from the sink site, assign the site.assignedID field
    idNext = maxDownstreamID
    
    while len(queue) >= 1:
        # Pop out the tuple
        t = queue.pop(0)
        u = t[0]
        if u.assignedID >= 0 and u.downwardRefID is None:
            # ID has already been assigned and we are not at the sink, must mean we just need to grab 
            # reference ID for this node
            u.downwardRefID = getLowestUpstreamNumber(net,u)
            continue
        
        cs = u.connectedSites()
        lifechoices = [] # The upstream paths we may choose              
        for theCon in cs:
            if theCon[1] == UPSTREAM_CON and theCon[0].assignedID < 0:
                # The connection is upstream and has not been assigned yet
                lifechoices.append(theCon)
            elif theCon[1] == UPSTREAM_CON:
                # This has been assigned already, seems like we are on a loop
                theCon[2].unadressable = True # Designate that this should not be allowed for use
                #print("Found Unadressable Flow sector: {0}".format(theCon[2]))
        lifechoices.sort(key= lambda conTup1: conTup1[2],reverse=False)
        # Add these future explorations into the queue in order
        if len(cs) > 1:
            # Confluence, append to the begining of queue
            # but preserve the order of lifechoices in the queue as well        
            # Standard procedure
            iIns = 0
            for conTup in lifechoices:
                queue.insert(iIns,conTup)
                iIns += 1
            refIDTup = (u,None,"REF")    
            if len(cs) > 2 and u.downwardRefID is None:
                # 3 way branch; needs reference ID
                queue.insert(iIns,refIDTup)
        elif len(cs) == 1:
            # Non-Confluence, append to the end of the queue
            # This is to handle special cases such as loops
            if cs[0][0].assignedID < 0:
                # Not assgned yet!
                queue.append(cs[0])
        else:
            pass

        if t[2] is None:
            u.assignedID = maxDownstreamID
            idNext = u.assignedID
        else:
            if isinstance(t[2],Flow):
                # We are not assigning a reference ID
                newID = alg(idNext,t[2].length,net.unitLength)        
                u.assignedID = newID
                u.downstreamID = idNext # The previous downstream ID is this
                idNext = newID

    return idNext # Return the last ID generated

def iSNA(net,rsc):
    '''
    Wrapper method of pSNA for running with real sites in network. Will execute pSNA one flow length
    away from an already assigned site in rsc

    net [Network]: Network to perform algorithm on.
    rsc [List(Of Site)]: List of sites which were assigned in net_tracer

    Returns None
    '''
    queue = []      
    # Step 1: Starting from the sink site, assign the site.assignedID field    
    distAccum = 0
    i = 0
    lastRef = None
    while i in range(len(rsc)):
        queue.append(rsc[i])
        while len(queue) >= 1:
            # Pop out the tuple
            u = queue.pop(0)
            # Basically go one layer out and then run pSNA from that point
            # Find the flow that has no data
            cs = u.connectedSites()
            startSite = None
            fl = None
            
            up_connections = []
            for con in cs:
                if con[1] == UPSTREAM_CON:
                    if con[0].assignedID < 0 or con[0].assignedID is None:
                        # We have a blank site. Start from here                        
                        up_connections.append(con[2])

            up_connections.sort()
            for con in up_connections:
                startSite = con.upstreamSite
                fl = con
                if startSite is None:
                    #print("INVALID START from {0}".format(u))
                    break
                elif u.downwardRefID is None and lastRef is None:
                    newSiteID = u.assignedID - fl.length
                elif u.downwardRefID is None:

                    newSiteID = lastRef - fl.length
                    u.downwardRefID = lastRef
                else:
                    newSiteID = u.downwardRefID - fl.length
                            
                lastRef = pSNA(net,newSiteID,startSite,False)
                # Determin the lastRef               
                if u.downwardRefID is None:
                    u.downwardRefID = lastRef

        i += 1

def getLowestUpstreamNumber(net,site):
    '''
    Gets the least (in number terms) upstream ID from a particular
    site. (Useful for refernce ID'ing confluences)

    net [Network]: Network to use in acquisition
    site [Site]: Starting point of curiosity

    Returns [SiteID]: Furthest upstream's SiteID
    '''
    return net.navigateFurthestUpstream(site).assignedID