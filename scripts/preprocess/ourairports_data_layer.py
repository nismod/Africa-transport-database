import sys
import os
import re
import pandas as pd
import geopandas as gpd
import igraph as ig
from shapely.geometry import Point
from math import radians, cos, sin, asin, sqrt
from haversine import haversine
from utils_new import *
from tqdm import tqdm
import country_converter as coco

tqdm.pandas()

    

def main(config):
    
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    cutoff_distance = 6600 # We assume airports within 6.6km are the same

    df_airports_ourairports = gpd.read_file(os.path.join(incoming_data_path,
                                    "airports",
                                    "africa_airports_ourairports.gpkg"))
    
    df_airports_nodes = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_airport_network.gpkg"), layer="nodes")
    df_airports_edges = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_airport_network.gpkg"), layer="edges")
    
    df_airports_ourairports= df_airports_ourairports.to_crs(epsg=4326)
    
    df_airports_ourairports_filtered = df_airports_ourairports[df_airports_ourairports['iata_code'].isin(df_airports_nodes['Origin'])]
    df_airports_nodes.rename(columns={"Origin":"iata_code"}, inplace=True)

    df_airports_ourairports_filtered= df_airports_ourairports_filtered.to_crs(epsg=4326)
    
    df_airports_nodes= df_airports_nodes.to_crs(epsg=4326)
    df_airports_edges= df_airports_edges.to_crs(epsg=4326)
    
    print(df_airports_nodes)
    print(df_airports_ourairports_filtered)

    df_airports_ourairports_filtered.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_ourairport_rev.gpkg"),
                        layer="nodes",driver="GPKG")
    
    df_airports_nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network_rev.gpkg"),
                        layer="nodes",driver="GPKG")
    df_airports_edges.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network_rev.gpkg"),
                        layer="edges",driver="GPKG")
    
    



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)