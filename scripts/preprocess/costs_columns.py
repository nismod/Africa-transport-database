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

    # maritime_nodes = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_maritime_network.gpkg"),
    #                         layer="nodes")
    
    # print(maritime_nodes.columns)
    # maritime_nodes = maritime_nodes.drop(columns = {"Continent_Code"})
    # print(maritime_nodes.columns)


    roads_nodes = gpd.read_file(os.path.join(incoming_data_path,
                            "africa_roads",
                            "africa_main_roads.gpkg"),
                            layer="nodes")
    roads_edges = gpd.read_file(os.path.join(incoming_data_path,
                            "africa_roads",
                            "africa_main_roads.gpkg"),
                            layer="edges")
    
    # print(roads_nodes.columns)
    # roads_nodes = roads_nodes.rename(columns={"iso_a3":"iso3"})
    # print(roads_nodes.columns)

    # print(roads_edges.columns)
    # roads_edges = roads_edges.rename(columns={"from_iso_a3":"from_iso3","to_iso_a3":"to_iso3"})
    # roads_edges = roads_edges.drop(columns={"tag_highway", "tag_surface", "tag_bridge", "tag_maxspeed", "tag_lanes"})
    # print(roads_edges.columns)

    airport_nodes = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_airport_network.gpkg"),
                            layer="nodes")
    airport_edges = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_airport_network.gpkg"),
                            layer="edges")
    
    print(airport_edges.columns)
     
    # airport_edges = airport_edges.rename(columns={"Name":"name1","NAme_1":"name2"})
    # airport_edges = airport_edges.drop(columns={"index_right","Country Na","Airport1La","Airport1Lo","Airport2La","Airport2Lo"})

    
    # print(airport_edges.columns)


    # print(airport_nodes.columns)
     
    # airport_nodes = airport_nodes.rename(columns={"Name":"name", "Country Name":"country_name"})
    # airport_nodes = airport_nodes.drop(columns={"index","continent","index_right","Airport1Latitude","Airport1Longitude",})

    
    # print(airport_nodes.columns)
    
    # IWW_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_iww_network.gpkg"),
    #                         layer="edges")
    
    # print(IWW_edges.columns)
     
    # IWW_edges = IWW_edges.rename(columns={"from_iso_a3":"from_iso3","to_iso_a3":"to_iso3"})
    
    
    # print(IWW_edges.columns)



    # # COSTS CALCULTATION
    
    # # RAILWAYS -----------------------------------------------------------------------------------------------------------------------
        
    rail_edges = gpd.read_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_railways_network.gpkg"),
                            layer="edges")
    
    print(rail_edges.columns)

    #construction/reconstruction cost

    rail_edges["cost_2010_USD"] = rail_edges["length_m"]*4500 
    rail_edges["cost_2024_USD"] = rail_edges["length_m"]*4500*pow(1.03,14) # assuming 3% discount rate
    

   
    # # ROADS -----------------------------------------------------------------------------------------------------------------------

    # construction

    roads_edges["con_cost_2010_USD"] = roads_edges["length_m"]*roads_edges["lanes"]*1200 
    roads_edges["con_cost_2024_USD"] = roads_edges["length_m"]*roads_edges["lanes"]*1200*pow(1.03,14) # assuming 3% discount rate

    # reconstruction/upgrade

    roads_edges["rec_cost_2024_USD"] = roads_edges["length_m"]*roads_edges["lanes"]*200*pow(1.03,14) # assuming 3% discount rate

   # # AIRPORTS -----------------------------------------------------------------------------------------------------------------------

    # construction

    airport_nodes["con_cost_2014_MUSD"] = airport_nodes["TotalSeats"]*449.24*pow(10,-6) 


    # Save files


    rail_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_railways_network.gpkg"),
                            layer="edges",driver="GPKG")
    

    # IWW_edges.to_file(os.path.join(processed_data_path,
    #                                "infrastructure",
    #                                "africa_iww_network.gpkg"),
    #                   layer="edges",driver="GPKG")
    
    airport_nodes.to_file(os.path.join(processed_data_path,
                                       "infrastructure",
                                       "africa_airport_network.gpkg"),
                          layer="nodes",driver="GPKG")
    # airport_edges.to_file(os.path.join(processed_data_path,
    #                                   "infrastructure",
    #                                   "africa_airport_network.gpkg"),
    #                         layer="edges",driver="GPKG")
    
    roads_nodes.to_file(os.path.join(incoming_data_path,
                                     "africa_roads",
                                     "africa_main_roads.gpkg"),
                        layer="nodes",driver="GPKG")
    roads_edges.to_file(os.path.join(incoming_data_path,
                                     "africa_roads",
                                    "africa_main_roads.gpkg"),
                        layer="edges",driver="GPKG")
    
    # maritime_nodes.to_file(os.path.join(processed_data_path,
    #                                 "infrastructure",
    #                                 "africa_maritime_network.gpkg"),
    #                         layer="nodes",driver="GPKG")
    

    



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)

    