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
    epsg_meters = 3395 # To convert geometries to measure distances in meters   
    multi_df = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_multimodal.gpkg"
                                ), 
                            layer="edges"
                            )
    air_nodes_df = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network.gpkg"
                                ), 
                            layer="nodes"
                            )
    air_edges_df = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network.gpkg"
                                ), 
                            layer="edges"
                            )
    connected_airports = list(set(air_edges_df["from_id"].values.tolist() + air_edges_df["to_id"].values.tolist()))
    afr_connected_airports = air_nodes_df[air_nodes_df["id"].isin(connected_airports)]
    print (afr_connected_airports)

if __name__ == '__main__':
    main()