#!/usr/bin/env python
# coding: utf-8
# (1) Merge three datasets; (2)Add ISO3 (4) extract non_intersected
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
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
tqdm.pandas()

def haversine_distance(point1, point2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lon1, lat1 = point1.bounds[0], point1.bounds[1]
    lon2, lat2 = point2.bounds[0], point2.bounds[1]

    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers
    # print('Distance from beginning to end of route in km: ',round((c * r), 2),'\n')
    return c * r

def modify_distance(x):
    if x["length"] < 355 and x["distance"] < 40075:
        return x["distance"]
    else:
        start = x.geometry.coords[0]
        end = x.geometry.coords[-1]
        return haversine(
                    (
                        round(start[1],2),
                        round(start[0],2)
                    ),
                    (
                        round(end[1],2),
                        round(end[0],2)
                    )
                )
def ckdnearest(gdA, gdB):
        from scipy.spatial import cKDTree
        import numpy as np

        a_coords = np.array(list(zip(gdA.geometry.x, gdA.geometry.y)))
        b_coords = np.array(list(zip(gdB.geometry.x, gdB.geometry.y)))
        btree = cKDTree(b_coords)
        dist, idx = btree.query(a_coords, k=1)
        gdB_nearest = gdB.iloc[idx].reset_index(drop=True)
        gdf = pd.concat([
            gdA.reset_index(drop=True),
            gdB_nearest.add_suffix('_nearest'),
            pd.Series(dist, name='dist')
        ], axis=1)
        return gdf

def match_ports(df1, df2, df1_id_column, df2_id_column, cutoff_distance):
    matches = ckdnearest(df1, df2)

    # Rename back to expected column names
    matches = matches.rename(columns={
        f"{df1_id_column}": df1_id_column,
        f"{df2_id_column}_nearest": df2_id_column,
    })

    matches = matches.sort_values(by="dist", ascending=True)
    matches["matches"] = np.where(matches["dist"] <= cutoff_distance, "Y", "N")
    selection = matches[matches["dist"] <= cutoff_distance]
    selection = selection.drop_duplicates(subset=df1_id_column, keep='first')
    matched_ids = list(selection[df1_id_column])
    
    return selection[[df1_id_column, df2_id_column]], df1[~df1[df1_id_column].isin(matched_ids)]

def add_iso_code(df,df_id_column,incoming_data_path):
    # Insert countries' ISO CODE
    africa_boundaries = gpd.read_file(os.path.join(
                            incoming_data_path,
                            "Africa_GIS Supporting Data",
                            "a. Africa_GIS Shapefiles",
                            "AFR_Political_ADM0_Boundaries.shp",
                            "AFR_Political_ADM0_Boundaries.shp"))
    africa_boundaries.rename(columns={"DsgAttr03":"iso3"},inplace=True)
    # Spatial join
    m = gpd.sjoin(df, 
                    africa_boundaries[['geometry', 'iso3']], 
                    how="left", predicate='within').reset_index()
    m = m[~m["iso3"].isna()]        
    un = df[~df[df_id_column].isin(m[df_id_column].values.tolist())]
    un = gpd.sjoin_nearest(un,
                            africa_boundaries[['geometry', 'iso3']], 
                            how="left").reset_index()
    m = pd.concat([m,un],axis=0,ignore_index=True)
    return m

def main(config):

    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    cutoff_distance = 6600 # We assume ports within 6.6km are the same
    # 1. Read the previously created dataset
    df = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "global_maritime_network.gpkg"),layer = 'nodes') 
    df_edges = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "global_maritime_network.gpkg"),layer = 'edges') 
    df_new = gpd.read_file(os.path.join(incoming_data_path,
                                    "Global port supply-chains",
                                    "Ports Updated 2025",
                                    "global_ports_up.gpkg"))
    maritime_values_calls = pd.read_csv(os.path.join(
                 incoming_data_path,
                 "Global port supply-chains",
                                    "Ports Updated 2025",
                                    "port_calls_average_2019-2024.csv"))
    maritime_values_cap = pd.read_csv(os.path.join(
                 incoming_data_path,
                 "Global port supply-chains",
                                    "Ports Updated 2025",
                                    "port_capacity_called_average_2019-2024.csv"))
    maritime_values_turn = pd.read_csv(os.path.join(
                 incoming_data_path,
                 "Global port supply-chains",
                                    "Ports Updated 2025",
                                    "port_turn_around_time_average_2019-2024.csv"))
     
    merged_gdf = df_new.merge(maritime_values_calls, on='portid', how='left', suffixes=('', '_csv'))
    merged_gdf = merged_gdf.merge(maritime_values_cap, on='portid', how='left', suffixes=('', '_csv'))
    merged_gdf = merged_gdf.merge(maritime_values_turn, on='portid', how='left', suffixes=('', '_csv'))

    df[df["id"].duplicated(keep=False)] #see if there are duplicates

    


    # Standardize merged_gdf
    merged_gdf = merged_gdf.rename(columns={"port_name": "name", "ISO3": "iso3"})
    merged_gdf["infra"] = "port"
    merged_gdf.drop(columns=["country_csv", "ISO3_csv"], inplace=True, errors="ignore")

    merged_attributes = merged_gdf.set_index("portid")

    # Match ports spatially
    mapping, new_ports_matched = match_ports(
        df.to_crs(epsg=epsg_meters),
        merged_gdf.to_crs(epsg=epsg_meters),
        "id", "portid",
        cutoff_distance
    )

    mapping_dict = dict(zip(mapping["id"], mapping["portid"]))
    mapping_df = pd.DataFrame(list(mapping_dict.items()), columns=["id", "portid"])

    # Merge df with mapping
    matched_df_subset = df.merge(mapping_df, on="id", how="left")

    # Join attributes from merged_gdf
    matched_with_attrs = matched_df_subset.join(merged_attributes, on="portid", rsuffix="_merged")
    matched_with_attrs["infra"] = matched_df_subset["infra"]
    matched_with_attrs.drop(columns=["portid"], inplace=True)

    # unmatched new ports
    matched_portids = set(mapping_dict.values())
    unmatched = merged_gdf[~merged_gdf["portid"].isin(matched_portids)].copy()
    unmatched["id"] = None

    # Assign new IDs to unmatched
    existing_ids = df[df["infra"] == "port"]["id"].tolist()
    existing_nums = [int(re.findall(r"\d+", v)[0]) for v in existing_ids if re.match(r"port_\d+", v)]
    max_existing = max(existing_nums) if existing_nums else 0
    new_ids = [f"port_{i}" for i in range(max_existing + 1, max_existing + 1 + len(unmatched))]

    unmatched["id"] = new_ids
    unmatched["infra"] = "port"

    # Combine
    combined_ports = pd.concat([matched_with_attrs, unmatched], ignore_index=True)
    combined_ports = gpd.GeoDataFrame(combined_ports, geometry="geometry", crs="EPSG:4326")

    # Merge with unmatched original df
    original_unmatched_df = df[~df["id"].isin(mapping_dict.keys())]
    final_ports = pd.concat([original_unmatched_df, combined_ports], ignore_index=True)
    final_ports = gpd.GeoDataFrame(final_ports, geometry="geometry", crs="EPSG:4326")

    # Clean ID format and check for duplicates
    final_ports["id"] = final_ports["id"].apply(lambda x: re.sub(r'([a-zA-Z]+)(\d+)', r'\1_\2', str(x)) if '_' not in str(x) else str(x))
    duplicate_ids = final_ports["id"][final_ports["id"].duplicated()]
    if not duplicate_ids.empty:
        raise ValueError(f"Duplicate port IDs found in final_ports: {duplicate_ids.tolist()}")

    # Drop temp geometry columns
    final_ports.drop(columns=["geometry_attr", "geometry_merged"], inplace=True, errors='ignore')

    # Save result
    final_ports.to_file(os.path.join(
        processed_data_path,
        "infrastructure",
        "global_maritime_network_UPDATED.gpkg"),
        layer="nodes",
        driver="GPKG"
    )

        
    # Need to create the edges for the new ports once I know I have no duplicates and create the edges layer too, then get the ports only for Africa

    # Get the ports for Africa
    port_edges = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "global_maritime_network_UPDATED.gpkg"),layer = 'edges') 
    port_nodes = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_UPDATED.gpkg"),layer="nodes")
    # global_edges = port_edges[["from_id","to_id","id","from_infra","to_infra","geometry"]].to_crs(epsg_meters)
    # global_edges["distance"] = global_edges.geometry.length
    global_edges = port_edges[["from_id","to_id","id","distance"]]
    africa_ports = port_nodes[port_nodes["Continent_Code"] == "AF"]
    G = ig.Graph.TupleList(global_edges.itertuples(index=False), edge_attrs=list(global_edges.columns)[2:])
    # print (G)

    all_edges = []
    africa_nodes = port_nodes[port_nodes["Continent_Code"] == "AF"]["id"].values.tolist()
    for o in range(len(africa_nodes)-1):
        origin = africa_nodes[o]
        destinations = africa_nodes[o+1:]
        e,_ = network_od_path_estimations(G,origin,destinations,"distance","id")
        all_edges += e

    all_edges = list(set([item for sublist in all_edges for item in sublist]))
    all_edges += port_edges[port_edges.index > 9390]["id"].values.tolist()
    all_edges = list(set(all_edges))
    # africa_edges = port_edges[port_edges["id"].isin(all_edges)]
    africa_edges = port_edges[port_edges["id"].isin(all_edges)][["from_id","to_id"]]
    dup_df = africa_edges.copy()
    dup_df[["from_id","to_id"]] = dup_df[["to_id","from_id"]]
    africa_edges = pd.concat([africa_edges,dup_df],axis=0,ignore_index=True)
    africa_edges = africa_edges.drop_duplicates(subset=["from_id","to_id"],keep="first")
    africa_edges = gpd.GeoDataFrame(
                        pd.merge(
                                africa_edges,port_edges,
                                how="left",on=["from_id","to_id"]
                                ),
                        geometry="geometry",crs="EPSG:4326")
    
    all_nodes = list(set(africa_edges["from_id"].values.tolist() + africa_edges["to_id"].values.tolist()))
    africa_nodes = port_nodes[port_nodes["id"].isin(all_nodes)] 

    africa_nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_maritime_network_UPDATED.gpkg"),
                        layer="nodes",driver="GPKG")
    africa_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_maritime_network_UPDATED.gpkg"),
                        layer="edges",driver="GPKG")


    port_edges = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_UPDATED.gpkg"),layer="edges")
    port_edges["from_infra"] = port_edges.progress_apply(
                                lambda x:re.sub('[^a-zA-Z]+', '',x["from_id"]),
                                axis=1)
    port_edges["to_infra"] = port_edges.progress_apply(
                                lambda x:re.sub('[^a-zA-Z]+', '',x["to_id"]),
                                axis=1)
    port_edges["id"] = port_edges.index.values.tolist()
    port_edges["id"] = port_edges.progress_apply(lambda x:f"maritimeroute_{x.id}",axis=1)
    port_edges['duplicates'] = pd.DataFrame(
                                    np.sort(port_edges[['from_id','to_id']])
                                    ).duplicated(keep=False).astype(int)
    u_df = port_edges[port_edges['duplicates'] == 0]
    u_df[["to_id","from_id"]] = u_df[["from_id","to_id"]]
    port_edges = gpd.GeoDataFrame(
                    pd.concat([port_edges,u_df],axis=0,ignore_index=True),
                    geometry="geometry",crs="EPSG:4326")
    port_edges.drop("duplicates",axis=1,inplace=True)
    # port_edges["length"] = port_edges.geometry.length
    # port_edges = port_edges.to_crs('+proj=cea')
    # port_edges["distance"] = 0.001*port_edges.geometry.length
    # port_edges = port_edges.to_crs(epsg=4326)
    # port_edges["distance"] = port_edges.progress_apply(lambda x:modify_distance(x),axis=1)
    port_edges.to_csv("test2.csv")
    port_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_UPDATED.gpkg"),layer="edges",driver="GPKG")


    # port_edges['duplicates'] = pd.DataFrame(
    #                                 np.sort(port_edges[['from_id','to_id']])
    #                                 ).duplicated(keep=False).astype(int)
    # u_df = port_edges[port_edges['duplicates'] == 0]
    # u_df[["to_id","from_id"]] = u_df[["from_id","to_id"]]
    # port_edges = gpd.GeoDataFrame(
    #                 pd.concat([port_edges,u_df],axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")
    # port_edges.drop("duplicates",axis=1,inplace=True)
    # # port_edges["length"] = port_edges.geometry.length
    # # port_edges = port_edges.to_crs('+proj=cea')
    # # port_edges["distance"] = 0.001*port_edges.geometry.length
    # # port_edges = port_edges.to_crs(epsg=4326)
    # # print (port_edges)
    port_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_maritime_network_UPDATED.gpkg"),
                        layer="edges",driver="GPKG")







if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)