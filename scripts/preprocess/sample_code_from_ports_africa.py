#!/usr/bin/env python
# coding: utf-8
import sys
import os
import re
import pandas as pd
import geopandas as gpd
from utils import *
from tqdm import tqdm
tqdm.pandas()

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    # Read the ports nodes and edges data
    port_nodes = gpd.read_file(os.path.join(incoming_data_path,"ports","africa_ports.gpkg"),layer="nodes")
    port_edges = gpd.read_file(os.path.join(incoming_data_path,"ports","africa_ports.gpkg"),layer="edges")

    # Get the maximum number of the port edges ID because we want to create new edges in the sequence
    max_edge_id = max([int(re.findall(r'\d+',v)[0]) for v in port_edges["edge_id"].values.tolist()])

    # Read the results of the non-interesected points
    non_intersected = gpd.read_file(os.path.join(processed_data_path,
                                    "non_intersected_from_merged.gpkg"))
    print(non_intersected.crs)
    non_intersected = non_intersected.reset_index(drop=True)
    print("Duplicate indices in port_nodes:", port_nodes.index.duplicated().sum())
    print("Duplicate indices in non_intersected:", non_intersected.index.duplicated().sum())
    port_nodes_reset = port_nodes.reset_index(drop=True)
    non_intersected_reset = non_intersected.reset_index(drop=True)
    combined_df = pd.concat([port_nodes_reset, non_intersected_reset[["node_id", "geometry"]]], axis=0, ignore_index=True)
    # Check the duplicated'node_id'
    duplicated_node_ids = combined_df[combined_df.duplicated(subset='node_id', keep=False)]
    print(duplicated_node_ids)



    # This should have point geometry, not points with buffer geometry
    #non_intersected["geometry"]  = non_intersected.geometry.centroid
    # Also it should be just 1 point at one location, so probably 
    # Group by FeatureUID
    non_intersected = non_intersected.groupby('FeatureUID').first().reset_index()
    #non_intersected = non_intersected.set_crs(epsg=3395) 
    # Also probabble have to project this to EPSG = 4326 because the other data is in that system
    # non_intersected = non_intersected.to_crs(epsg=4326)
    print(non_intersected)


    # Extract nodes for the port networkthat are not ports
    pn = port_nodes[port_nodes["infra"] != "port"]
    print(pn)
    # Find nearest node in pn to every point in non_intersectedcd
    nearest_nodes = ckdnearest(non_intersected[['FeatureUID','geometry']],pn[['node_id','geometry']])
    print(nearest_nodes)
    from_node_id = 'FeatureUID' # ID column in non_intersected
    to_node_id = 'node_id' # ID column in non_intersected
    # Create lines between nearest nodes
    nearest_nodes["geometry"] = nearest_nodes.progress_apply(
                                lambda x:add_lines(
                                    x,non_intersected,pn,from_node_id,to_node_id
                                    ),
                                axis=1)
    nearest_nodes.rename(columns={from_node_id:"from_node",to_node_id:"to_node"},inplace=True)
    nearest_nodes["edge_id"] = list(max_edge_id + 1 + nearest_nodes.index.values)
    nearest_nodes["edge_id"] = nearest_nodes.progress_apply(lambda x: f"port_route{x.edge_id}",axis=1) 

    nearest_nodes = gpd.GeoDataFrame(nearest_nodes,geometry="geometry",crs="EPSG:4326")

    port_edges = gpd.GeoDataFrame(
                    pd.concat([port_edges,nearest_nodes],
                    axis=0,ignore_index=True),
                    geometry="geometry",crs="EPSG:4326")
    port_edges.to_file(os.path.join(processed_data_path,"africa_ports_modified.gpkg"),layer="edges",driver="GPKG")

    # Also make the new nodes layer
    # I have only chosen to add the ID and geometry from the non_intersected, but you can choose to add other columns if needed
    non_intersected.rename(columns={'FeatureUID':"node_id"},inplace=True)

    port_nodes = gpd.GeoDataFrame(
                    pd.concat([port_nodes_reset, non_intersected_reset[["node_id", "geometry"]]], axis=0),
                    geometry="geometry",crs="EPSG:4326")
    port_nodes.to_file(os.path.join(processed_data_path,"africa_ports_modified.gpkg"),layer="nodes",driver="GPKG")




if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)