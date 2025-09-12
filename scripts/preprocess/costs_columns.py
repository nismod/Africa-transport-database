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

    # maritime_nodes = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network.gpkg"),
    #                         layer="nodes")
    
    # maritime_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network.gpkg"),
    #                         layer="edges")
    # multimodal_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_multimodal.gpkg"),
    #                         layer="edges")
    # print(multimodal_edges.columns)
    # multimodal_edges = multimodal_edges[["id","from_id","to_id","from_infra","to_infra","from_iso3","to_iso3","link_type","length_m","geometry"]]

    
   

    # maritime_edges["new_id"] = maritime_edges.progress_apply(lambda x:f"maritimeroute_{x.id}",axis=1)
    
    # maritime_nodes = maritime_nodes.drop(columns={"id"})
    #  maritime_nodes = maritime_nodes.rename(columns={"new_id":"id"})

    # maritime_nodes["id"] = maritime_nodes["id"].str.replace('maritime', 'maritime_')
    # maritime_nodes["id"] = maritime_nodes["id"].str.replace('port', 'port_')
    # maritime_edges["from_id"] = maritime_edges["from_id"].str.replace('maritime', 'maritime_')
    # maritime_edges["to_id"] = maritime_edges["to_id"].str.replace('maritime', 'maritime_')
    # maritime_edges["from_id"] = maritime_edges["from_id"].str.replace('port', 'port_')
    # maritime_edges["to_id"] = maritime_edges["to_id"].str.replace('port', 'port_')


    # maritime_edges["new_from_id"] = maritime_edges.progress_apply(lambda x:f"maritime_{x.from_id}",axis=1)
    # maritime_edges["new_to_id"] = maritime_edges.progress_apply(lambda x:f"maritime_{x.to_id}",axis=1)
    
    # print(maritime_edges)

    # maritime_edges = maritime_edges.drop(columns={"to_id","id"})
    # maritime_edges = maritime_edges.drop(columns={"length_km"})
    # maritime_edges = maritime_edges.rename(columns={"length_m":"length_km"})

    # maritime_nodes = maritime_nodes[["id","iso3","name","infra","geometry"]]
    # maritime_edges = maritime_edges[["id","from_id","to_id","from_infra","to_infra","distance","length","geometry"]]
    # print(maritime_edges)
    # print(maritime_nodes)

    roads_nodes = gpd.read_parquet(os.path.join(
                 processed_data_path,
                 "infrastructure",
                 "africa_roads_nodes_FINAL.geoparquet"
                 ))
    roads_edges = gpd.read_parquet(os.path.join(
                 processed_data_path,
                 "infrastructure",
                 "africa_roads_edges_FINAL.geoparquet"
                 ))
   
    roads_nodes = roads_nodes.rename(columns={"iso_a3":"iso3"})

    roads_edges = roads_edges.sort_values(by='id')
    mask = roads_edges['lanes'] > 8


    for i in roads_edges.index[mask]:  # Iterate over indices where "lanes" > 8
       if i > 0:  # Ensure it's not the first row
          roads_edges.at[i, 'lanes'] = roads_edges.at[i - 1, 'lanes']
          

    print(roads_edges)
    print("Max lanes:", max(roads_edges['lanes']))
                
             
    # IWW_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_iww_network.gpkg"),
    #                         layer="edges")
    # IWW_nodes = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_iww_network.gpkg"),
    #                         layer="nodes")
    
     
    # IWW_edges = IWW_edges[["id","from_id","to_id","from_iso3", "to_iso3","from_infra","to_infra","component","length_m","geometry"]]
    # IWW_nodes = IWW_nodes[["id","iso3","name","infra","component","geometry"]]
    
    

    # airport_nodes = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_airport_network.gpkg"),
    #                         layer="nodes")
    # airport_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_airport_network.gpkg"),
    #                         layer="edges")
    
    
    # # print(airport_edges.columns)
    # airport_edges = airport_edges.rename(columns={"Name":"name1","NAme_1":"name2"})
    
    # airport_edges = airport_edges.drop(columns={"index"})
    

    
    # print(airport_edges.columns)


    # print(airport_nodes.columns)
     
    # airport_nodes = airport_nodes.rename(columns={"Name":"name", "Country Name":"country_name"})
    # airport_nodes = airport_nodes.drop(columns={"Orig"})
  
    # airport_edges = airport_edges.rename(columns={"iso3_1":"from_iso3","iso3_2":"to_iso3"})
    
    # print(airport_nodes.columns)

    # print(roads_edges.columns)
    roads_edges = roads_edges.rename(columns={"from_iso_a3":"from_iso3", "to_iso_a3":"to_iso3"})
    roads_edges = roads_edges[["id","from_id","to_id","from_iso3","to_iso3","component","border_road", "corridor_name","length_m","osm_way_id","tag_highway","tag_surface","tag_bridge", "tag_maxspeed","tag_lanes","bridge","paved","material","lanes","asset_type","geometry"]]
    # print(roads_edges.columns)

    print(roads_nodes.columns)
    roads_nodes = roads_nodes[["id","iso3","component","geometry"]]
    

    # Save files
    # multimodal_edges.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_multimodal.gpkg"),
    #                         layer="edges",driver="GPKG")

    # rail_edges.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_railways_network.gpkg"),
    #                         layer="edges",driver="GPKG")
    # # rail_nodes.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_railways_network.gpkg"),
    #                         layer="nodes",driver="GPKG")
    
    

    # IWW_edges.to_file(os.path.join(processed_data_path,
    #                                "infrastructure",
    #                                "africa_iww_network.gpkg"),
    #                   layer="edges",driver="GPKG")
    # IWW_nodes.to_file(os.path.join(processed_data_path,
    #                                "infrastructure",
    #                                "africa_iww_network.gpkg"),
    #                   layer="nodes",driver="GPKG")
    
    # airport_nodes.to_file(os.path.join(processed_data_path,
    #                                    "infrastructure",
    #                                    "africa_airport_network.gpkg"),
    #                       layer="nodes",driver="GPKG")
    # # airport_edges.to_file(os.path.join(processed_data_path,
    # #                                   "infrastructure",
    #                                   "africa_airport_network.gpkg"),
    #                         layer="edges",driver="GPKG")
    
    roads_edges = gpd.GeoDataFrame(roads_edges,
                    geometry="geometry",
                    crs="EPSG:4326")
    roads_nodes = gpd.GeoDataFrame(roads_nodes,
                    geometry="geometry",
                    crs="EPSG:4326")

    roads_nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_network.gpkg"),
                             layer="nodes",driver="GPKG")
    roads_edges.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_network.gpkg"),
                             layer="edges",driver="GPKG")
    
    roads_nodes.to_parquet(os.path.join(
                 processed_data_path,
                 "infrastructure",
                 "africa_roads_nodes_FINAL.geoparquet"
                 ))
    roads_edges.to_parquet(os.path.join(
                 processed_data_path,
                 "infrastructure",
                 "africa_roads_edges_FINAL.geoparquet"
                 ))
    
    # maritime_nodes.to_file(os.path.join(processed_data_path,
    #                                 "infrastructure",
    #                                 "africa_maritime_network.gpkg"),
    #                         layer="nodes",driver="GPKG")
    # maritime_edges.to_file(os.path.join(processed_data_path,
    #                                 "infrastructure",
    #                                 "africa_maritime_network.gpkg"),
    #                         layer="edges",driver="GPKG")
    

    



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)

    