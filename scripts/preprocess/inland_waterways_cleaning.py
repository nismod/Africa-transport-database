#!/usr/bin/env python
# coding: utf-8
# (1) Merge three datasets; (2)Add ISO3 (4) extraxt non_intersected
import sys
import os
import re
import pandas as pd
import geopandas as gpd
import igraph as ig
from shapely.geometry import LineString
from utils_new import *
from tqdm import tqdm
tqdm.pandas()




def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    
# IWW_ports: IWW ports data from different datasets were taken and combined, 
# then we produced a final version of the selected ports and routes between them by manual cleaning
      
# IWW ports 
      
    df_ports = pd.read_excel(os.path.join(incoming_data_path,
                                    "IWW_ports",
                                    "africa_IWW_ports.xlsx"),
                            sheet_name="selected_ports")
    df_ports["geometry"] = gpd.points_from_xy(
                            df_ports["lon"],df_ports["lat"])
    df_ports["infra"] = "IWW port"
  
    df_ports = gpd.GeoDataFrame(df_ports,geometry="geometry",crs="EPSG:4326")

# known lake routes connecting ports - merge ports and routing files
    
    df_lake_routes = pd.read_excel(os.path.join(incoming_data_path,
                                    "IWW_ports",
                                    "africa_IWW_ports.xlsx"),
                            sheet_name="known_connections")
    
    df_lake_routes = pd.merge(df_lake_routes,
                    df_ports[["name","geometry"]],
                    how="left",left_on=["from_port"],right_on=["name"])
    df_lake_routes.drop("name",axis=1,inplace=True)
    df_lake_routes.rename(columns={"geometry":"from_geometry"},inplace=True)
    df_lake_routes = pd.merge(df_lake_routes,
                    df_ports[["name","geometry"]],
                    how="left",left_on=["to_port"],right_on=["name"])
    df_lake_routes.drop("name",axis=1,inplace=True)
    df_lake_routes.rename(columns={"geometry":"to_geometry"},inplace=True)
    df_lake_routes["geometry"] = df_lake_routes.progress_apply(
                                    lambda x:LineString([x.from_geometry,x.to_geometry]),
                                    axis=1)
    df_lake_routes.drop(["from_geometry","to_geometry"],axis=1,inplace=True)
    
# Add lines for Congo ports based on the routing along the rivers

    df_congo_rivers = gpd.read_file(os.path.join(incoming_data_path,
                            "IWW_ports",
                            "edges_port_IWW_af.gpkg"))
    
    df_congo_ports = df_ports[df_ports["iso3"].isin(["CAF","COD","COG"])]
    lake_ids = list(set(df_lake_routes["from_port"].values.tolist() + df_lake_routes["to_port"].values.tolist())) 
    df_congo_ports = df_congo_ports[~df_congo_ports["name"].isin(lake_ids)]
    
    df_south_sudan = gpd.read_file(os.path.join(incoming_data_path,
                            "IWW_ports",
                            "hotosm_ssd_waterways.gpkg"))
    df_south_sudan = df_south_sudan.loc[df_south_sudan.geometry.geometry.type =='LineString']
    df_south_sudan = df_south_sudan[df_south_sudan["waterway"] == "river"]

# Create a geo dataframe with all the elements analyzed until now and create a network

    df_routes = gpd.GeoDataFrame(pd.concat([df_lake_routes[["geometry"]],
                        df_congo_rivers[["geometry"]],
                        df_south_sudan[["geometry"]]],axis=0,ignore_index=True),
                        geometry="geometry",crs="EPSG:4326")
    network = create_network_from_nodes_and_edges(df_ports.to_crs(epsg=epsg_meters),
                        df_routes.to_crs(epsg=epsg_meters),"iww",
                                snap_distance=6000,
                                geometry_precision=True)
    edges = network.edges.set_crs(epsg=epsg_meters)
    nodes = network.nodes.set_crs(epsg=epsg_meters)
    edges, nodes = components(edges,nodes,
                                node_id_column="node_id",
                                edge_id_column="edge_id",
                                from_node_column="from_node",
                                to_node_column="to_node")

# Get the specific routes that connect IWW ports in Congo basin, reject other routes???

    routing_edges = edges[["from_node","to_node","edge_id","component","geometry"]]
    routing_edges["distance"] = routing_edges.geometry.length
    G = ig.Graph.TupleList(routing_edges.itertuples(index=False), edge_attrs=list(routing_edges.columns)[2:]) #could just go?

# Minimize the edges?
    all_edges = []
    ports = nodes[nodes["infra"] == "IWW port"]["node_id"].values.tolist()
    for o in range(len(ports)-1):
        origin = ports[o]
        destinations = ports[o+1:]
        e,c = network_od_path_estimations(G,origin,destinations,"distance","edge_id")
        all_edges += e

    all_edges = list(set([item for sublist in all_edges for item in sublist]))
    africa_edges = edges[edges["edge_id"].isin(all_edges)]
    
    all_nodes = list(set(africa_edges["from_node"].values.tolist() + africa_edges["to_node"].values.tolist()))
    africa_nodes = nodes[nodes["node_id"].isin(all_nodes)]

    africa_nodes["infra"] = np.where(africa_nodes["infra"] == "IWW port",
                                    africa_nodes["infra"],
                                    "IWW route")
    
# Adding missing iso3 codes

    missing_isos = africa_nodes[africa_nodes["iso3"].isna()]
    missing_isos = add_iso_code(missing_isos,"node_id",incoming_data_path,epsg=epsg_meters)
    for del_col in ["index","index_right","lat","lon"]:
        if del_col in missing_isos.columns.values.tolist():
            missing_isos.drop(del_col,axis=1,inplace=True) 
    iso_nodes = africa_nodes[~africa_nodes["iso3"].isna()]

# Clean and create final Africa nodes and edges

    africa_nodes = pd.concat([iso_nodes,missing_isos],axis=0,ignore_index=True)
    africa_nodes.drop(["lat","lon"],axis=1,inplace=True)
    africa_nodes = gpd.GeoDataFrame(africa_nodes[["node_id","name","country",
                            "iso3","infra","component","geometry"]],
                            geometry="geometry",crs=f"EPSG:{epsg_meters}")

    africa_edges = pd.merge(africa_edges,
                        africa_nodes[["node_id","iso3","infra"]],
                        how="left",left_on=["from_node"],right_on=["node_id"])
    africa_edges.rename(columns={"iso3":"from_iso_a3","infra":"from_infra"},inplace=True)
    africa_edges.drop("node_id",axis=1,inplace=True)
    africa_edges = pd.merge(africa_edges,
                        africa_nodes[["node_id","iso3","infra"]],
                        how="left",left_on=["to_node"],right_on=["node_id"])
    africa_edges.rename(columns={"iso3":"to_iso_a3","infra":"to_infra"},inplace=True)
    africa_edges.drop("node_id",axis=1,inplace=True)
    africa_edges["length_m"] = africa_edges.geometry.length
    africa_edges.rename(columns={"edge_id":"id","from_node":"from_id","to_node":"to_id"},inplace=True)
    africa_nodes.rename(columns={"node_id":"id"},inplace=True)

# Save nodes and edges

    africa_edges = africa_edges.to_crs(epsg=4326)
    africa_nodes = africa_nodes.to_crs(epsg=4326)
    africa_nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_iww_network.gpkg"),
                        layer="nodes",driver="GPKG")
    africa_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_iww_network.gpkg"),
                        layer="edges",driver="GPKG")

    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)