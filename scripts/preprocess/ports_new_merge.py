#!/usr/bin/env python
# coding: utf-8

import sys
import os
import re
import pandas as pd
import geopandas as gpd
import igraph as ig
from shapely.geometry import Point, LineString, Polygon
from math import radians, cos, sin, asin, sqrt
from haversine import haversine
from utils_new import *
from tqdm import tqdm
import igraph as ig
import networkx
tqdm.pandas()




def add_lines2(x, nodes_df, from_col, to_col):
    from_id = x[from_col]
    to_id = x[to_col]

    from_point = nodes_df[nodes_df["id"] == from_id]
    to_point = nodes_df[nodes_df["id"] == to_id]

    if from_point.empty:
        print(f"Missing from_id: {from_id}")
    if to_point.empty:
        print(f"Missing to_id: {to_id}")

    if not from_point.empty and not to_point.empty:
        return LineString([from_point.geometry.values[0], to_point.geometry.values[0]])
    else:
        return None


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

def get_continent(x):
    if x == "AF":
        return "Africa"
    elif x in ("AS","OC"):
        return "Asia & Pacific"
    elif x == "EU":
        return "Europe"
    elif x == "NA":
        return "North America"
    elif x == "SA":
        return "South America"
    else:
        return x


def main(config):

    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    cutoff_distance = 6600 # We assume ports within 6.6km are the same
    # 1. Read the previously created dataset
    df = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "global_maritime_network.gpkg"),layer = 'nodes') 
    df["country"] = df.progress_apply(lambda x:str(x["name"]).split("_")[1] if "_" in str(x["name"]) else x['name'],axis=1)
    df["name"] = df.progress_apply(lambda x:str(x["name"]).split("_")[0] if "_" in str(x["name"]) else x['name'],axis=1)
    df["continent"] = df["Continent_Code"].progress_apply(lambda x: get_continent(x))
    df_edges = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "global_maritime_network.gpkg"),layer = 'edges') 
    df_new = gpd.read_file(os.path.join(incoming_data_path,
                                    "Global port supply-chains",
                                    "Ports Updated 2025",
                                    "Ports.shp"))
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
   

    # Standardize merged_gdf
    merged_gdf = merged_gdf.rename(columns={"port_name": "name", "ISO3": "iso3"})
    merged_gdf["infra"] = "port"
    merged_gdf.drop(columns=["country_csv", "ISO3_csv"], inplace=True, errors="ignore")

    # Ensure both GeoDataFrames are in the same CRS
    merged_gdf = merged_gdf.to_crs(epsg=epsg_meters)
    df = df.to_crs(epsg=epsg_meters)
    port_df = df[df["infra"] == "port"]

    # Perform spatial join: 'left' to keep all rows from df
    left_join = gpd.sjoin_nearest(merged_gdf,port_df, how="left", max_distance= 3000)

    # Perform spatial join: 'right' to keep all rows from merged_gdf
    right_join = gpd.sjoin_nearest(port_df, merged_gdf, how="left", max_distance= 3000)

    # Now union the two (include only unmatched rows from the right join)
    # Filter rows in right_join where df index is missing => unmatched
    unmatched_right = right_join[right_join.index_right.isna()].drop(columns='index_right')

    # Combine both sets
    nodes_merged = pd.concat(
                                [
                                    left_join, 
                                    unmatched_right, 
                                    df[df["infra"] != "port"][["id","infra","geometry"]]
                                ], 
                                ignore_index=True)
    

    # Convert to GeoDataFrame again with correct CRS
    nodes_merged = gpd.GeoDataFrame(nodes_merged, geometry="geometry", crs=epsg_meters)
    nodes_merged["infra_left"] = nodes_merged["infra_left"].fillna(nodes_merged["infra_right"])
    nodes_merged["infra_left"] = nodes_merged["infra_left"].fillna(nodes_merged["infra"])
    nodes_merged["iso3_left"] = nodes_merged["iso3_left"].fillna(nodes_merged["iso3_right"])
    nodes_merged["country_left"] = nodes_merged["country_left"].fillna(nodes_merged["country_right"])
    nodes_merged["continent_left"] = nodes_merged["continent_left"].fillna(nodes_merged["continent_right"])
    nodes_merged["portname"] = nodes_merged["portname"].fillna(nodes_merged["name"])
    nodes_merged["portid"] = nodes_merged["portid"].fillna(nodes_merged["id"])
    nodes_merged.drop(columns=["name", "iso3_right", "infra_right","infra","id"], inplace=True, errors="ignore")
    nodes_merged.rename(
                        columns={
                                    "portid": "id",
                                    "infra_left":"infra",
                                    "portname": "name", 
                                    "iso3_left": "iso3",
                                    "country_left": "country",
                                    "continent_left":"continent"}, 
                        inplace=True)
    
    
   
    nodes_merged = gpd.GeoDataFrame(nodes_merged, geometry="geometry", crs=epsg_meters)
    nodes_merged["vessel_cou"] = nodes_merged["vessel_cou"].fillna(0)
    nodes_merged = nodes_merged.sort_values(by="vessel_cou", ascending=False)
    nodes_merged = nodes_merged.drop_duplicates(subset=["id"], keep='first')
    # print (nodes_merged)

    """Remove the edges which contain nodes not found in the node list 
    """
    # nodes = nodes_merged["id"].values.tolist()
    nodes = nodes_merged[(nodes_merged["infra"] == "port") & (nodes_merged["continent"] == "Africa")]["id"].values.tolist()
    print (len(nodes))
    from_to_nodes = list(set(df_edges["from_id"].values.tolist() + df_edges["to_id"].values.tolist()))
    extra_nodes = [n for n in from_to_nodes if n not in nodes] 
    # new_nodes = [n for n in nodes if n not in from_to_nodes]
    new_nodes = nodes
    print (df_edges)
    df_edges = df_edges[~(df_edges["from_id"].isin(nodes) | df_edges["to_id"].isin(nodes))]
    print (df_edges)
    # df_edges = df_edges[~(df_edges["from_id"].isin(nodes) | df_edges["to_id"].isin(nodes))]

    # df_origins = nodes_merged[
    #                         nodes_merged["infra"] == "port"
    #                         ][nodes_merged["id"].isin(new_nodes)][["id","infra","geometry"]]
    df_origins = nodes_merged[
                            nodes_merged["infra"] == "port"
                            ][nodes_merged["id"].isin(new_nodes)][["id","infra","geometry"]]
    print (df_origins)
    df_origins.rename(columns={"id":"from_id"},inplace=True)
    left_join = gpd.sjoin_nearest(
                            df_origins,
                            nodes_merged[nodes_merged["infra"] != "port"][["id","infra","geometry"]], 
                            how="left")
    left_join.drop("index_right",axis=1,inplace=True)
    left_join.rename(
                    columns={
                                "infra_left":"from_infra",
                                "infra_right":"to_infra",
                                "geometry":"from_geometry"
                            },
                    inplace=True)

    left_join = pd.merge(
                        left_join,
                        nodes_merged[nodes_merged["infra"] != "port"][["id","geometry"]], 
                        on='id', how='left'
                        )
    left_join.rename(
                    columns={
                                "id":"to_id",
                                "geometry":"to_geometry"
                            },
                    inplace=True)
    
    left_join["geometry"] = left_join.progress_apply(lambda x: LineString([x.from_geometry, x.to_geometry]),axis=1)
    left_join.drop(["from_geometry","to_geometry"],axis=1,inplace=True)

    left_join = gpd.GeoDataFrame(left_join,geometry="geometry",crs=f"EPSG:{epsg_meters}")
    left_join = left_join.to_crs(epsg=4326)
    print(left_join)

    right_join = left_join.copy()
    right_join.columns = ["to_id","to_infra","from_id","from_infra","geometry"]
    print (left_join.crs)
    print (df_edges.crs)
    df_edges = pd.concat([df_edges,left_join,right_join],axis=0,ignore_index=True)
    df_edges.drop("id",axis=1,inplace=True)

    print (df_edges)

    df_edges["from_id"] = df_edges["from_id"].str.replace('maritime', 'maritime_')
    df_edges["from_id"] = df_edges["from_id"].str.replace('port', 'port_')

    df_edges["to_id"] = df_edges["to_id"].str.replace('maritime', 'maritime_')
    df_edges["to_id"] = df_edges["to_id"].str.replace('port', 'port_')

    port_edges = gpd.GeoDataFrame(df_edges,geometry="geometry",crs=f"EPSG:4326")

    port_edges["id"] = port_edges.index.values.tolist()
    port_edges["id"] = port_edges.progress_apply(lambda x:f"maritimeroute_{x.id}",axis=1)
    port_edges["length_degree"] = port_edges.geometry.length
    port_edges = port_edges.to_crs('+proj=cea')
    port_edges["distance"] = 0.001*port_edges.geometry.length
    port_edges = port_edges.to_crs(epsg=4326)
    port_edges["distance_km"] = port_edges.progress_apply(lambda x:modify_distance(x),axis=1)
    # id_to_iso3 = nodes_merged.set_index("id")["iso3"]
    # port_edges["from_iso3"] = port_edges["from_id"].map(id_to_iso3)
    # port_edges["to_iso3"] = port_edges["to_id"].map(id_to_iso3)
    port_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_PROVA_NEW1.gpkg"),layer="edges",driver="GPKG")
    
    
    
    nodes_merged["id"] = nodes_merged["id"].str.replace('maritime', 'maritime_')
    nodes_merged["id"] = nodes_merged["id"].str.replace('port', 'port_')
    nodes_merged.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_PROVA_NEW1.gpkg"),layer="nodes",driver="GPKG")
   

    # Get the ports for AFRICA
    
    port_edges = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_PROVA_NEW1.gpkg"),layer="edges")
    port_nodes = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_PROVA_NEW1.gpkg"),layer="nodes")
    # global_edges = port_edges[["from_id","to_id","id","from_infra","to_infra","geometry"]].to_crs(epsg_meters)
    # global_edges["distance"] = global_edges.geometry.length
    global_edges = port_edges[["from_id","to_id","id","distance"]]
    africa_ports = port_nodes[port_nodes["continent"] == "Africa"]
    G = ig.Graph.TupleList(global_edges.itertuples(index=False), edge_attrs=list(global_edges.columns)[2:])
    # print (G)

    all_edges = []
    africa_nodes = africa_ports[africa_ports["infra"]=="port"]["id"].values.tolist()

    for o in range(len(africa_nodes)-1):
        origin = africa_nodes[o]
        destinations = africa_nodes[o+1:]
        e,_ = network_od_path_estimations(G,origin,destinations,"distance","id")
        all_edges += e

    all_edges = list(set([item for sublist in all_edges for item in sublist]))
    # all_edges += port_edges[port_edges.index > 9390]["id"].values.tolist()
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
    # id_to_iso3 = africa_nodes.set_index("id")["iso3"]
    # africa_edges["from_iso3"] = africa_edges["from_id"].map(id_to_iso3)
    # africa_edges["to_iso3"] = africa_edges["to_id"].map(id_to_iso3)


    africa_edges = africa_edges[["id","from_id","to_id","from_infra","to_infra","distance","geometry"]]
    africa_edges = africa_edges.rename(columns={"distance":"distance_km"})
    
    africa_nodes = africa_nodes[['id', 'name', 'fullname', 'infra', 'country', 'iso3',
       'vessel_cou', 'vessel_c_1', 'vessel_c_2', 'vessel_c_3', 'vessel_c_4',
       'vessel_c_5', 'industry_t', 'industry_1', 'industry_2', 'share_coun',
       'share_co_1', 'call_container', 'call_drybulk', 'call_generalcargo', 'call_roro',
       'call_tanker', 'capacity_container', 'capacity_drybulk',
       'capacity_generalcargo', 'capacity_roro', 'capacity_tanker',
       'time_container', 'time_drybulk', 'time_generalcargo', 'time_roro',
       'time_tanker', 'geometry']]
    africa_nodes = africa_nodes.rename(columns={"vessel_cou": "vessel_count_total","vessel_c_1": "vessel_count_container","vessel_c_2": "vessel_count_drybulk",
                                                "vessel_c_3": "vessel_count_generalcargo","vessel_c_4": "vessel_count_roro","vessel_c_5": "vessel_count_tanker",
                                                "industry_t": "industry_top1","industry_1": "industry_top2","industry_2": "industry_top3",
                                                "share_coun": "share_country_maritime_import","share_co_1": "share_country_maritime_export",
                                                'capacity_container':'capacity_container_tons', 'capacity_drybulk': 'capacity_drybulk_tons',
                                                'capacity_generalcargo':'capacity_generalcargo_tons', 'capacity_roro':'capacity_roro_tons', 
                                                'capacity_tanker':'capacity_tanker_tons', 'time_container':'time_container_h', 'time_drybulk':'time_drybulk_h', 
                                                'time_generalcargo':'time_generalcargo_h', 'time_roro':'time_roro_h','time_tanker':'time_tanker_h'})   

    africa_nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_maritime_network_PROVA_NEW1.gpkg"),
                        layer="nodes",driver="GPKG")
    africa_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_maritime_network_PROVA_NEW1.gpkg"),
                        layer="edges",driver="GPKG")
    print("Africa maritime network created successfully.")    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)