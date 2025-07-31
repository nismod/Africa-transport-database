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
import country_converter as coco

tqdm.pandas()

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
    cutoff_distance = 6600 # We assume airports within 6.6km are the same

    df_airports_flow = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_airport_network.gpkg"), layer="edges")
    
    df_airports_nodes = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_airport_network.gpkg"), layer="nodes")
    
    
    df_airports_flow= df_airports_flow.to_crs(epsg=4326)
    df_airports_flow = df_airports_flow.drop_duplicates(subset=['from_id', 'to_id'], keep='first')
    df_airports_nodes = df_airports_nodes.drop(['from_iso3','to_iso3'], axis=1, inplace=True)
    id_to_geom = df_airports_nodes.set_index('id')['geometry'].to_dict()

    def create_linestring(row):
            from_geom = id_to_geom.get(row['from_id'])
            to_geom = id_to_geom.get(row['to_id'])
            if from_geom and to_geom:
                return LineString([from_geom, to_geom])
            return None

    # Apply the function to each row in flows
    df_airports_flow['geometry'] = df_airports_flow.apply(create_linestring, axis=1)

    # Convert to GeoDataFrame
    df_airports_flow = gpd.GeoDataFrame(df_airports_flow, geometry='geometry', crs="EPSG:4326")
    
    df_airports_nodes.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network_last.gpkg"),
                        layer="nodes",driver="GPKG")
    df_airports_flow.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_airport_network_last.gpkg"),
                        layer="edges",driver="GPKG")
    


    
   
    

    


    # df_airports_flow= add_iso_code(df_airports_flow,"Country1",incoming_data_path)
    # df_airports_flow.rename(columns={"iso3": "iso3_1"},inplace=True)  
    # df_airports_flow.drop(columns=["index_right"], inplace = True)  
    
    # df_airports_flow = add_iso_code(df_airports_flow,"Country2",incoming_data_path)
    # df_airports_flow.rename(columns={"iso3": "iso3_2"},inplace=True) 
    
    # df_airports_flow.drop(columns = ["level_0"], inplace=True)

    # cc = coco.CountryConverter()
    # df_airports_flow["continent1"]  = cc.pandas_convert(df_airports_flow["Country1"], to='Continent')  
    # df_airports_flow["continent2"]  = cc.pandas_convert(df_airports_flow["Country2"], to='Continent')  

    # print(df_airports_flow)
    

    # df_airports_nodes["geom"] = gpd.points_from_xy(
    #                         df_airports_nodes["Airport1Longitude"],df_airports_nodes["Airport1Latitude"])
    # df_airports_nodes.drop("geometry",axis=1,inplace=True)
    # df_airports_nodes.rename(columns={"geom":"geometry"},inplace=True)

    # df_airports_nodes = gpd.GeoDataFrame(df_airports_nodes,geometry="geometry",crs="EPSG:4326")

    # df_airports_nodes= df_airports_nodes.to_crs(epsg=4326)
    
    # df_airports_nodes = add_iso_code(df_airports_nodes,"Country Name",incoming_data_path)

    # df_airports_nodes["infra"] = "airport"

    # df_airports_nodes["continent"]  = cc.pandas_convert(df_airports_nodes["Country Name"], to='Continent')  


    # print(df_airports_nodes)
    

    
    
    
    
    # Get the airports for Africa


    # airport_edges = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_airport_network.gpkg"),layer="edges")
    # airport_nodes = gpd.read_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "global_airport_network.gpkg"),layer="nodes")
   
    # africa_airports = airport_nodes[airport_nodes["continent"] == "Africa"]
   
    # africa_air_tracks = airport_edges[airport_edges["continent1" or "continent2"] == "Africa"]
    
    # print(africa_airports)
    
    
    # df_airports_nodes.to_file(os.path.join(processed_data_path,
    #                         "infrastructure",
    #                         "africa_airport_network.gpkg"),
    #                     layer="nodes",driver="GPKG")


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)