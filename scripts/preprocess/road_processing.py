#!/usr/bin/env python
# coding: utf-8
import sys
import os
import re
import json
import pandas as pd
import igraph as ig
import geopandas as gpd
from utils import *
from tqdm import tqdm
tqdm.pandas()



def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    # nodes = gpd.read_file(os.path.join(
    #                         incoming_data_path,
    #                         "africa_roads",
    #                         "africa_main_roads.gpkg"),
    #                     layer="nodes")
    # edges = gpd.read_file(os.path.join(
    #                         incoming_data_path,
    #                         "africa_roads",
    #                         "africa_main_roads.gpkg"),
    #                     layer="edges")
    # nodes.to_parquet(os.path.join(
    #                         incoming_data_path,
    #                         "africa_roads",
    #                         "africa_main_roads_nodes.geoparquet"))
    # edges.to_parquet(os.path.join(
    #                         incoming_data_path,
    #                         "africa_roads",
    #                         "africa_main_roads_edges.geoparquet"))

    nodes = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes.geoparquet"))
    edges = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges.geoparquet"))
    print (nodes)
    print (edges)

    nodes = nodes[nodes["iso_a3"] == "ZMB"]
    edges = edges[(edges["from_iso_a3"] == "ZMB") | (edges["to_iso_a3"] == "ZMB")]
    
    print (nodes)
    print (edges)

    nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "zambia_roads.gpkg"),layer="nodes",driver="GPKG")
    edges.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "zambia_roads.gpkg"),layer="edges",driver="GPKG")

    nodes = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_railways_network.gpkg"),layer="nodes")
    edges = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_railways_network.gpkg"),layer="edges")
    nodes = nodes[nodes["iso3"] == "ZMB"]
    edges = edges[(edges["from_iso_a3"] == "ZMB") | (edges["to_iso_a3"] == "ZMB")]

    nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "zambia_railways.gpkg"),layer="nodes",driver="GPKG")
    edges.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "zambia_railways.gpkg"),layer="edges",driver="GPKG")

    # edges = edges[[
    #         'from_id','to_id','id','osm_way_id','from_iso_a3','to_iso_a3',
    #         'tag_highway', 'tag_surface','tag_bridge','tag_maxspeed','tag_lanes',
    #         'bridge','paved','material','lanes','width_m','length_m','asset_type','geometry']]
    # """Find the network components
    # """
    # edges, nodes = components(edges,nodes,node_id_column="road_id")
    
    # """Assign border roads
    # """
    # edges["border_road"] = np.where(edges["from_iso_a3"] == edges["to_iso_a3"],0,1)

    # nodes.to_parquet(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_roads_nodes.geoparquet"))
    # edges.to_parquet(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_roads_edges.geoparquet"))

    # nodes.to_file(os.path.join(
    #                         incoming_data_path,
    #                         "africa_roads",
    #                         "africa_main_roads.gpkg"),
    #                     layer="nodes",driver="GPKG")
    # edges.to_file(os.path.join(
    #                         incoming_data_path,
    #                         "africa_roads",
    #                         "africa_main_roads.gpkg"),
    #                     layer="edges",driver="GPKG")

    """Add costs
    """



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)