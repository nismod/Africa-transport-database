#!/usr/bin/env python
# coding: utf-8
import sys
import os
import re
import json
import pandas as pd
import igraph as ig
import geopandas as gpd
from utils_new import *
from tqdm import tqdm
tqdm.pandas()



def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
   
    # Read the road edges data for Africa
    road_id_column = "id"
    node_id_column = "id"
    road_type_column = "tag_highway"
    main_road_types = ["trunk","motorway","primary","secondary"]
    
    Lobito_edges = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_PROVA_Lobito_corridor.geoparquet"))
    Lobito_nodes = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_PROVA_Lobito_corridor.geoparquet"))

    TA_edges = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_PROVA_TA_corridor.geoparquet"))
    TA_nodes = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_PROVA_TA_corridor.geoparquet"))

    TSH_edges = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_PROVA_TSH_corridor.geoparquet"))
    TSH_nodes = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_PROVA_TSH_corridor.geoparquet"))

    NS_edges = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_PROVA_NS_corridor.geoparquet"))
    NS_nodes = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_PROVA_NS_corridor.geoparquet"))

    MDG_edges = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_PROVA_MDG.geoparquet"))
    
    MDG_nodes = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_PROVA_MDG.geoparquet"))

    road_edges = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_withcorridors.geoparquet"))
    
    road_nodes = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_withcorridors.geoparquet"))
    
    
    MDG_edges = MDG_edges[MDG_edges["corridor_name"] == "Madagascar – Port Beira Corridor" ]
    #MDG_nodes = MDG_nodes[MDG_nodes["corridor_name"] == "Madagascar – Port Beira Corridor" ]
    
    NS_edges = NS_edges[NS_edges["corridor_name"] == "North-South Corridor (North section)" ]
   # NS_nodes = NS_nodes[NS_nodes["corridor_name"] == "North-South Corridor (North section)" ]

    Lobito_edges = Lobito_edges[Lobito_edges["corridor_name"] == "Lobito Corridor" ]
    #Lobito_nodes = Lobito_nodes[Lobito_nodes["corridor_name"] == "Lobito Corridor" ]

    TA_edges = TA_edges[TA_edges["corridor_name"] == "Tunisia – Algeria" ]
    #TA_nodes = TA_nodes[TA_nodes["corridor_name"] == "Tunisia – Algeria" ]

    TSH_edges = TSH_edges[TSH_edges["corridor_name"] == "Central Corridor of the TSH" ]
    #TSH_nodes = TSH_nodes[TSH_nodes["corridor_name"] == "Central Corridor of the TSH" ]

    # print(road_edges) 
    print(MDG_edges) 

    road_edges = road_edges.to_crs(epsg=epsg_meters)
    MDG_edges = MDG_edges.to_crs(epsg=epsg_meters)
    NS_edges = NS_edges.to_crs(epsg=epsg_meters)
    Lobito_edges = Lobito_edges.to_crs(epsg=epsg_meters)
    TA_edges = TA_edges.to_crs(epsg=epsg_meters)
    TSH_edges = TSH_edges.to_crs(epsg=epsg_meters)
    


    
    road_edges = pd.concat([road_edges,MDG_edges, NS_edges,Lobito_edges, TA_edges,TSH_edges])
    print(road_edges) 
    
    connected_nodes = list(set(road_edges.from_id.values.tolist() + road_edges.to_id.values.tolist()))
    nearest_nodes = road_nodes[road_nodes[node_id_column].isin(connected_nodes)]
    nearest_nodes.rename(columns={node_id_column:"id"},inplace=True)
    nearest_nodes = nearest_nodes.to_crs(epsg=4326)

    # """Find the network components
    # """
    edges = road_edges[[
            'from_id','to_id','id','osm_way_id','from_iso_a3','to_iso_a3',
            'tag_highway', 'tag_surface','tag_bridge','tag_maxspeed','tag_lanes',
            'bridge','paved','material','lanes','length_m','asset_type','corridor_name','geometry']]
    edges, nearest_nodes = components(edges,nearest_nodes,node_id_column="id")

    edges["border_road"] = np.where(edges["from_iso_a3"] == edges["to_iso_a3"],0,1)

    nearest_nodes = gpd.GeoDataFrame(nearest_nodes,
                    geometry="geometry",
                    crs="EPSG:4326")

    edges = gpd.GeoDataFrame(edges,
                    geometry="geometry",
                    crs="EPSG:3395")
    edges = edges.to_crs(epsg=4326)

    nearest_nodes.to_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_FINAL.geoparquet"))
    edges.to_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_FINAL.geoparquet"))
    nearest_nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_network.gpkg"),
                            layer="nodes",driver="GPKG")
    edges.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_network.gpkg"),
                            layer="edges",driver="GPKG")
   
    
    # # Write  the file back to the original if you are feeling confident!
    # # Otherwise rename
    # # roads_with_corridors.to_csv(
    # #                         os.path.join(
    # #                                 processed_data_path,
    # #                                 "infrastructure",
    # #                                 "roads_corridors_PROVA.csv"
    # #                                 )
    # #                     )
    # # road_edges.to_parquet(
    # #                         os.path.join(
    # #                                 processed_data_path,
    # #                                 "infrastructure",
    # #                                 "africa_roads_edges_PROVA.geoparquet"
    # #                                 )
    # #                     )
   






if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)