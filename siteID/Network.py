DOWNSTREAM_CON = 1
UPSTREAM_CON = 2

class Network(object):
    '''
    Description
    ---------------------------------------------------------------------------
    Represents a collection of flows connected at the ends by sites and the relationships between each.
    Organized into two main tables a flow table and a site table (a table here is just a list).
    Keeps track of its total size (length of all flows combined)

    Class Variables
    ---------------------------------------------------------------------------
    totalSize [number]: Total length of the Network (length of all Flows). Must be 
                        Recomputed to be acurate via recalculateTotalLength()
    flowTable [List(Of Flow)]: The flows (or connections) in the Network
    siteTable [List(Of Site)]: The sites (or nodes) in the Network
    unitLength [number]: (IN KM!) How much distance before incrementing what
                         SiteID value portion should be assigned

    Usage
    ---------------------------------------------------------------------------
    (Here is an example of how to run the entire thing with a Network)
    >>> dictt = importJSON("Data/SmallNet001.json")
    >>> net = isolateNet(dictt,True)       
    >>> sinks = calculateSink(net)
    >>> setupSiteSafety(net)
    >>> faucets = calculateFaucets(net)
    >>> calculateUpstreamDistances(net,faucets)
    >>> net.recalculateTotalLength()
    >>> pSNA(net,SiteID(1001,9999,None),sinks[0])
    '''
    def __init__(self,flows,sites,unitLen = 1):
        '''
        Constructs a new Network object

        flows [List(Of Flow)]: Flowtable to initialize with
        sites [List (Of Site)]: Sitetable to initialize with
        unitLen [number]: How many (KM) before decrementing/incrementing the value portion of a SiteID
        '''
        self.totalSize = 0
        self.flowTable = flows
        self.siteTable = sites
        self.unitLength = unitLen # km; How many km before incrementing what ID should be assigned proportionally

    def recalculateTotalLength(self):
        '''
        Recalculates the Network's totalSize
        Returns [None]
        '''
        self.totalSize = 0
        for f in self.flowTable:
            self.totalSize += f.length
    
    def removeInvolvedFlows(self,site):
        '''
        Removes any flows from the flow table which have 'site' as
        one of the endpoints

        site [Site]: Site that if appearing in
                     a flow in the flow table, means the flow should be purged

        Returns [None]
        '''
        i = 0        
        s = set()
        while i in range(len(self.flowTable)):
            f = self.flowTable[i]
            if f.upstreamSite == site or f.downstreamSite == site:
                self.flowTable.pop(i)
            else:               
                i += 1

    def getRealSites(self):
        '''
        Determines a list of all the real sites in this network

        net [Network]: Network to perform analysis on

        Returns List[Of Site] sites in the sitetable (byref) which
        are real-world data collection sites (these probably also have already been assigned a real ID)

        '''
        r = []
        for s in self.siteTable:
            if s.isReal:
                r.append(s)
        return r

    def calculateSink(self):
        '''
        Calculate the sink for a given network. The sink is the most downstream
        Site of the entire Network. (If you think of the Network like a tree, it would
        be the root!)

        net [Network]: Network to perform analysis on

        Returns [Site]: The sink site of a network
        Raises RuntimeError if the graph has no sink (is invalid)!
        '''

        kaboodle = []
        for kit in self.siteTable:
            flag = True
            for flow in kit.flowsCon:
                if flow.upstreamSite == kit:
                    flag = False
            if flag:
                # This site is downstream and is the only downstream site left
                kaboodle.append(kit)
        return kaboodle 

    def calculateUpstreamDistances(self):
        '''
        Recalculates the upstream distances for each Site in a Network starting from each faucet 
        (furthest sites from the sink, dendrites)
        

        net [Network]: Network to perform operations on.
        faucets [List(Of Site)]: A premade list of faucets used to complete method
        
        Returns [None]
        Raises RuntimeError if there is a multiple sink situation
        '''
        faucets = self.calculateFaucets()
        
        # Written by Nicole and Marcus
        counter = 0
        queue = list(faucets)
        while len(queue) >= 1:
            counter +=1
            
            u = queue.pop(0)
            
            if counter > len(self.siteTable) * 10000:                
                raise RuntimeError("calculateUpstreamDistances() [Error]: Took too")
            cs = u.connectedSites()
            
            cntr = 0
            for con in cs:
                if con[1] == UPSTREAM_CON:
                    cntr += 1
                    if con[0].pendingUpstream == 0:
                        cntr -= 1
            u.pendingUpstream = cntr
            
            if u.pendingUpstream > 0:
                # This site is not ready for assignment
                # Re-add it to the queue at the end
                queue.append(u)
                continue
            totalUp = 0
            totalDown = 0        
            dcon = None
            if len(cs) == 1:
                # This is a true faucet            
                if cs[0][1] == DOWNSTREAM_CON:
                    dcon = cs[0][2]                
                else:
                    break # This is the sink
                # Append downstream site if not already in the queue
                if cs[0][0] not in queue:
                    queue.append(cs[0][0])
            else:            
                for entry in cs:
                    if entry[1] == DOWNSTREAM_CON:
                        if dcon is None:
                            # add to totalDown
                            totalDown += entry[2].length
                            dcon = entry[2]
                            # Append downstream site if not already in the queue
                        if entry[0] not in queue:
                            queue.append(entry[0])
                    else:                   
                        totalUp += entry[2].thisAndUpstream
                totalDown += totalUp
                if dcon is None:
                    # Reached the end
                    #raise RuntimeError("ERROR: calculateUpstreamDistances() invalid end")
                    pass
                else:
                    dcon.thisAndUpstream = totalDown 

    def find_flow(self, id_number):
        for flow in self.flowTable:
            if flow.id == id_number:
                return flow

    def calculateFaucets(self):    
        '''
        Calculate the faucets for a given network. The 'faucets' are the sources of
        the water network. (If you think of the network as a tree, these would be the outermost
        leaf nodes)

        net [Network]: Network to perform analysis on.
        
        Returns List(Of Site): List of sites at the upstream-most areas of a network (faucets).
        '''
        faucets = []
        for s in self.siteTable:
            flag = True
            for flow in s.flowsCon:
                if flow.upstreamSite != s:
                    flag = False
            if flag == True:
                faucets.append(s)
            # if len(s.flowsCon) == 1 and s.flowsCon[0].upstreamSite == s:
            #     # s is a faucet (the most upstream on a particular branch)
            #     faucets.append(s)
        return faucets

    def positionalEqualityList(self):
        '''
        Determines all sites with positional equality
        Returns [List(Of Site)]: List of sites with positional equality
        '''
        l = []
        for site in net.siteTable:
            for situ in net.siteTable:
                if site == situ:
                    continue
                elif site.hasPositionalEquality(situ):
                    l.append((site,situ))
        return l

    def setupSiteSafety(self):
        '''
        Will calculate the pending upstream number for every site in the sitetable

        net [Network]: The network to lookup sites in site-table.

        Returns [None]
        
        Notes: Do NOT call this method outside of preconfigured use. It will mess up the
        algorithm.
        '''
        for s in self.siteTable:
            s.calculatePendingUpstream()
            
    def navigateToNearestConfluence(self,site):
        '''
        Will navigate to the nearest confluence. Returns the last flow which allowed reaching the
        confluence. 

        net [Network]: Network to perform analysis on
        site [Site]: Site to start operation from.

        Returns [Site]: Nearest confluence to argument 'site'
        Raises RuntimeWarning if 'site' is not in sitetable
        '''
        if not site in self.siteTable:
            raise RuntimeWarning("WARNING navigate_nearestConfluence() failed; site not in siteTable")
        s = site
        startSite = site
        flag = True
        rtrnFlow = None
        while flag:
            cs = s.connectedSites()
            dsCons = []
            for conTup in cs:
                if conTup[1] == DOWNSTREAM_CON:
                    dsCons.append(conTup)
            if len(dsCons) != 1 or (len(cs) == 3 and  not s == startSite):
                # We are at the confluence or have reached the end.
                return rtrnFlow
            else:
                # Keep progressing
                rtrnFlow = dsCons[0][2]
                s = dsCons[0][0]
    def findSharedConfluence(self,site1,site2):
        '''
        Will navigate through the network to find the confluence
        of two sites (nodes). Note: This will not work if there are loops potentially
        '''
        s1History = []
        s2History = [] # Where these overlap is where the shared confluence is
        
        def popHistory(s,history):
            while s != None:
                history.append(s)
                d = s.getDownstream()
                u = s.getUpstream()
                if len(d) == 1:
                    # Use this downstream
                    s = d[0][0]
                else:
                    if len(u) == 1 and len(d) == 0:
                        # This is a sink, its fine  
                        pass                      
                    else:
                        # This is not fine
                        raise RuntimeError("Error: Are there loops?")

        popHistory(site1,s1History)
        popHistory(site2,s2History)

        # Compare lists to find where they overlap
        s1Set = frozenset(s1History)
        s2Set = frozenset(s2History)

        iSct = s1Set.intersection(s2Set)
        return iSct[0]
                    

    def navigateFurthestUpstream(self,site):
        '''
        Will navigate through the network to find the node at the end of a branch
        by using > operations.

        net [Network]: Network to perform analysis on.
        site [Site]: Site to start operation from.
        
        Returns [Site]: Furthest upstream site.
        '''
        sInvest = site
        flag = True
        while flag:
            cs = sInvest.connectedSites()
            flup = None        
            for con in cs:
                # If the connection is upstream it is pursuable
                if con[1] == UPSTREAM_CON:                
                    if flup is None:
                        flup = con[2]
                    else:
                        if con[2] < flup:
                            flup = con[2]
            if flup is None:
                # We have reached the upmost area on the branch
                flag = False
                break
            sInvest = flup.upstreamSite
        return sInvest
    def calcStraihler(self):
        faucets = self.calculateFaucets()
        queue = []
        for flow in self.flowTable:
            if flow.upstreamSite in faucets:
                flow.straihler = 1
                if flow.downstreamSite not in queue:
                    queue.append(flow.downstreamSite)
        
        sink = self.calculateSink()[0]

        while(queue):
            curr = queue.pop(0)
            
            if curr.id == sink.id:
                break
            down = []
            up = []
            for flow in self.flowTable:
                if flow.downstreamSite == curr:
                    down.append(flow)

                if flow.upstreamSite == curr:
                    up.append(flow)

            if len(down) == 2 and down[0].upstreamSite == down[1].upstreamSite:
                for f in down:
                    if f.straihler == -1:
                        down.remove(f)
            flag = False
            for flow in down:
                if flow.straihler == -1:
                    queue.append(curr)
                    flag = True
                    break
            
            if flag == True:
                continue
            vals = [f.straihler for f in down]
            if len(vals) > 1 and all(elem == vals[0] for elem in vals):
                for f in up:
                    f.straihler = vals[0] + 1
                    if f.downstreamSite not in queue:
                        queue.append(f.downstreamSite)
            else:
                for f in up:
                    f.straihler = max(vals)
                    if f.downstreamSite not in queue:
                        queue.append(f.downstreamSite)

    def subnetTrace(self,startSite):
        '''
        Will navigate through network from startSite and
        generate a cloned Network from the resulting recursion

        startSite [Site]: Site in Network to start from

        Returns [Network]: Deep Copy of Network based on recursive paths
        '''
        ft = [] # New flowtable
        st = [] # New sitetable        
        
        queue = []
        queue.append(startSite)
        while len(queue) > 0:
            u = queue.pop(0)
            st.append(u)
            u.assignedID = 0
            for conTup in u.connectedSites():
                if conTup[1] == UPSTREAM_CON and conTup[0].assignedID < 0:
                    # Flow is reachable and addressable. Add to traversal
                    ft.append(conTup[2])
                    queue.insert(1,conTup[0])
                elif conTup[1] == UPSTREAM_CON:
                    ft.append(conTup[2])
                    # Flow is not addressable but still exists, add it anyway
        for site in st:
            site.assignedID = -1
        ftCopy = []
        stCopy = []
        
        net = Network(ft,st)
        net.recalculateTotalLength()
        net.unitLength = int(net.totalSize / 10)
        return net

     