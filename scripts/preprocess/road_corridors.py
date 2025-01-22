#!/usr/bin/env python
# coding: utf-8
import sys
import os
import re
import json
import pandas as pd
import igraph as ig
import geopandas as gpd
from utils_new import *
from tqdm import tqdm
tqdm.pandas()



def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
   
    # Read the road edges data for Africa

    road_id_column = "id"
    node_id_column = "id"
    road_type_column = "tag_highway"
    main_road_types = ["trunk","motorway","primary","secondary"]
    # """
    # Assuming that the starting point is the road network with the main highways
    # Because main corridors should be along main highways
    # """
    
    road_edges = gpd.read_parquet(os.path.join(
                            incoming_data_path,
                            "africa_roads",
                            "edges_with_topology.geoparquet"))
    road_nodes = gpd.read_parquet(os.path.join(
                            incoming_data_path,
                            "africa_roads",
                            "nodes_with_topology.geoparquet"))
    road_edges = road_edges.to_crs(epsg=epsg_meters)
    road_nodes = road_nodes.to_crs(epsg=epsg_meters) 
    #main_edges = gpd.read_parquet(os.path.join(
                                # processed_data_path,
                                # "infrastructure",
                                # "africa_roads_edges.geoparquet"))
    
    # """
    # Read the file with the start and end points of the corridor
    # Example data: (can include more column names with values, but these are the minimum)
    # start_location | end_location | corridor_name | start_latitude | start_longitude | end_latitude | end_longitude
    # """
    
    start_latitude_column = "start_latitude"
    start_longitude_column = "start_longitude"
    end_latitude_column = "end_latitude"
    end_longitude_column = "end_longitude"
    start_location_column = "start_location"
    end_location_column = "end_location"
    corridor_name_column = "corridor_name"

    corridor_df = pd.read_excel(os.path.join(
                            incoming_data_path,
                            "road_corridors.xlsx"))
    corridor_df2 = corridor_df.copy()
    columns = [
                (
                    "source" , start_location_column , start_longitude_column , start_latitude_column, corridor_name_column 
                )
            ] 
    
    columns2 = [            
                (
                    "target" , end_location_column , end_longitude_column , end_latitude_column, corridor_name_column
                )
            ]
    
    
    for idx, (st,l_id, lon, lat, c1) in enumerate(columns):
       
        corridor_df["geometry"] = gpd.points_from_xy(
                                                        corridor_df[lon],
                                                        corridor_df[lat]
                                                        )
       

        corridor_df = gpd.GeoDataFrame(corridor_df,geometry="geometry",crs="EPSG:4326")
        corridor_df = corridor_df.to_crs(epsg=epsg_meters)

        
        corridor_df = gpd.sjoin_nearest(corridor_df[[l_id,c1,"geometry"]],
                                            road_nodes[["id","geometry"]],
                                            how="left").reset_index()
        
        
        corridor_df.rename(columns={"id":st},inplace=True)

        
        corridor_df.drop(["geometry","index_right"],axis=1,inplace=True)


    print(corridor_df)


    for idx2, (st2,l_id2, lon2, lat2, c2) in enumerate(columns2):
        corridor_df2["geometry"] = gpd.points_from_xy(
                                                        corridor_df2[lon2],
                                                        corridor_df2[lat2]
                                                        )
       

        corridor_df2 = gpd.GeoDataFrame(corridor_df2,geometry="geometry",crs="EPSG:4326")
        corridor_df2 = corridor_df2.to_crs(epsg=epsg_meters)

        
        corridor_df2 = gpd.sjoin_nearest(corridor_df2[[l_id2,c2,"geometry"]],
                                            road_nodes[["id","geometry"]],
                                            how="left").reset_index()
        
        
        corridor_df2.rename(columns={"id":st2},inplace=True)

        corridor_df2.drop(["geometry","index_right"],axis=1,inplace=True)

    print(corridor_df2)
         
    corridor_df = corridor_df.join(corridor_df2, lsuffix='_start', rsuffix='_end')
    print("corridor_df")
    print(corridor_df)

    corridor_df.drop(["index_start","index_end","corridor_name_start"],axis=1,inplace=True)
    corridor_df.rename(columns={"corridor_name_end":"corridor_name"}, inplace=True)
    # corridor_df = pd.concat([corridor_df, corridor_df2]axis=0)
    # corridor_df = corridor_df.reindex(columns=['start_location','source','end_location','target','corridor_name'])


    graph = create_igraph_from_dataframe(
                    road_edges[["from_id","to_id",road_id_column,"length_m"]])
    
    
    roads_with_corridors = []
    corridor_name_column = "corridor_name"

    for row in corridor_df.itertuples():            
        path = graph.get_shortest_paths(
                                        row.source, 
                                        row.target, 
                                        weights="length_m",output="epath")[0]

        connected_roads = []
        if path:
            for n in path:
                connected_roads.append(graph.es[n]["id"])
        corridor_names = [getattr(row,corridor_name_column)]*len(connected_roads)
        roads_with_corridors += list(zip(connected_roads,corridor_names))

    roads_with_corridors = pd.DataFrame(roads_with_corridors,columns=["id","corridor_name"])
    

                                 

    # Could be possible that a road might have multiple corridors
    roads_with_corridors = roads_with_corridors.groupby("id").agg(
                                                            {
                                                                "corridor_name":list
                                                            }
                                                            ).reset_index()
    
    

    # This will covert values from a list to a string seperated by / 
    # Example: ['a','b','c'] becomes 'a/b/c' 
    roads_with_corridors["corridor_name"] = roads_with_corridors["corridor_name"].progress_apply(lambda a: "/".join(list(set(a))))
                         
    
    road_edges = pd.merge(road_edges,roads_with_corridors,how="left",on=["id"])
    
    connected_nodes = list(set(road_edges.from_id.values.tolist() + road_edges.to_id.values.tolist()))
    nearest_nodes = road_nodes[road_nodes[node_id_column].isin(connected_nodes)]
    nearest_nodes.rename(columns={node_id_column:"id"},inplace=True)
    nearest_nodes = nearest_nodes.to_crs(epsg=4326)

    """Find the network components
    """
    edges = road_edges[[
            'from_id','to_id','id','osm_way_id','from_iso_a3','to_iso_a3',
            'tag_highway', 'tag_surface','tag_bridge','tag_maxspeed','tag_lanes',
            'bridge','paved','material','lanes','width_m','length_m','asset_type','corridor_name','geometry']]
    edges, nearest_nodes = components(edges,nearest_nodes,node_id_column="id")

    edges["border_road"] = np.where(edges["from_iso_a3"] == edges["to_iso_a3"],0,1)

    nearest_nodes = gpd.GeoDataFrame(nearest_nodes,
                    geometry="geometry",
                    crs="EPSG:4326")

    edges = gpd.GeoDataFrame(edges,
                    geometry="geometry",
                    crs="EPSG:4326")

    nearest_nodes.to_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes_PROVA.geoparquet"))
    edges.to_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_PROVA.geoparquet"))
   
    
    # Write  the file back to the original if you are feeling confident!
    # Otherwise rename
    # roads_with_corridors.to_csv(
    #                         os.path.join(
    #                                 processed_data_path,
    #                                 "infrastructure",
    #                                 "roads_corridors_PROVA.csv"
    #                                 )
    #                     )
    # road_edges.to_parquet(
    #                         os.path.join(
    #                                 processed_data_path,
    #                                 "infrastructure",
    #                                 "africa_roads_edges_PROVA.geoparquet"
    #                                 )
    #                     )
   






if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)