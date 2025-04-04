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

    
    roads_df = gpd.read_parquet(os.path.join(
                 processed_data_path,
                 "infrastructure",
                 "africa_roads_edges_FINAL.geoparquet"
                 ))
    rail_df = gpd.read_file(os.path.join(
                 processed_data_path,
                 "infrastructure",
                 "africa_railways_network.gpkg"
                 ), layer = 'edges')
    




    

    # Convert length from meters to kilometers
    rail_df['length_km'] = rail_df['length_m'] / 1000
    grouped_data_rail = rail_df.groupby(['status'])['length_km'].sum().reset_index()
    grouped_data_rail['percentage'] = (grouped_data_rail['length_km'] / grouped_data_rail['length_km'].sum()) * 100
    print(grouped_data_rail)
    # Save the grouped data to a CSV file
    grouped_data_rail.to_csv(os.path.join(
        processed_data_path,
        "infrastructure",
        "rail_stats.csv"
    ), index=False)

    # Convert length from meters to kilometers
    roads_df['length_km'] = roads_df['length_m'] / 1000

    # Split the 'corridor_name' by '/' to account for multiple corridors
    roads_df['corridor_name'] = roads_df['corridor_name'].str.split('/')

    # Explode the data to separate overlapping corridors into individual rows
    gdf_exploded = roads_df.explode('corridor_name', ignore_index=True)
    # Define valid highway types
    valid_highways = ['trunk', 'motorway', 'primary', 'secondary', 'tertiary']

    # Replace values not in the valid list with 'Other'
    gdf_exploded.loc[~gdf_exploded['tag_highway'].isin(valid_highways), 'tag_highway'] = 'Other'

    grouped_data = gdf_exploded.groupby([ 'corridor_name','paved'], as_index=False).agg({'length_km': 'sum'})
    
    # Calculate the percentage
    
    print(grouped_data)

    grouped_data.to_csv(os.path.join(
        processed_data_path,
        "infrastructure",
        "paved_stats.csv"
    ), index=False)

    
    

    
    # Save files
    
   
    



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)

    