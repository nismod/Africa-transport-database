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

    #df[df["id"].duplicated(keep=False)] #see if there are duplicates

   

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
    
    # source_geom = nodes_merged.loc[nodes_merged["name"] == "Sidi Kerir_Egypt", "geometry"].values[0]
    # nodes_merged.loc[nodes_merged["name"] == "Sidi Kerir", "geometry"] = source_geom
    # nodes_merged = nodes_merged[nodes_merged["name"] != "Sidi Kerir_Egypt"]
    # Clean up
    # nodes_merged.drop(columns=["geometry_merged", "index_right", "index_left"], inplace=True, errors="ignore")

   

   # # Step 1: Get max port ID number
   #  prt = nodes_merged[nodes_merged["infra"] == "port"]
   #  max_port_id = max([
   #      int(re.findall(r'\d+', v)[0]) 
   #      for v in prt["id"].values 
   #      if isinstance(v, str) and v.startswith("port") and re.search(r'\d+', v)
   #  ], default=0)

   #  # Step 2: Create a closure with a mutable counter
   #  def make_id_assigner(start_count):
   #      counter = [start_count]  # list used as mutable integer

   #      def assign_id(row):
   #          if row["infra"] == "port":
   #              if pd.isna(row["id"]):
   #                  new_id = f"port{counter[0]}"
   #                  counter[0] += 1
   #                  return new_id
   #              else:
   #                  return row["id"]  # keep existing
   #          else:
   #              return row["id"]  # leave other infra types untouched

   #      return assign_id

   #  # Step 3: Apply the function
   #  id_assigner = make_id_assigner(max_port_id + 1)
   #  nodes_merged = nodes_merged.reset_index(drop=True)
   #  nodes_merged["id"] = nodes_merged.progress_apply(id_assigner, axis=1)

    # Add continent code
   
    nodes_merged = gpd.GeoDataFrame(nodes_merged, geometry="geometry", crs=epsg_meters)
    # df_edges = gpd.GeoDataFrame(df_edges, geometry="geometry", crs=epsg_meters)

    # nodes_merged.to_file(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network_PROVA_NEW.gpkg"),
    #                     layer="nodes",driver="GPKG")

    """Remove the edges which contain nodes not found in the node list 
    """
    nodes = nodes_merged["id"].values.tolist()
    from_to_nodes = list(set(df_edges["from_id"].values.tolist() + df_edges["to_id"].values.tolist()))
    extra_nodes = [n for n in from_to_nodes if n not in nodes] 
    new_nodes = [n for n in nodes if n not in from_to_nodes]

    df_edges = df_edges[~(df_edges["from_id"].isin(extra_nodes) | df_edges["to_id"].isin(extra_nodes))]

    df_origins = nodes_merged[
                            nodes_merged["infra"] == "port"
                            ][nodes_merged["id"].isin(new_nodes)][["id","infra","geometry"]]
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
    print (left_join.crs)
    print (df_edges.crs)
    df_edges = pd.concat([df_edges,left_join],axis=0,ignore_index=True)
    df_edges.drop("id",axis=1,inplace=True)

    print (df_edges)

    # ids_to_check = {
    # "port_1620", "maritime_2700", "port_1512", "maritime_1613",
    # "port_1617", "maritime_2599", "port_1573", "maritime_64",
    # "port_1598", "maritime_675", "port_1712", "maritime_385",
    # "port_1641", "maritime_1"
    # }

    # print(nodes_merged[nodes_merged["id"].isin(ids_to_check)])
    
    # nodes_merged["id"] = nodes_merged["id"].astype(str).str.strip()
    # connect_pairs = [("port_1512","maritime_1613","port","maritime"),
    #                         ("port_1620","maritime_2700","port","maritime"),
    #                         ("port_1617","maritime_2599","port","maritime"),
    #                         ("port_1573","maritime_64","port","maritime"),
    #                         ("port_1598","maritime_675","maritime","maritime"),
    #                         ("port_1712","maritime_385","maritime","maritime"),
    #                         ("port_1641","maritime_1","maritime","maritime")
    #                         ]
    
    
    
    # nodes_merged2 = nodes_merged.copy()
    # nodes_merged2.rename(columns={"id":"from_id"},inplace=True)
    # from_node='from_id'
    # to_node='to_id'
    # additional_lines = pd.DataFrame(connect_pairs,columns=["from_id","to_id","from_infra","to_infra"])
    # additional_lines["from_id"] = additional_lines["from_id"].astype(str).str.strip()
    # additional_lines["to_id"] = additional_lines["to_id"].astype(str).str.strip()
    # nodes_merged2["from_id"] = nodes_merged2["from_id"].astype(str).str.strip()
    
    # additional_lines["geometry"] = additional_lines.progress_apply(
    #                                                 lambda x:add_lines2(
    #                                                 x,nodes_merged,"from_id", "to_id"
    #                                                 ), axis=1)
    # print(additional_lines)

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
    #port_edges["distance_km"] = port_edges.progress_apply(lambda x:modify_distance(x),axis=1)
    port_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_PROVA_NEW.gpkg"),layer="edges",driver="GPKG")
    
    
    # #nodes_merged= add_iso_code(nodes_merged,"country",incoming_data_path)
    nodes_merged["id"] = nodes_merged["id"].str.replace('maritime', 'maritime_')
    nodes_merged["id"] = nodes_merged["id"].str.replace('port', 'port_')
    nodes_merged.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "global_maritime_network_PROVA_NEW.gpkg"),layer="nodes",driver="GPKG")
    
    # africa_nodes = nodes_merged[nodes_merged["continent"] == "Africa"]
    # africa_nodes["Continent_Code"] = "AF"
    # africa_nodes.drop(columns = "index_right", inplace=True)
    # africa_nodes.rename(columns={"iso3":"iso3_old"},inplace=True)
    # africa_nodes= add_iso_code(africa_nodes,"country",incoming_data_path)
    # africa_nodes.drop(columns=["iso3_old"],inplace=True,errors="ignore")

    # print(africa_nodes)
    # print(port_edges)
    
    # G = ig.Graph.TupleList(port_edges.itertuples(index=False), edge_attrs=list(port_edges.columns)[2:])
    # # print (G)

    # all_edges = []
    # africa_nodes = africa_nodes[africa_nodes["Continent_Code"] == "AF"]["id"].values.tolist()

    

      
    



    # for o in range(len(africa_nodes)-1):
    #     origin = africa_nodes[o]
    #     destinations = africa_nodes[o+1:]
    #     e,_ = network_od_path_estimations(G,origin,destinations,"distance","id")
    #     all_edges += e

    # breakpoint()
    

    # all_edges = list(set([item for sublist in all_edges for item in sublist]))
    # all_edges += port_edges[port_edges.index > 9390]["id"].values.tolist()
    # all_edges = list(set(all_edges))
    # # africa_edges = port_edges[port_edges["id"].isin(all_edges)]
    # africa_edges = port_edges[port_edges["id"].isin(all_edges)][["from_id","to_id"]]
    # dup_df = africa_edges.copy()
    # dup_df[["from_id","to_id"]] = dup_df[["to_id","from_id"]]
    # africa_edges = pd.concat([africa_edges,dup_df],axis=0,ignore_index=True)
    # africa_edges = africa_edges.drop_duplicates(subset=["from_id","to_id"],keep="first")
    # africa_edges = gpd.GeoDataFrame(
    #                     pd.merge(
    #                             africa_edges,port_edges,
    #                             how="left",on=["from_id","to_id"]
    #                             ),
    #                     geometry="geometry",crs="EPSG:4326")
    
    # all_nodes = list(set(africa_edges["from_id"].values.tolist() + africa_edges["to_id"].values.tolist()))
    # africa_nodes = africa_nodes[africa_nodes["id"].isin(all_nodes)] 

    

    # africa_edges["from_infra"] = africa_edges.progress_apply(
    #                             lambda x:re.sub('[^a-zA-Z]+', '',x["from_id"]),
    #                             axis=1)
    # africa_edges["to_infra"] = africa_edges.progress_apply(
    #                             lambda x:re.sub('[^a-zA-Z]+', '',x["to_id"]),
    #                             axis=1)
    # africa_edges["id"] = africa_edges.index.values.tolist()
    # africa_edges["id"] = africa_edges.progress_apply(lambda x:f"maritimeroute_{x.id}",axis=1)
    # africa_edges['duplicates'] = pd.DataFrame(
    #                                 np.sort(port_edges[['from_id','to_id']])
    #                                 ).duplicated(keep=False).astype(int)
    # u_df = port_edges[port_edges['duplicates'] == 0]
    # u_df[["to_id","from_id"]] = u_df[["from_id","to_id"]]
    # port_edges = gpd.GeoDataFrame(
    #                 pd.concat([port_edges,u_df],axis=0,ignore_index=True),
    #                 geometry="geometry",crs="EPSG:4326")
    # port_edges.drop("duplicates",axis=1,inplace=True)

    # africa_nodes.to_file(os.path.join(
    #                         processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network_NEW_PROVA.gpkg"),
    #                     layer="nodes",driver="GPKG")
    # africa_edges.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network_NEW_PROVA.gpkg"),
    #                     layer="edges",driver="GPKG")

    # breakpoint()



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)