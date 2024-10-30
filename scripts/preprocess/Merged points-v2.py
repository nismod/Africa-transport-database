#!/usr/bin/env python
# coding: utf-8
# (1) Merge three datasets; (2)Add ISO3 (3) extraxt non_intersected
import os
import geopandas as gpd
import pandas as pd
from utils import *
from tqdm import tqdm

def main(config):
    # Get the data from the config.json
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    # 1. Read USGS data, Africa prots dataset,African development corriodor datasets
    path = incoming_data_path
    df_ports_shp = gpd.read_file(os.path.join(
                                incoming_data_path,
                                "Africa_GIS Supporting Data",
                                "a. Africa_GIS Shapefiles",
                                "AFR_Infra_Transport_Ports.shp",
                                "AFR_Infra_Transport_Ports.shp"))
    # This contains some wrong geometry, which we will have to convert to Point from Latitude and Longitude values
    df_ports_shp["geom"] = gpd.points_from_xy(
                            df_ports_shp["Longitude"],df_ports_shp["Latitude"])
    df_ports_shp.drop("geometry",axis=1,inplace=True)
    df_ports_shp.rename(columns={"geom":"geometry"},inplace=True)
    df_ports_shp = gpd.GeoDataFrame(df_ports_shp,geometry="geometry",crs="EPSG:4326")

    # We will read the global ports dataset
    df_ports = gpd.read_file(os.path.join(incoming_data_path,
                                    "ports",
                                    "nodes_maritime.gpkg"))
    # Read the Africa Corridor data
    df_corridor = gpd.read_file(os.path.join(
                                incoming_data_path,
                                "africa_corridor_developments",
                                "AfricanDevelopmentCorridorDatabase2022.gpkg" 
                                ),layer='point')
    
    # Filter corridor data for "Port" Infrastructure development type
    # Also remove the Inland port, which is far away from the Maritime ports
    # Also remove the Conarky Port which is not properly geolocated in the data
    df_corridor = df_corridor[(
                    df_corridor["Infrastructure_development_type"] == "Port"
                    ) & ~(df_corridor["Project_code"].isin(["LTT0002","KMI0001","DLC0002"]))]
    # Create FeatureUID according to Project_code
    # df_corridor = df_corridor.copy()
    df_corridor.loc[:, 'FeatureUID'] = df_corridor['Project_code'].str[:3] + df_corridor['Project_code'].str[-2:]
    
    
    # Filter africa_ports for "port" infra
    df_africa_ports_proj = df_ports[df_ports["infra"] == "port"]
    
    # Set CRS as 'EPSG:3395' for estimating the distances in meters
    proj_crs = "EPSG:3395"
    df_ports_shp_proj = df_ports_shp.to_crs(proj_crs)
    df_africa_ports_proj = df_africa_ports_proj.to_crs(proj_crs)
    df_corridor_proj = df_corridor.to_crs(proj_crs)
    
    # 3. Set buffer
    buffer_distance = 0.03 * 111000  # 3.3km
    df_ports_shp_proj['geometry'] = df_ports_shp_proj.buffer(buffer_distance)
    df_africa_ports_proj['geometry'] = df_africa_ports_proj.buffer(buffer_distance)
    df_corridor_proj['geometry'] = df_corridor_proj.buffer(buffer_distance)
    
    # 4. Spatial join (datasets)
    # With the buffer we are actually assuming that ports which are within 6.6km of each other are same

    # First find the common port between the USGS and the Global ports data  
    merged_shp_gpkg = gpd.sjoin(df_ports_shp_proj, 
                            df_africa_ports_proj, 
                            how="inner", predicate="intersects", lsuffix='_gpkg', rsuffix='_africa')
    merged_shp_corridor = gpd.sjoin(df_africa_ports, corridor_port_data, how="inner", predicate="intersects", lsuffix='_africa', rsuffix='_corridor')
    merged_three = gpd.sjoin(merged_shp_gpkg, merged_shp_corridor, how="inner", predicate="intersects")
    # 5. Delete the duplicates
    duplicates_gpkg = merged_shp_gpkg[merged_shp_gpkg.duplicated(subset='geometry', keep=False)]
    print("Duplicated number of merged_shp_gpkg：", len(duplicates_gpkg))
    
    duplicates_corridor = merged_shp_corridor[merged_shp_corridor.duplicated(subset='geometry', keep=False)]
    print("Duplicated numbers of merged_shp_corridor：", len(duplicates_corridor))
    
    merged_shp_gpkg.drop_duplicates(subset='geometry', inplace=True)
    
    # 6. Combine all datesets
    merged_all = pd.concat([merged_shp_gpkg, merged_shp_corridor, merged_three, df_ports_shp_proj, df_africa_ports, corridor_port_data], ignore_index=True)
    merged_all_unique = merged_all.drop_duplicates(subset='geometry', keep='first')
    
    merged_all = merged_all_unique.copy()
    merged_all['geometry'] = merged_all['geometry'].centroid
    
    # Insert countries' boundary
    path_to_shp = f"{path}/ports/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
    world = gpd.read_file(path_to_shp)
    
    #  merged_all projections "EPSG:4326"
    merged_all = merged_all.to_crs("EPSG:4326")
    
    # Delte the column of 'index_left' and 'index_right' 
    for df in [merged_all, world]:
        for col in ['index_left', 'index_right']:
            if col in df.columns:
                df.drop(col, axis=1, inplace=True)
    
    # Spatial join
    merged_with_iso = gpd.sjoin(merged_all, world[['geometry', 'ISO_A3']], how="left", predicate='within')
    
    # Set the GeoPackage output
    output_gpkg_path = os.path.join(processed_data_path, "merged_with_iso2.gpkg")
    merged_with_iso.to_file(output_gpkg_path, driver="GPKG")
    
    # Set the merged_iso CSV output
    output_csv_path = os.path.join(processed_data_path, "merged_with_iso2.csv")
    merged_with_iso.to_csv(output_csv_path, index=False)

    # Projections  df_africa_ports.crs to merged_all.CRS
    df_africa_ports_proj = df_africa_ports.to_crs(merged_all.crs)

    # Points that not included into df_africa_ports_proj
    non_intersected_from_merged = merged_all.loc[~merged_all.index.isin(df_africa_ports_proj.index)]
    # Delete the airport and inland port
    non_intersected_from_merged = non_intersected_from_merged[non_intersected_from_merged['FeatureUID'] != 'LTT02']
    non_intersected_from_merged = non_intersected_from_merged[non_intersected_from_merged['FeatureUID'] != 'KMI01']
    
    # Save gpkg and csv files
    non_intersected_gpkg_path = os.path.join(processed_data_path, "non_intersected_from_merged.gpkg")
    non_intersected_from_merged.to_file(non_intersected_gpkg_path, driver="GPKG")

    print(f"Total entries in non_intersected_from_merged: {len(non_intersected_from_merged)}")

    non_intersected_csv_path = os.path.join(processed_data_path, "non_intersected_from_merged.csv")
    non_intersected_from_merged.to_csv(non_intersected_csv_path, index=False)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
