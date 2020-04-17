#!/usr/bin/python3.6


from Precompiler import *
DOWNSTREAM_CON = 1
UPSTREAM_CON = 2

def net_tracer(network,forcedOrigin=None):
    '''
    Returns a list of sites which are along the real->sink chain
    '''
    real_sites_counter = 0
    realSiteQueue = []
    rsc = [] # real to sink chain
    for site in network.siteTable:
        if site.isReal:
            if forcedOrigin and site == forcedOrigin:
                real_sites_counter += 1
                realSiteQueue.append(site)
                rsc.append([])
            else:
                real_sites_counter += 1
                realSiteQueue.append(site)
                rsc.append([])
    rsc_c = 0
    while len(realSiteQueue) > 0:
        c = realSiteQueue.pop(0)
        queue = [c]
        while (queue):
            curr = queue.pop()
            
            conTup = curr.connectedSites()
            current_flow = None
            for con in conTup:
                if con[1] == DOWNSTREAM_CON:
                    current_flow = con[2]
                    foundDown = True # We found a new downstream
            
            if current_flow is None:
                # We must be dealing with upstreams only
                continue
                
            dsDest = current_flow.downstreamSite
            # Get the other flow which is upstream of the shared confluence
            conTup = dsDest.connectedSites()
            other_flow = None
            numUpStr = 0
            for con in conTup:
                if con[1] == UPSTREAM_CON and con[0] != curr:
                    other_flow = con[2]
                    numUpStr += 1
            
            # Special cases -----
            if not (current_flow.downstreamSite.assignedID is -1 or current_flow.downstreamSite.assignedID is None ):
                    # Already assigned! Do not do anything more
                continue # So we dont add to the queue again
            if dsDest == network.calculateSink()[0] and not dsDest.isConfluence():
                # The next site is a sink downstream; apply special rule
                dsDest.assignedID = curr.assignedID + current_flow.length
                break

            
            if not other_flow is None:

                if current_flow < other_flow:
                    # current <= other
                    if (curr.assignedID is -1 or curr.assignedID is None ):
                        r = curr.id
                    else:
                        r = curr.assignedID
                    l = r - other_flow.thisAndUpstream
                    
                    current_flow.downstreamSite.assignedID =  r + current_flow.length # Conf. ID

                    if curr == c:
                        current_flow.downstreamSite.downwardRefID = r

                    #assign other upstream site
                    #other_flow.upstreamSite.id = current_flow.upstreamSite.id - other_flow.thisAndUpstream
                
                else:
                    # current > other
                    if (curr.assignedID is -1 or curr.assignedID is None ):
                        l = curr.id
                    else:
                        l = curr.assignedID

                    r = l + current_flow.length                
                    current_flow.downstreamSite.assignedID = r + other_flow.thisAndUpstream
                    #current_flow.downstreamSite.downwardRefID = r

                    #Assign other upstream site
                    #other_flow.upstreamSite.id = other_flow.downstreamSite.id - other_flow.thisAndUpstream
            else:
                # We have no other flow, we just need to progress downstream
                if (curr.assignedID is -1 or curr.assignedID is None ):
                        l = curr.id
                else:
                    l = curr.assignedID
                current_flow.downstreamSite.assignedID = l + current_flow.length

            queue.append(current_flow.downstreamSite)
            rsc[rsc_c].append(current_flow.downstreamSite)
        rsc_c += 1
    return rsc

            
