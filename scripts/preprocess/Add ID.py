#!/usr/bin/env python
# coding: utf-8

# Aim: to complete the attribution table for 'ports' in the 'africa_ports_modified.gpkg' file, specifically adding the 'node_id', 'name', and 'ISO3' fields. 
# The output file will be named 'output.gpkg' and will contain two layers: 'nodes' and 'edges'."


import geopandas as gpd
from shapely.ops import nearest_points
import os
import pandas as pd
import sys
import re
from utils import *
from tqdm import tqdm
tqdm.pandas()

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']

    # 1. Read files 
    # (1) Read the non-intersected gpkg
    non_intersected = gpd.read_file(os.path.join(processed_data_path,
                                        "non_intersected_from_merged.gpkg"))
    # (2) Read the merged gpkg 
    #nodes
    df = gpd.read_file(os.path.join(processed_data_path,"africa_ports_modified.gpkg"),layer="nodes")
    # lines
    df_lines = gpd.read_file(os.path.join(processed_data_path,"africa_ports_modified.gpkg"), layer="edges")

    # (3) Read the country boundary and extracted the ISO3 code
    path_to_shp = os.path.join(incoming_data_path,"ports","ne_110m_admin_0_countries","ne_110m_admin_0_countries.shp")
    world = gpd.read_file(path_to_shp)

    #（4）Read merged file with iso3
    merged_file_path=os.path.join(processed_data_path,"merged_with_iso2.csv")
    merged_file= pd.read_csv(merged_file_path)
    
    #2. Fill in the blank values in the column of node_id

    for idx, row in df[df['node_id'].isnull()].iterrows():
        # Find the coresponding rows ion the non_intersected datasets
        intersected_rows = non_intersected[non_intersected.intersects(row['geometry'])]
   
        # If an intersection exists, take the 'FeatureUID' of the first intersection and assign it to the corresponding 'node_id' of df.
        if not intersected_rows.empty:
            df.at[idx, 'node_id'] = intersected_rows.iloc[0]['FeatureUID']

    #3. Keep the node_id as the unique ID
    df.drop_duplicates(subset='node_id', inplace=True, keep='first')
    print("Duplicates in df:", df[df.duplicated(subset='node_id', keep=False)]['node_id'])
    print("Duplicates in merged_file:", merged_file[merged_file.duplicated(subset='node_id', keep=False)][['node_id']])



    #4. Add the ISO3 valyes
    # (1) Add from the "merged_with_iso2.csv"
    merged_file = merged_file.loc[:,~merged_file.columns.duplicated()]
    merged_result = df.merge(merged_file[['node_id', 'ISO_A3']], on='node_id', how='left')
    merged_result['iso3'].fillna(merged_result['ISO_A3'], inplace=True)
    merged_result.drop(columns=['ISO_A3'], inplace=True)  

    # (2) Extract the ISO number from world boundary file
    merged_result = merged_result.merge(world[['ISO_A3', 'geometry']], left_on='iso3', right_on='ISO_A3', how='left')

    # Delete the duplicated geometry columns
    merged_result.drop(columns='geometry_y', inplace=True)
    merged_result.rename(columns={'geometry_x': 'geometry'}, inplace=True)
    merged_result.drop(columns='ISO_A3')



    #5. Add values to the name column
    # Extract these rows with name-null from merged_result
    for idx, row in merged_result[merged_result['name'].isnull()].iterrows():
        
        # Accoding to node_id, extraxct rows from merged_file
        related_row = merged_file[merged_file['node_id'] == row['node_id']]
        
        if not related_row.empty:
            related_row = related_row.iloc[0]  
            
            # if  FeatureNam is not null，
            if pd.notnull(related_row['FeatureNam']):
                merged_result.at[idx, 'name'] = related_row['FeatureNam']
                
            # if  FeatureNamis numm but the column "name" ios not null
            elif pd.notnull(related_row['name']):
                merged_result.at[idx, 'name'] = related_row['name']
                
            # if both FeatureNam and name is null，use the 'Project_name' to update
            else:
                merged_result.at[idx, 'name'] = related_row['Project_name']

    #6. Add values to the 'infra' column and 'Continent_Code' columns
    merged_result.loc[merged_result['infra'].isnull(), 'infra'] = 'ports'
    merged_result.drop(columns='ISO_A3',inplace= True)
    merged_result.loc[merged_result['infra'] == 'ports', 'id'] = merged_result['node_id']
    merged_result['Continent_Code'] = 'AF'

    #7. Add values to the 'infra' column and 'Continent_Code' columns
    condition = (merged_result['infra'] == 'ports') & (merged_result['iso3'].isnull())
    ports_missing_iso3 = merged_result[condition]

    #8. Add values to the blank rows of 'iso3' columns
    for idx, row in merged_result[condition].iterrows():
        point = row['geometry']
        # Find the nearest country
        distances = world['geometry'].apply(lambda country: country.distance(point))
        nearest_country = world.loc[distances.idxmin(), 'ISO_A3']
        merged_result.loc[idx, 'iso3'] = nearest_country


    #8. Generate the new ouput
    gdf_merged_result = gpd.GeoDataFrame(merged_result, geometry='geometry')
    df_lines.to_file(os.path.join(processed_data_path,"output.gpkg"), layer="edges", driver="GPKG")
    gdf_merged_result.to_file(os.path.join(processed_data_path,"output.gpkg"), layer="nodes", driver="GPKG")

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)