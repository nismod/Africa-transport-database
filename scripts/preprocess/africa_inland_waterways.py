#!/usr/bin/env python
# coding: utf-8
# (1) Merge three datasets; (2)Add ISO3 (4) extraxt non_intersected
import sys
import os
import re
import json
import pandas as pd
import geopandas as gpd
import igraph as ig
from shapely.geometry import LineString
from utils import *
from tqdm import tqdm
tqdm.pandas()




def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    # Step 1: Take the OSM rivers data and convert it into a network
    step = False # This step takes a lot of time, so we have set it to false after running it once
    if step is True:
        edges = gpd.read_parquet(
                os.path.join(
                    incoming_data_path,
                    "Africa_osm_rivers",
                    "OpenStreetMap_Waterways_for_Africa.geoparquet")
                )

        edges = edges[edges["waterway"] == "river"] # Only select the rivers because they will be used for navigation
        network = create_network_from_nodes_and_edges(None,edges,"iww")

        edges = gpd.GeoDataFrame(network.edges,geometry="geometry",crs="EPSG:4326")
        nodes = gpd.GeoDataFrame(network.nodes,geometry="geometry",crs="EPSG:4326")

        edges, nodes = components(edges,nodes,
                                node_id_column="node_id",edge_id_column="edge_id",
                                from_node_column="from_node",to_node_column="to_node"
                                )
        edges["component_size"] = edges.groupby(["component"])["component"].transform("count")
        nodes["component_size"] = nodes.groupby(["component"])["component"].transform("count")

        edges.to_parquet(
                    os.path.join(
                        incoming_data_path,
                        "Africa_osm_rivers",
                        "africa_river_edges.geoparquet")
                    )
        nodes.to_parquet(
                    os.path.join(
                        incoming_data_path,
                        "Africa_osm_rivers",
                        "africa_river_nodes.geoparquet")
                    )
    
    # Step 2: Select the big connected rivers across Africa based on the largest component sizes
    step = True
    if step is True:
        component_size_threshold = 750 # We checked this from the reuslt of the previous step
        snap_distance_threshold = 6000
        epsg_meters = 3395
        edges = gpd.read_parquet(
                        os.path.join(
                            incoming_data_path,
                            "Africa_osm_rivers",
                            "africa_river_edges.geoparquet")
                        )
        edges = edges[edges["component_size"] > component_size_threshold]
        original_crs = edges.crs
        edges.drop(["edge_id","from_node","to_node","component","component_size"],axis=1,inplace=True)

        # IWW_ports: IWW ports data from different datasets were taken and combined, 
        # then we produced a final version of the selected ports and routes between them by manual cleaning
        # IWW ports 
        df_ports = pd.read_excel(os.path.join(incoming_data_path,
                                    "IWW_ports",
                                    "africa_IWW_ports.xlsx"),
                            sheet_name="selected_ports")
        df_ports["geometry"] = gpd.points_from_xy(
                                df_ports["lon"],df_ports["lat"])
        df_ports["infra"] = df_ports.progress_apply(lambda x:f"IWW {x.infra}",axis=1)
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
        
        df_routes = gpd.GeoDataFrame(pd.concat([df_lake_routes[["geometry"]],
                        edges[["geometry"]]],axis=0,ignore_index=True),
                        geometry="geometry",crs="EPSG:4326")
        network = create_network_from_nodes_and_edges(df_ports.to_crs(epsg=epsg_meters),
                            df_routes.to_crs(epsg=epsg_meters),"iww",
                                    snap_distance=6000)
        edges, nodes = components(network.edges,network.nodes,
                                    node_id_column="node_id",
                                    edge_id_column="edge_id",
                                    from_node_column="from_node",
                                    to_node_column="to_node")

        edges = gpd.GeoDataFrame(edges,geometry="geometry",crs=f"EPSG:{epsg_meters}")
        nodes = gpd.GeoDataFrame(nodes,geometry="geometry",crs=f"EPSG:{epsg_meters}")

        edges = edges.to_crs(epsg=4326)
        nodes = nodes.to_crs(epsg=4326)

        edges.to_parquet(
                    os.path.join(
                        incoming_data_path,
                        "Africa_osm_rivers",
                        "africa_network_edges.geoparquet")
                    )
        nodes.to_parquet(
                    os.path.join(
                        incoming_data_path,
                        "Africa_osm_rivers",
                        "africa_network_nodes.geoparquet")
                    )
        edges.to_file(
                    os.path.join(
                        incoming_data_path,
                        "Africa_osm_rivers",
                        "africa_network_edges.gpkg"),
                    layer="edges",driver="GPKG"
                    )
        nodes.to_file(
                    os.path.join(
                        incoming_data_path,
                        "Africa_osm_rivers",
                        "africa_network_nodes.gpkg"),
                    layer="nodes",driver="GPKG"
                    )

    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)