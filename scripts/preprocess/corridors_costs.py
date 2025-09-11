import sys
import os
import re
import pandas as pd
import geopandas as gpd
import igraph as ig
from shapely.geometry import LineString
from utils_new import *
from tqdm import tqdm
import math
tqdm.pandas()



def calculate_discounting_rate_factor(
    discount_rate=2.0,
    start_year=2025,
    end_year=2050,
    maintain_period=4.0,
    skip_year_one=False,
):

    discount_rates = []
    maintain_years = np.arange(start_year + 1, end_year + 1, maintain_period)
    for year in range(start_year, end_year + 1):
        if year in maintain_years:
            discount_rates.append(
                1.0 / math.pow(1.0 + 1.0 * discount_rate / 100.0, year - start_year)
            )
        else:
            if skip_year_one is True:
                discount_rates.append(0)
            else:
                discount_rates.append(1)

    return np.array(discount_rates)

def main(config):

    incoming_data_path = config['paths']['incoming_data']
    
    processed_data_path = config['paths']['data']


    roads_edges = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_network.gpkg"),
                             layer="edges",driver="GPKG")
    
    costs_df = pd.read_excel(os.path.join(
                            incoming_data_path,
                            "Roads_Costs.xlsx"),sheet_name="Roads_Costs_equal")
    

    roads_edges = roads_edges[~roads_edges['corridor_name'].isna()]
    roads_edges['length_km'] = roads_edges['length_m'] / 1000
    # Split the 'corridor_name' by '/' to account for multiple corridors
    roads_edges['corridor_name'] = roads_edges['corridor_name'].str.split('/')
    gdf_exploded = roads_edges.explode('corridor_name', ignore_index=True)

    # Group by the single corridor and tag_highway, then sum length_km
    grouped_data = gdf_exploded.groupby(['corridor_name', 'tag_highway','asset_type','lanes','paved'])['length_km'].sum().reset_index()
    grouped_data.loc[~grouped_data['tag_highway'].isin(['trunk', 'motorway', 'primary', 'secondary', 'tertiary', 'bridge']), 'tag_highway'] = 'tertiary'
    grouped_data["cost_tag"] = np.where(grouped_data["asset_type"]=="road_bridge","bridge",grouped_data["tag_highway"])   
    print("costs",costs_df)
    print("corridors",grouped_data)
    print("road type",grouped_data['tag_highway'])
    # Merge costs_df with grouped_data on tag_highway and paved
    merged_data = grouped_data.merge(costs_df, left_on=['cost_tag', 'paved'], right_on=['tag_highway', 'paved'], how='left')

    # Calculate costs
      # Actualize to 2025 values with a X annual inflation rate 37 (2020) and 80 (2010) 

    merged_data['min_capital_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * merged_data['cost_min']*(1.37)
    merged_data['max_capital_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * merged_data['cost_max']*(1.37)
    merged_data['median_capital_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * merged_data['cost_median']*(1.37)

    merged_data.drop([ 'cost_min', 'cost_max'], axis=1, inplace=True)
    merged_data['min_OM_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_min'].values[0]*(1.8)
    merged_data['max_OM_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_max'].values[0]*(1.8)
    merged_data['median_OM_cost_USD_2025'] = merged_data['length_km'] * merged_data['lanes'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_median'].values[0]*(1.8)
    
    merged_data.to_csv(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "merged_costs_data.csv"))
    
    maintain_years = calculate_discounting_rate_factor(
                discount_rate=2,
                skip_year_one=True,
            )
    
    print(merged_data[merged_data['paved']=='true'])
    

    # Investment calculation - assuming a road has a lifetime of 20 years (big cost only once in 25 years) and O & M are every 4 years, calcultation of investment to 2050 
    merged_data['investment_min_USD_2025'] = merged_data['min_capital_cost_USD_2025'] + ((merged_data['min_OM_cost_USD_2025']))*sum(maintain_years)
    merged_data['investment_max_USD_2025'] = merged_data['max_capital_cost_USD_2025'] + ((merged_data['max_OM_cost_USD_2025']))*sum(maintain_years)
    merged_data['investment_median_USD_2025'] = merged_data['median_capital_cost_USD_2025'] + ((merged_data['median_OM_cost_USD_2025']))*sum(maintain_years)
    
    
    merged_data=merged_data.groupby(['corridor_name']).agg({'length_km':'sum','min_capital_cost_USD_2025':'sum','max_capital_cost_USD_2025':'sum','median_capital_cost_USD_2025':'sum','min_OM_cost_USD_2025':'sum','max_OM_cost_USD_2025':'sum','median_OM_cost_USD_2025':'sum','investment_min_USD_2025':'sum','investment_max_USD_2025':'sum','investment_median_USD_2025':'sum'}).reset_index()
    
 
    merged_data.to_csv(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_corridors_costs.csv"))



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)

    