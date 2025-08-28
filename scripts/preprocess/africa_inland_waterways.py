#!/usr/bin/env python
# coding: utf-8
# (1) Merge three datasets; (2)Add ISO3 (4) extraxt non_intersected
import sys
import os
import re
import json
import pandas as pd
import geopandas as gpd
from utils import *
from tqdm import tqdm
tqdm.pandas()




def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    edges = json.load(open(os.path.join(incoming_data_path,
                            "Africa_osm_rivers",
                            "OpenStreetMap_Waterways_for_Africa.geojson")))
    edges = convert_json_geopandas(edges)
    network = create_network_from_nodes_and_edges(None,edges,"iww")
    edges = gpd.GeoDataFrame(network.edges,geometry="geometry",crs="EPSG:4326")
    nodes = gpd.GeoDataFrame(network.nodes,geometry="geometry",crs="EPSG:4326")

    edges.to_parquet(
                os.path.join(
                    incoming_data_path,
                    "Africa_osm_rivers",
                    "africa_waterways_edges.geoparquet")
                )
    nodes.to_parquet(
                os.path.join(
                    incoming_data_path,
                    "Africa_osm_rivers",
                    "africa_waterways_nodes.geoparquet")
                )





    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)