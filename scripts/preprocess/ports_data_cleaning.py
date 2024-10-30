#!/usr/bin/env python
# coding: utf-8
# (1) Merge three datasets; (2)Add ISO3 (4) extract non_intersected
import sys
import os
import re
import pandas as pd
import geopandas as gpd
import igraph as ig
from shapely.geometry import Point
from math import radians, cos, sin, asin, sqrt
from haversine import haversine
from utils import *
from tqdm import tqdm
tqdm.pandas()

def haversine_distance(point1, point2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lon1, lat1 = point1.bounds[0], point1.bounds[1]
    lon2, lat2 = point2.bounds[0], point2.bounds[1]

    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers
    # print('Distance from beginning to end of route in km: ',round((c * r), 2),'\n')
    return c * r

def modify_distance(x):
    if x["length"] < 355 and x["distance"] < 40075:
        return x["distance"]
    else:
        start = x.geometry.coords[0]
        end = x.geometry.coords[-1]
        return haversine(
                    (
                        round(start[1],2),
                        round(start[0],2)
                    ),
                    (
                        round(end[1],2),
                        round(end[0],2)
                    )
                )

def match_ports(df1,df2,df1_id_column,df2_id_column,cutoff_distance):
    # Find the nearest ports that match and the ones which do not 
    matches = ckdnearest(df1,
                        df2)
    matches = matches.sort_values(by="dist",ascending=True)
    matches["matches"] = np.where(matches["dist"] <= cutoff_distance,"Y","N")

    selection = matches[matches["dist"] <= cutoff_distance]
    selection = selection.drop_duplicates(subset=df2_id_column,keep='first')
    matched_ids = list(set(selection[df1_id_column].values.tolist()))
    return matches, df1[~(df1[df1_id_column].isin(matched_ids))]

def add_iso_code(df,df_id_column,incoming_data_path):
    # Insert countries' ISO CODE
    africa_boundaries = gpd.read_file(os.path.join(
                            incoming_data_path,
                            "Africa_GIS Supporting Data",
                            "a. Africa_GIS Shapefiles",
                            "AFR_Political_ADM0_Boundaries.shp",
                            "AFR_Political_ADM0_Boundaries.shp"))
    africa_boundaries.rename(columns={"DsgAttr03":"iso3"},inplace=True)
    # Spatial join
    m = gpd.sjoin(df, 
                    africa_boundaries[['geometry', 'iso3']], 
                    how="left", predicate='within').reset_index()
    m = m[~m["iso3"].isna()]        
    un = df[~df[df_id_column].isin(m[df_id_column].values.tolist())]
    un = gpd.sjoin_nearest(un,
                            africa_boundaries[['geometry', 'iso3']], 
                            how="left").reset_index()
    m = pd.concat([m,un],axis=0,ignore_index=True)
    return m

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    # epsg_meters = 3395 # To convert geometries to measure distances in meters
    # cutoff_distance = 6600 # We assume ports within 6.6km are the same
    # # 1. Read USGS data, Global ports dataset, African development corridor datasets
    # df_global_ports = gpd.read_file(os.path.join(incoming_data_path,
    #                                 "Global port supply-chains",
    #                                 "Network",
    #                                 "nodes_maritime.gpkg")) 
    # df_ports_shp = gpd.read_file(os.path.join(
    #                             incoming_data_path,
    #                             "Africa_GIS Supporting Data",
    #                             "a. Africa_GIS Shapefiles",
    #                             "AFR_Infra_Transport_Ports.shp",
    #                             "AFR_Infra_Transport_Ports.shp")) 
    # # This contains geometry is wrong, which we will have to convert to Point from Latitude and Longitude values
    # df_ports_shp["geom"] = gpd.points_from_xy(
    #                         df_ports_shp["Longitude"],df_ports_shp["Latitude"])
    # df_ports_shp.drop("geometry",axis=1,inplace=True)
    # df_ports_shp.rename(columns={"geom":"geometry"},inplace=True)
    # df_ports_shp = gpd.GeoDataFrame(df_ports_shp,geometry="geometry",crs="EPSG:4326")

    # df_corridor = gpd.read_file(os.path.join(
    #                             incoming_data_path,
    #                             "africa_corridor_developments",
    #                             "AfricanDevelopmentCorridorDatabase2022.gpkg" 
    #                             ),layer='point')

    # # Filter corridor data for "Port" Infrastructure development type
    # # Also remove the Inland port, which is far away from the Maritime ports
    # # Also remove the Conarky Port which is not properly geolocated in the data
    # df_corridor = df_corridor[(
    #                 df_corridor["Infrastructure_development_type"] == "Port"
    #                 ) & ~(df_corridor["Project_code"].isin(["LTT0002","KMI0001","DLC0002"]))]
    
    # mapping, new_ports_corridor = match_ports(
    #                         df_corridor.to_crs(epsg=epsg_meters),
    #                         df_global_ports.to_crs(epsg=epsg_meters),
    #                         "Project_code","id",cutoff_distance)
    # # Save mapping results for further cleaning
    # # mapping.to_csv("corridor_port_matches.csv",index=False)
    
    # # Find the nearest port from Corridor to USGG ports
    # mapping, new_ports_corridor = match_ports(
    #                         new_ports_corridor.to_crs(epsg=epsg_meters),
    #                         df_ports_shp.to_crs(epsg=epsg_meters),
    #                         "Project_code","FeatureUID",cutoff_distance)
    # # Save mapping results for further cleaning
    # # mapping.to_csv("corridor_usgs_matches.csv",index=False)
    
    # # Find the nearest port from USGS ports to the Global ports
    # mapping, new_ports_usgs = match_ports(
    #                         df_ports_shp.to_crs(epsg=epsg_meters),
    #                         df_global_ports.to_crs(epsg=epsg_meters),
    #                         "FeatureUID","id",cutoff_distance)
    # # mapping = mapping.drop_duplicates(subset="FeatureUID",keep="first")
    # # Save mapping results for further cleaning
    # # mapping.to_csv("usgs_port_matches.csv",index=False)
    # new_ports_usgs = new_ports_usgs.drop_duplicates(subset="FeatureUID",keep='first')
    
    # new_ports_corridor = new_ports_corridor.to_crs(epsg=4326)
    # new_ports_usgs = new_ports_usgs.to_crs(epsg=4326)
    
    # new_ports_corridor = add_iso_code(new_ports_corridor,"Project_code",incoming_data_path)
    # new_ports_usgs = add_iso_code(new_ports_usgs,"FeatureUID",incoming_data_path)
    # new_ports_corridor["name"] = new_ports_corridor.progress_apply(
    #                                 lambda x:f"{x['Project_name']}_{x['Country']}",
    #                                 axis=1)
    # new_ports_usgs["name"] = new_ports_usgs.progress_apply(
    #                                 lambda x:f"{x['FeatureNam']}_{x['Country']}",
    #                                 axis=1)

    # new_ports = pd.concat([new_ports_corridor,
    #                         new_ports_usgs],axis=0,ignore_index=True)
    # # Get the maximum number of the port node ID because we want to create new nodes in the sequence
    # prt = df_global_ports[df_global_ports["infra"] == "port"]
    # max_port_id = max([int(re.findall(r'\d+',v)[0]) for v in prt["id"].values.tolist()])
    # new_ports["id"] = list(max_port_id + 1 + new_ports.index.values)
    # new_ports["id"] = new_ports.progress_apply(lambda x: f"port{x.id}",axis=1)
    # new_ports["Continent_Code"] = "AF"
    # new_ports["infra"] = "port"
    
    # # Save mapping results for further cleaning
    # # new_ports["matches"] = "Y"
    # # new_ports.to_csv("new_port_matches.csv",index=False)
    
    # new_ports = gpd.GeoDataFrame(new_ports,geometry="geometry",crs="EPSG:4326")
    # # Get the maximum number of the port edges ID because we want to create new edges in the sequence
    # port_edges = gpd.read_file(os.path.join(incoming_data_path,
    #                             "ports",
    #                             "edges_maritime_corrected.gpkg"))
    # # Find nearest node in pn to every point in non_intersectedcd
    # pn = df_global_ports[df_global_ports["infra"] != "port"]
    # pn.rename(columns={"id":"to_id"},inplace=True)
    # nearest_nodes = ckdnearest(new_ports[['id','geometry']],pn[['to_id','geometry']])
    # from_node_id = 'id' # ID column in non_intersected
    # to_node_id = 'to_id' # ID column in non_intersected
    # # Create lines between nearest nodes
    # nearest_nodes["geometry"] = nearest_nodes.progress_apply(
    #                             lambda x:add_lines(
    #                                 x,new_ports,pn,from_node_id,to_node_id
    #                                 ),
    #                             axis=1)
    # nearest_nodes.rename(columns={from_node_id:"from_id"},inplace=True)
    # nearest_nodes["from_infra"] = "port"
    # nearest_nodes["to_infra"] = "maritime"
    # nearest_nodes = gpd.GeoDataFrame(nearest_nodes,geometry="geometry",crs="EPSG:4326")
    # nearest_nodes.drop("dist",axis=1,inplace=True)

    # port_edges = gpd.GeoDataFrame(
    #                 pd.concat([port_edges,nearest_nodes],
    #                 axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")

    # # Also make the new nodes layer
    # port_nodes = gpd.GeoDataFrame(
    #                 pd.concat([df_global_ports, 
    #                 new_ports[["id","infra","name","iso3","Continent_Code", "geometry"]]], 
    #                 axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")
    # # Remove maritime nodes and add Suez Canal
    # remove_nodes = ["maritime2926","maritime2927"]
    # port_nodes = port_nodes[~port_nodes["id"].isin(remove_nodes)]
    # port_edges = port_edges[~(port_edges["from_id"].isin(remove_nodes) | port_edges["to_id"].isin(remove_nodes))]
    # # Add the suez canal
    # suez_canal_nodes = gpd.read_file(os.path.join(
    #                                     incoming_data_path,
    #                                     "egypt-latest-free.shp",
    #                                     "suez_canal_network.gpkg"),layer="nodes")
    # suez_canal_edges = gpd.read_file(os.path.join(
    #                                     incoming_data_path,
    #                                     "egypt-latest-free.shp",
    #                                     "suez_canal_network.gpkg"),layer="edges")
    # nodes = suez_canal_nodes.copy()
    # nodes.rename(columns={"id":"to_id","infra":"to_infra"},inplace=True)
    # edges = [port_edges,
    #         suez_canal_edges[["from_id","to_id","from_infra","to_infra","geometry"]]]

    # # Join some pre-selected ports/maritime points to the Suez canal points
    # # m = ckdnearest(port_nodes[['id','infra','geometry']].to_crs(epsg=epsg_meters),
    # #                 suez_canal_nodes[['id','geometry']].to_crs(epsg=epsg_meters))
    # # m = m.sort_values(by="dist",ascending=True)

    # connect_pairs = [("port1440","maritime16265","port","maritime"),
    #                     ("port192","maritime16247","port","maritime"),
    #                     ("port71","maritime16270","port","maritime"),
    #                     ("port321","maritime16270","port","maritime"),
    #                     ("maritime2917","maritime16270","maritime","maritime"),
    #                     ("maritime1606","maritime16247","maritime","maritime"),
    #                     ("maritime1606","maritime16265","maritime","maritime")]
    # # Create lines between nearest nodes
    # suez_lines = pd.DataFrame(connect_pairs,columns=["id","to_id","from_infra","to_infra"])
    # suez_lines["geometry"] = suez_lines.progress_apply(
    #                             lambda x:add_lines(
    #                                 x,port_nodes,nodes,from_node_id,to_node_id
    #                                 ),
    #                             axis=1)
    # suez_lines.rename(columns={from_node_id:"from_id"},inplace=True)
    # edges.append(suez_lines[["from_id","to_id","from_infra","to_infra","geometry"]])

    # port_edges = gpd.GeoDataFrame(
    #                 pd.concat(edges,
    #                 axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")

    # port_edges["id"] = port_edges.index.values.tolist()
    # port_edges["id"] = port_edges.progress_apply(lambda x:f"maritimeroute_{x.id}",axis=1)
    # port_edges["length_degree"] = port_edges.geometry.length
    # port_edges = port_edges.to_crs('+proj=cea')
    # port_edges["distance"] = 0.001*port_edges.geometry.length
    # port_edges = port_edges.to_crs(epsg=4326)
    # port_edges["distance_km"] = port_edges.progress_apply(lambda x:modify_distance(x),axis=1)
    # port_edges.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_maritime_network.gpkg"),layer="edges",driver="GPKG")

    # # Also make the new nodes layer
    # port_nodes = gpd.GeoDataFrame(
    #                 pd.concat([port_nodes,suez_canal_nodes[["id","infra","geometry"]]],
    #                 axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")
    # port_nodes.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_maritime_network.gpkg"),layer="nodes",driver="GPKG")

    # Get the ports for Africa
    # port_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_maritime_network.gpkg"),layer="edges")
    # port_nodes = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_maritime_network.gpkg"),layer="nodes")
    # # global_edges = port_edges[["from_id","to_id","id","from_infra","to_infra","geometry"]].to_crs(epsg_meters)
    # # global_edges["distance"] = global_edges.geometry.length
    # global_edges = port_edges[["from_id","to_id","id","distance"]]
    # africa_ports = port_nodes[port_nodes["Continent_Code"] == "AF"]
    # G = ig.Graph.TupleList(global_edges.itertuples(index=False), edge_attrs=list(global_edges.columns)[2:])
    # # print (G)

    # all_edges = []
    # africa_nodes = port_nodes[port_nodes["Continent_Code"] == "AF"]["id"].values.tolist()
    # for o in range(len(africa_nodes)-1):
    #     origin = africa_nodes[o]
    #     destinations = africa_nodes[o+1:]
    #     e,_ = network_od_path_estimations(G,origin,destinations,"distance","id")
    #     all_edges += e

    # all_edges = list(set([item for sublist in all_edges for item in sublist]))
    # all_edges += port_edges[port_edges.index > 9390]["id"].values.tolist()
    # all_edges = list(set(all_edges))
    # # africa_edges = port_edges[port_edges["id"].isin(all_edges)]
    # africa_edges = port_edges[port_edges["id"].isin(all_edges)][["from_id","to_id"]]
    # dup_df = africa_edges.copy()
    # dup_df[["from_id","to_id"]] = dup_df[["to_id","from_id"]]
    # africa_edges = pd.concat([africa_edges,dup_df],axis=0,ignore_index=True)
    # africa_edges = africa_edges.drop_duplicates(subset=["from_id","to_id"],keep="first")
    # africa_edges = gpd.GeoDataFrame(
    #                     pd.merge(
    #                             africa_edges,port_edges,
    #                             how="left",on=["from_id","to_id"]
    #                             ),
    #                     geometry="geometry",crs="EPSG:4326")
    
    # all_nodes = list(set(africa_edges["from_id"].values.tolist() + africa_edges["to_id"].values.tolist()))
    # africa_nodes = port_nodes[port_nodes["id"].isin(all_nodes)] 

    # africa_nodes.to_file(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network.gpkg"),
    #                     layer="nodes",driver="GPKG")
    # africa_edges.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network.gpkg"),
    #                     layer="edges",driver="GPKG")


    # port_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_maritime_network.gpkg"),layer="edges")
    # port_edges["from_infra"] = port_edges.progress_apply(
    #                             lambda x:re.sub('[^a-zA-Z]+', '',x["from_id"]),
    #                             axis=1)
    # port_edges["to_infra"] = port_edges.progress_apply(
    #                             lambda x:re.sub('[^a-zA-Z]+', '',x["to_id"]),
    #                             axis=1)
    # port_edges["id"] = port_edges.index.values.tolist()
    # port_edges["id"] = port_edges.progress_apply(lambda x:f"maritimeroute_{x.id}",axis=1)
    # port_edges['duplicates'] = pd.DataFrame(
    #                                 np.sort(port_edges[['from_id','to_id']])
    #                                 ).duplicated(keep=False).astype(int)
    # u_df = port_edges[port_edges['duplicates'] == 0]
    # u_df[["to_id","from_id"]] = u_df[["from_id","to_id"]]
    # port_edges = gpd.GeoDataFrame(
    #                 pd.concat([port_edges,u_df],axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")
    # port_edges.drop("duplicates",axis=1,inplace=True)
    # # port_edges["length"] = port_edges.geometry.length
    # # port_edges = port_edges.to_crs('+proj=cea')
    # # port_edges["distance"] = 0.001*port_edges.geometry.length
    # # port_edges = port_edges.to_crs(epsg=4326)
    # # port_edges["distance"] = port_edges.progress_apply(lambda x:modify_distance(x),axis=1)
    # port_edges.to_csv("test2.csv")
    # port_edges.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_maritime_network.gpkg"),layer="edges",driver="GPKG")



    port_edges = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_maritime_network.gpkg"),
                        layer="edges")
    port_edges["from_infra"] = port_edges.progress_apply(
                                lambda x:re.sub('[^a-zA-Z]+', '',x["from_id"]),
                                axis=1)
    port_edges["to_infra"] = port_edges.progress_apply(
                                lambda x:re.sub('[^a-zA-Z]+', '',x["to_id"]),
                                axis=1)
    # port_edges['duplicates'] = pd.DataFrame(
    #                                 np.sort(port_edges[['from_id','to_id']])
    #                                 ).duplicated(keep=False).astype(int)
    # u_df = port_edges[port_edges['duplicates'] == 0]
    # u_df[["to_id","from_id"]] = u_df[["from_id","to_id"]]
    # port_edges = gpd.GeoDataFrame(
    #                 pd.concat([port_edges,u_df],axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")
    # port_edges.drop("duplicates",axis=1,inplace=True)
    # # port_edges["length"] = port_edges.geometry.length
    # # port_edges = port_edges.to_crs('+proj=cea')
    # # port_edges["distance"] = 0.001*port_edges.geometry.length
    # # port_edges = port_edges.to_crs(epsg=4326)
    # # print (port_edges)
    port_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_maritime_network.gpkg"),
                        layer="edges",driver="GPKG")






if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)