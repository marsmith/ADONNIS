import platform
#import plotly
# from  plotly import graph_objects as go
# from plotly.offline import download_plotlyjs, plot
#import networkx as nx
from Precompiler import *
import webbrowser
import test

def visualize(net, x = -1.0, y = -1.0, id = -1):
    create_files(net)
    create_visuals("Visualize-Net", x, y, id)

def create_files(net):
    fileobject = open("Sites.txt", "w")
    for site in net.siteTable:
        
        strr = "{0}, {1:f}, {2:f}, {3}, {4}, {5}\n".format(site.id, site.latLong.srcLat, site.latLong.srcLong, str(site.assignedID), str(site.downwardRefID), str(site.isReal))
        fileobject.write(strr)
    fileobject.close()
    fileobject = open("Flows.txt", "w")
    for flow in net.flowTable:
        strr = "{0}, {1}, {2:f}, {3:f}, {4}\n".format(flow.upstreamSite.id, flow.downstreamSite.id, flow.length, flow.thisAndUpstream, flow.straihler)
        fileobject.write(strr)
    fileobject.close()

def make_annotations(Xn, Yn, labels, font_size=14, font_color='rgb(10,10,10)'):
    L=len(Xn)
    if len(labels)!=L:
        raise ValueError('The lists pos and text must have the same len')
    annotations = []
    for k in range(L):
        annotations.append(dict(text=labels[k], 
                                x=Xn[k]+0.0001, 
                                y=Yn[k]+0.0001,#this additional value is chosen by trial and error
                                xref='x1', yref='y1',
                                font=dict(color= font_color, size=font_size),
                                showarrow=False)
                          )
    return annotations  

