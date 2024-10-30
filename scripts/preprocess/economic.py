#!/usr/bin/env python
# coding: utf-8
# This file aims to merge the value/weight/utilisations files together with the consolidated ports datasets

import os 
import pandas as pd
import sys
import geopandas as gpd
from utils import *
from tqdm import tqdm
tqdm.pandas()
import geopandas as gpd
from shapely.geometry import Point
from shapely import wkt

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    # Read USGS dataset
    shapefile_path = r"C:\\Users\\engs2461\\Documents\\Git_project\\transport-critical-minerals\\Incoming data\\Africa_GIS Supporting Data\\a. Africa_GIS Shapefiles\\AFR_Infra_Transport_Ports.shp\\AFR_Infra_Transport_Ports.shp"
    USGS_gdf = gpd.read_file(shapefile_path)
    # Rename columns
    USGS_gdf.rename(columns={
        'DsgAttr01': 'Port Commodity ID',
        'DsgAttr02': 'Multiple Commodities',
        'DsgAttr03': 'Commodity Exports',
        'DsgAttr04': 'Commodity Form',
        'DsgAttr05': 'Est. Annual Capacity',
        'DsgAttr06': 'Capacity Units',
        'DsgAttr07': 'Capacity Notes',
        'DsgAttr08': 'Commodity Source',
        'DsgAttr09': 'Commodity Destination'
    }, inplace=True)

    # Read weight and value files
    portsweight_path = os.path.join(incoming_data_path,"Global port supply-chains","Port_statistics","port_locations_weight.csv")
    portsvalue_path = os.path.join(incoming_data_path,"Global port supply-chains","Port_statistics","port_locations_value.csv")
    ports_utilization_path =os.path.join(incoming_data_path,"Global port supply-chains","Port_statistics","port_utilization.csv")
    portsweight= pd.read_csv(portsweight_path)
    portsvalue= pd.read_csv(portsvalue_path)
    ports_utilization=pd.read_csv(ports_utilization_path)


    # Read merged file with iso3
    merged_file_path=os.path.join(processed_data_path,"merged_with_iso2.csv")
    merged_file= pd.read_csv(merged_file_path)


    merged_file.rename(columns={
        'DsgAttr01': 'Port Commodity ID',
        'DsgAttr02': 'Multiple Commodities',
        'DsgAttr03': 'Commodity Exports',
        'DsgAttr04': 'Commodity Form',
        'DsgAttr05': 'Est. Annual Capacity',
        'DsgAttr06': 'Capacity Units',
        'DsgAttr07': 'Capacity Notes',
        'DsgAttr08': 'Commodity Source',
        'DsgAttr09': 'Commodity Destination'
    }, inplace=True)

    columns = merged_file.columns

    for column in columns:
        if column.endswith("_left"):
            left_column = column
            right_column = column.replace("_left", "_right")
            
            if right_column in merged_file.columns:

                merged_file[left_column].fillna(merged_file[right_column], inplace=True)

                merged_file.drop(right_column, axis=1, inplace=True)

    # Delete null columns
    columns_to_remove = ['FeatureUID_left', 'Country_left', 'id_left', 'infra_left', 'name_left', 'iso3_left', 'Continent_Code_left', 'node_id_left']
    merged_file.drop(columns=columns_to_remove, inplace=True)
    
        # Delete null rows

    merged_file=merged_file[merged_file['FeatureUID'] !='LTT02']
    merged_file=merged_file[merged_file['FeatureUID'] !='KMI01']
    merged_file.drop(columns=["Distance__km__Minimum", "Distance__km__Maximum", "GIS_distance"], inplace=True)

    merged_file['iso3'] = merged_file['iso3'].fillna(merged_file['ISO_A3'])
    merged_file['ISO_A3'] = merged_file['ISO_A3'].fillna(merged_file['iso3'])

    merged_file['geometry'] = merged_file['geometry'].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(merged_file, geometry='geometry')


    def nearest_distance(row, gdf):
        current_point = row['geometry']
        
        # distance between current points with all points
        distances = gdf['geometry'].distance(current_point)
        
        # delete itself
        distances = distances[distances > 0]
        
        return distances.min()



    gdf['nearest_distance'] = gdf.apply(nearest_distance, gdf=gdf, axis=1)


    def nearest_distance(row, gdf):
        current_point = row['geometry']
        distances = gdf['geometry'].distance(current_point)
        distances = distances[distances > 0]
        
        # return index of the nearest row along with the distance
        min_distance = distances.min()
        nearest_index = distances.idxmin()
        
        return nearest_index, min_distance


    # Step 1: Compute nearest distances and indices
    gdf['nearest_info'] = gdf.apply(nearest_distance, gdf=gdf, axis=1)

    # Step 2: Filter rows where distance is less than 0.03
    close_rows = gdf[gdf['nearest_info'].apply(lambda x: x[1] < 0.03)]


    count_less_than_0_03 = (gdf['nearest_distance'] < 0.03).sum()
    print(count_less_than_0_03)



    portsweight.rename(columns={'import':'import flow in USD',
                            'export':'export flow in USD',
                            'trans':'transhipment in USD',
                            'throughput': 'total throughput in USD'},inplace=True)


    portsweight.rename(columns={'import':'import flow in tonnes',
                            'export':'export flow in tonnes',
                            'trans':'transhipment in tonnes',
                            'throughput': 'total throughput in tonnes'},inplace=True)

    ports_weightvalues = pd.merge(portsweight, portsvalue, on='id')

    # Merge weight/values/
    ports_weightvalues_util = pd.merge(ports_weightvalues, ports_utilization, on='id')
    ports_weightvalues=ports_weightvalues_util
    cols_to_remove = [col for col in ports_weightvalues.columns if col.endswith("_y")]
    ports_weightvalues.drop(columns=cols_to_remove, inplace=True)
    ports_weightvalues.columns = ports_weightvalues.columns.str.replace('_x', '')
    ports_weightvalues_path=os.path.join(processed_data_path,'ports_weightvalues.csv')
    ports_weightvalues.to_csv(ports_weightvalues_path,index=True)


    ports_weightvalues_unique = ports_weightvalues.drop_duplicates(subset='id', keep='first')

    result = merged_file.merge(ports_weightvalues_unique, on='id', how='left')
    missing_coords_df = result_df[result_df['Latitude'].isnull() | result_df['Longitude'].isnull()]
    missing_coords_df=missing_coords_df[missing_coords_df['lat'].isnull() |missing_coords_df['lon'].isnull()]
    # save the output files
    merged_file_path=os.path.join(processed_data_path,'merged2.csv')
    result_path=os.path.join(processed_data_path,'economic results2.csv')
    missing_coords_path=os.path.join(processed_data_path,'missing_coords.csv')
    merged_file.to_csv(merged_file_path, index=False)
    result.to_csv(result_path, index=False)
    missing_coords_df.to_csv(missing_coords_path, index=False)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)