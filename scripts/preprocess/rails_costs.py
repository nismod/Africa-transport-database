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


    rails_edges = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_railways_network.gpkg"),
                             layer="edges",driver="GPKG")
    
    costs_df = pd.read_excel(os.path.join(
                            incoming_data_path,
                            "Rail_Costs.xlsx"))
    

    rails_edges['length_km'] = rails_edges['length_m'] / 1000
    # Split the 'corridor_name' by '/' to account for multiple corridors

    # Group by the single corridor and tag_highway, then sum length_km
    grouped_data = rails_edges.groupby(['line', 'status'])['length_km'].sum().reset_index()
    if grouped_data['status'].isin(['construction', 'planned', 'proposed', 'rehabilitation']).any():
       
        # Calculate costs
        # Actualize to 2025 values with a 2% inflation rate (https://www.bls.gov/data/inflation_calculator.htm)

        grouped_data['min_capital_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'construction and upgrading', 'cost_min'].values[0]*pow(1.02,5)
        grouped_data['max_capital_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'construction and upgrading', 'cost_max']*pow(1.02,5)
        grouped_data['median_capital_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'construction and upgrading', 'cost_median']*pow(1.02,5)

        grouped_data['min_OM_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_min'].values[0]*pow(1.02,15)
        grouped_data['max_OM_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_max'].values[0]*pow(1.02,15)
        grouped_data['median_OM_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_median'].values[0]*pow(1.02,15)
        
        # Investment calculation - assuming a rail has a lifetime of 50 years and O & M are every 5 years
        grouped_data['investment_min_USD_2025'] = (grouped_data['min_capital_cost_USD_2025'] + (10 * grouped_data['min_OM_cost_USD_2025']))*pow(1.02,50)
        grouped_data['investment_max_USD_2025'] = (grouped_data['max_capital_cost_USD_2025'] + (10 * grouped_data['max_OM_cost_USD_2025']))*pow(1.02,50)
        grouped_data['investment_median_USD_2025'] = (grouped_data['median_capital_cost_USD_2025'] + (10 * grouped_data['median_OM_cost_USD_2025']))*pow(1.02,50)
        # Actualize to 2025 values with a 2% discount rate
        
        grouped_data=grouped_data.groupby(['line','status']).agg({'length_km':'sum','min_capital_cost_USD_2025':'sum','max_capital_cost_USD_2025':'sum','median_capital_cost_USD_2025':'sum','min_OM_cost_USD_2025':'sum','max_OM_cost_USD_2025':'sum','median_OM_cost_USD_2025':'sum','investment_min_USD_2025':'sum','investment_max_USD_2025':'sum','investment_median_USD_2025':'sum'}).reset_index()
        

    grouped_data.to_csv(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_rails_costs.csv"))
   
    
   

    



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)

    