def create_visuals(test_name, ux, uy, id):
    f = open("Sites.txt", 'r')
    temp_sites = f.read()
    temp_sites = temp_sites.split("\n")
    temp_sites.pop()
    sites = {}
    for site in temp_sites:
        site = site.split(", ")
        site[0] = int(site[0])
        site[1] = float(site[1])
        site[2] = float(site[2])
        site[3] = str(site[3])
        site[4] = str(site[4])
        site[5] = str(site[5])
        sites[site[0]] = site


    f = open("Flows.txt", 'r')
    temp_flows = f.read()
    temp_flows = temp_flows.split("\n")
    temp_flows.pop()
    flows = []
    for flow in temp_flows:
        flow = flow.split(", ")
        flow[0] = int(flow[0])
        flow[1] = int(flow[1])
        flow[2] = float(flow[2])
        flow[3] = float(flow[3])
        flow[4] = int(flow[4])
        flows.append(flow)


    if ux != -1 and uy != -1 and id != -1:
        ux = [ux]
        uy = [uy]
        user_click_trace = go.Scatter(
        x=ux, y=uy,
        mode='markers',
        text = [id],
        hoverinfo='text',
        marker=dict(
            color = 'green',
            size=10,
            line_width=2))

    real_sites = []
    for site in sites.keys():
        if sites[site][5] == "True":
            real_sites.append([sites[site][1], sites[site][2]])
    Xr = [real_sites[k][0] for k in range(len(real_sites))]
    Yr = [real_sites[k][1] for k in range(len(real_sites))]
    realSites_trace = go.Scatter(
        x=Xr, y=Yr,
        mode='markers',
        hoverinfo= 'none',
        marker=dict(
            color = 'red',
            size=10,
            line_width=2))



    midpoints = []
    for flow in flows:
        x0 = sites[flow[0]][1]
        y0 = sites[flow[0]][2]
        x1 = sites[flow[1]][1]
        y1 = sites[flow[1]][2]
        temp_length = flow[2]
        new_x = (x0 + x1) / 2
        new_y = (y0 + y1) / 2
        midpoints.append([temp_length, new_x, new_y])
    Xm = [midpoints[k][1] for k in range(len(midpoints))]
    Ym = [midpoints[k][2] for k in range(len(midpoints))]
    flow_lengths = ["This: " + str(flows[k][2]) + "\t Upstream: " + str(flows[k][3]) + "\t straihler: " + str(flows[k][4])for k in range(len(flows))]
    midpoint_trace = go.Scatter(
        x=Xm, y=Ym,
        mode='markers',
        text = flow_lengths,
        hoverinfo='text',
        marker=go.Marker(
            opacity=0
        )
    )


    G=nx.Graph()
    my_nodes = range(len(sites))
    my_edges = [(flows[k][0],flows[k][1]) for k in range(len(flows))]
    G.add_nodes_from(my_nodes)
    G.add_edges_from(my_edges)

    sL = list(sites.values())

    Xn = []
    Yn = []
    for k in range(len(sL)):
        Xn.append(sL[k][1])
        Yn.append(sL[k][2])

    labels = [sL[k][0] for k in range(len(sL))]
    node_labels = ["ID: " + str(sL[k][0]) + "\nAssigned ID: " + str(sL[k][3]) + "\nDownward Ref ID:" + sL[k][4] for k in range(len(sL))]

    node_trace = go.Scatter(
        x=Xn, y=Yn,
        mode='markers',
        text = node_labels,
        hoverinfo = 'text',
        marker=dict(
            color = 'white',
            size=7,
            line_width=2))

    Xe = []
    Ye = []
    
    Xdict = dict()
    Ydict = dict()
    for k in range(len(sL)):
        Xdict[sL[k][0]] = sL[k][1]
        Ydict[sL[k][0]] = sL[k][2]
    
    for e in G.edges():
        x0 = Xdict[e[0]]
        y0 = Ydict[e[0]]
        x1 = Xdict[e[1]]
        y1 = Ydict[e[1]]
        Xe.append(x0)
        Xe.append(x1)
        Xe.append(None)
        Ye.append(y0)
        Ye.append(y1)
        Ye.append(None)

    edge_trace = go.Scatter(
        x=Xe, y=Ye,
        line=dict(width=0.5, color='#888'),
        mode='lines')



    axis=dict(showline=False, # hide axis line, grid, ticklabels and  title
            zeroline=False,
            showgrid=False,
            showticklabels=False,
            title='' 
            )


    layout=dict(title= test_name,  
                font= dict(family='Balto'),
                width=1500,
                height=1000,
                autosize=False,
                showlegend=False,
                xaxis=axis,
                yaxis=axis,
        hovermode='closest',
        plot_bgcolor='#bad7ff', #set background color            
        )

    if ux!= -1 and uy != -1 and id != -1:
        fig = dict(data=[user_click_trace,node_trace, edge_trace, midpoint_trace, realSites_trace], layout=layout)
    else:
        fig = dict(data=[node_trace, edge_trace, midpoint_trace, realSites_trace], layout=layout)
    fig['layout'].update(annotations=make_annotations(Xn, Yn, labels))
    plot(fig)


def createWebViewer(filepath, netTup, real_sites):
    newJSON = importJSON(filepath)
    for site in netTup[0].siteTable:
        new_feat = dict()
        new_feat["type"] = "Feature"
        new_feat["id"] = site.id

        propDict = dict()
        propDict["id"] = str(site.id)
        propDict["assigned_id"] = str(site.assignedID)

        geoDict = dict()
        geoDict["type"] = "Point"
        coords = []
        coords.append(site.latLong.srcLat)
        coords.append(site.latLong.srcLong)
        geoDict["coordinates"] = coords

        new_feat["properties"] = propDict
        new_feat["geometry"] = geoDict
        newJSON["features"].append(new_feat)
    
    realJSON = importJSON(real_sites)
    fList = realJSON["features"]

    for geomObj in fList:
        new_feat = dict()
        new_feat["type"] = "Feature"

        propDict = dict()
        propDict["site_no"] = geomObj['properties']['site_no']
        propDict["real_site"] = "True"

        geoDict = dict()
        geoDict["type"] = "Point"
        geoDict["coordinates"] = geomObj["geometry"]["coordinates"]

        new_feat["properties"] = propDict
        new_feat["geometry"] = geoDict
        newJSON["features"].append(new_feat)


    with open("jsonViewer/data.json", 'w') as fp:
        json.dump(newJSON, fp)

    webbrowser.open('http://localhost:3000/jsonViewer/index.html')

    