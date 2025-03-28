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


    roads_edges = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_FINAL.gpkg"),
                             layer="edges",driver="GPKG")
    
    costs_df = pd.read_excel(os.path.join(
                            incoming_data_path,
                            "Roads_Costs.xlsx"))
    

    roads_edges = roads_edges[~roads_edges['corridor_name'].isna()]
    roads_edges['length_km'] = roads_edges['length_m'] / 1000
    # Split the 'corridor_name' by '/' to account for multiple corridors
    roads_edges['corridor_name'] = roads_edges['corridor_name'].str.split('/')
    gdf_exploded = roads_edges.explode('corridor_name', ignore_index=True)

    # Group by the single corridor and tag_highway, then sum length_km
    grouped_data = gdf_exploded.groupby(['corridor_name', 'tag_highway','lanes','paved'])['length_km'].sum().reset_index()
    if not grouped_data['tag_highway'].isin(['trunk', 'motorway', 'primary', 'secondary', 'tertiary', 'bridge']).any():
        grouped_data['tag_highway'] = 'tertiary'
        
    print("costs",costs_df)
    print("corridors",grouped_data)
    print("road type",grouped_data['tag_highway'])
    # Merge costs_df with grouped_data on tag_highway and paved
    merged_data = grouped_data.merge(costs_df, left_on=['tag_highway', 'paved'], right_on=['tag_highway', 'paved'], how='left')

    # Calculate costs
    # Actualize to 2025 values with a 2% inflation rate (https://www.bls.gov/data/inflation_calculator.htm)

    merged_data['min_capital_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * merged_data['cost_min']*pow(1.02,5)
    merged_data['max_capital_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * merged_data['cost_max']*pow(1.02,5)
    merged_data['median_capital_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * merged_data['cost_median']*pow(1.02,5)

    
    merged_data.drop([ 'cost_min', 'cost_max'], axis=1, inplace=True)
    merged_data['min_OM_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_min'].values[0]*pow(1.02,15)
    merged_data['max_OM_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_max'].values[0]*pow(1.02,15)
    merged_data['median_OM_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_median'].values[0]*pow(1.02,15)
    
    # Investment calculation - assuming a road has a lifetime of 50 years and O & M are every 5 years
    merged_data['investment_min_USD_2025'] = (merged_data['min_capital_cost_USD_2025'] + (10 * merged_data['min_OM_cost_USD_2025']))*pow(1.02,50)
    merged_data['investment_max_USD_2025'] = (merged_data['max_capital_cost_USD_2025'] + (10 * merged_data['max_OM_cost_USD_2025']))*pow(1.02,50)
    merged_data['investment_median_USD_2025'] = (merged_data['median_capital_cost_USD_2025'] + (10 * merged_data['median_OM_cost_USD_2025']))*pow(1.02,50)
    # Actualize to 2025 values with a 2% discount rate
    
    merged_data=merged_data.groupby(['corridor_name']).agg({'length_km':'sum','min_capital_cost_USD_2025':'sum','max_capital_cost_USD_2025':'sum','median_capital_cost_USD_2025':'sum','min_OM_cost_USD_2025':'sum','max_OM_cost_USD_2025':'sum','median_OM_cost_USD_2025':'sum','investment_min_USD_2025':'sum','investment_max_USD_2025':'sum','investment_median_USD_2025':'sum'}).reset_index()
    

    merged_data.to_csv(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_corridors_costs.csv"))
   
    
   

    



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)

    