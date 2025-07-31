#!/usr/bin/env python
# coding: utf-8
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from utils_new import *
from tqdm import tqdm
tqdm.pandas()

config = load_config()
incoming_data_path = config['paths']['incoming_data']
processed_data_path = config['paths']['data']

def main():

    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    epsg_meters = 3395 # To convert geometries to measure distances in meters   

    ports_nodes = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_maritime_network.gpkg"),layer = 'nodes') 
    ports_edges = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_maritime_network.gpkg"),layer = 'edges')
    roads_nodes
    
    # """Remove the edges which contain nodes not found in the node list 
    # """
    # # nodes = ports_nodes["id"].values.tolist()
    # nodes = ports_nodes[(ports_nodes["infra"] == "port")]["id"].values.tolist()
    # print (len(nodes))
    # from_to_nodes = list(set(ports_edges["from_id"].values.tolist() + ports_edges["to_id"].values.tolist()))
    # extra_nodes = [n for n in from_to_nodes if n not in nodes] 
    # # new_nodes = [n for n in nodes if n not in from_to_nodes]
    # new_nodes = nodes
    # print (ports_edges)
    # ports_edges = ports_edges[~(ports_edges["from_id"].isin(nodes) | ports_edges["to_id"].isin(nodes))]
    # print (ports_edges)
   
    # df_origins = ports_nodes[
    #                         ports_nodes["infra"] == "port"
    #                         ][ports_nodes["id"].isin(new_nodes)][["id","infra","geometry"]]
    # print (df_origins)
    # df_origins.rename(columns={"id":"from_id"},inplace=True)
    # left_join = gpd.sjoin_nearest(
    #                         df_origins,
    #                         ports_nodes[ports_nodes["infra"] != "port"][["id","infra","geometry"]], 
    #                         how="left")
    # left_join.drop("index_right",axis=1,inplace=True)
    # left_join.rename(
    #                 columns={
    #                             "infra_left":"from_infra",
    #                             "infra_right":"to_infra",
    #                             "geometry":"from_geometry"
    #                         },
    #                 inplace=True)

    # left_join = pd.merge(
    #                     left_join,
    #                     ports_nodes[ports_nodes["infra"] != "port"][["id","geometry"]], 
    #                     on='id', how='left'
    #                     )
    # left_join.rename(
    #                 columns={
    #                             "id":"to_id",
    #                             "geometry":"to_geometry"
    #                         },
    #                 inplace=True)
    
    # left_join["geometry"] = left_join.progress_apply(lambda x: LineString([x.from_geometry, x.to_geometry]),axis=1)
    # left_join.drop(["from_geometry","to_geometry"],axis=1,inplace=True)

    # left_join = gpd.GeoDataFrame(left_join,geometry="geometry",crs=f"EPSG:{epsg_meters}")
    # left_join = left_join.to_crs(epsg=4326)
    # print(left_join)

    # right_join = left_join.copy()
    # right_join.columns = ["to_id","to_infra","from_id","from_infra","geometry"]
    # print (left_join.crs)
    # print (ports_edges.crs)
    # ports_edges = pd.concat([ports_edges,left_join,right_join],axis=0,ignore_index=True)
    # ports_edges.drop("id",axis=1,inplace=True)
    
    # ports_edges = gpd.GeoDataFrame(ports_edges,geometry="geometry",crs=f"EPSG:4326")

    # ports_edges["id"] = ports_edges.index.values.tolist()
    # ports_edges["id"] = ports_edges.progress_apply(lambda x:f"maritimeroute_{x.id}",axis=1)
    # ports_edges["length_degree"] = ports_edges.geometry.length
    # ports_edges = ports_edges.to_crs('+proj=cea')
    # ports_edges["length"] = ports_edges.geometry.length
    # ports_edges["distance"] = 0.001*ports_edges.geometry.length
    # ports_edges = ports_edges.to_crs(epsg=4326)
    # ports_edges["distance_km"] = ports_edges.progress_apply(lambda x:modify_distance(x),axis=1)


    # print(ports_edges.columns)
    # print (ports_edges.head())

    # ports_edges.to_file(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network_last.gpkg"),
    #                     layer="edges",driver="GPKG")
    # ports_nodes.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network_last.gpkg"),
    #                     layer="nodes",driver="GPKG")
    # print("Africa maritime network created successfully.")    
    
    # multi_df = gpd.read_file(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_multimodal.gpkg"
    #                             ), 
    #                         layer="edges"
    #                         )
    # air_nodes_df = gpd.read_file(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_airport_network.gpkg"
    #                             ), 
    #                         layer="nodes"
    #                         )
    # air_edges_df = gpd.read_file(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_airport_network.gpkg"
    #                             ), 
    #                         layer="edges"
    #                         )
    # connected_airports = list(set(air_edges_df["from_id"].values.tolist() + air_edges_df["to_id"].values.tolist()))
    # afr_connected_airports = air_nodes_df[air_nodes_df["id"].isin(connected_airports)]
    # print (afr_connected_airports)

if __name__ == '__main__':
    main()