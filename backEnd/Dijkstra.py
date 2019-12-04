import sys

def netwideDistanceFromSink(net,sinkSite):
    length = net.siteTable[-1].id + 1
    dist = [sys.maxsize] * length
    dist[sinkSite.id] = 0
    pathSet = [False] * length
    for n in range(length):
        #pick node with minimum distance that hasn't been processed
        u = minDistance(dist, pathSet, length)
        pathSet[u] = True
        for v in range(length):
            temp_dist = 0
            for flow in net.flowTable:
                if int(flow.upstreamSite.id) == v and int(flow.downstreamSite.id) == u:
                     temp_dist = flow.length
                
            if temp_dist > 0 and pathSet[v] == False and \
                dist[v] > dist[u] + temp_dist:
                dist[v] = dist[u] + temp_dist
                print(str(v) + " dist:  " + str(dist[v]))
    return dist

def minDistance(dist, pathSet, length):
    min = sys.maxsize
    min_index = -1
    for v in range(length):
        if dist[v] < min and pathSet[v] == False:
            min = dist[v]
            min_index = v
    return min_index
