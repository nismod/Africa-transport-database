#!/usr/bin/env python
# coding: utf-8
# Code to extract the suez canal navigation route 
import os
import pandas as pd
import geopandas as gpd
import re
from utils import *
from tqdm import tqdm
tqdm.pandas()

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    # Read the OSM data and the suez canal IDs
    waterways = gpd.read_file(os.path.join(
                    incoming_data_path,
                    "egypt-latest-free.shp",
                    "gis_osm_waterways_free_1.shp"))
    waterways["osm_id"] = waterways["osm_id"].astype(int)
    suez_ids = pd.read_csv(os.path.join(
                            incoming_data_path,
                                "egypt-latest-free.shp",
                                "suez_canal_ids.csv"))
    suez_ids = [int(n) for n in suez_ids["osm_id"].values.tolist()]
    suez_canal = waterways[waterways["osm_id"].isin(suez_ids)]
    # Convert to a topological network
    network = create_network_from_nodes_and_edges(None,suez_canal,"water")
    edges, nodes = components(network.edges,network.nodes,"node_id")

    # Rename nodes to match global nodes layer
    df_global_ports = gpd.read_file(os.path.join(incoming_data_path,
                                    "Global port supply-chains",
                                    "Network",
                                    "nodes_maritime.gpkg")) 

    nodes["infra"] = "maritime"
    prt = df_global_ports[df_global_ports["infra"] == "maritime"]
    max_port_id = max([int(re.findall(r'\d+',v)[0]) for v in prt["id"].values.tolist()])
    nodes["id"] = list(max_port_id + 1 + nodes.index.values)
    nodes["id"] = nodes.progress_apply(lambda x: f"maritime{x.id}",axis=1)
    edges = pd.merge(edges,
                        nodes[["node_id","id"]],
                        how="left",left_on=["from_node"],right_on=["node_id"])
    edges.drop("node_id",axis=1,inplace=True)
    edges.rename(columns={"id":"from_id"},inplace=True)
    edges = pd.merge(edges,
                    nodes[["node_id","id"]],
                    how="left",left_on=["to_node"],right_on=["node_id"])
    edges.rename(columns={"id":"to_id"},inplace=True)
    edges.drop("node_id",axis=1,inplace=True)
    edges["from_infra"] = "maritime"
    edges["to_infra"] = "maritime"
    # Write the Suez Canal routes to a GPKG
    gpd.GeoDataFrame(edges,geometry="geometry",crs=waterways.crs).to_file(os.path.join(
                    incoming_data_path,
                    "egypt-latest-free.shp",
                    "suez_canal_network.gpkg"),layer="edges",driver="GPKG")
    gpd.GeoDataFrame(nodes,geometry="geometry",crs=waterways.crs).to_file(os.path.join(
                    incoming_data_path,
                    "egypt-latest-free.shp",
                    "suez_canal_network.gpkg"),layer="nodes",driver="GPKG")


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)