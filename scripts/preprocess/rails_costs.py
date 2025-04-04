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


    rails_edges = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_railways_network.gpkg"),
                             layer="edges",driver="GPKG")
    
    costs_df = pd.read_excel(os.path.join(
                            incoming_data_path,
                            "Rail_Costs.xlsx"))
    

    rails_edges['length_km'] = rails_edges['length_m'] / 1000


    # Group by the single line and status, then sum length_km
    grouped_data = rails_edges.groupby(['line', 'status'])['length_km'].sum().reset_index()
    
    mask = grouped_data['status'].isin(['construction', 'planned', 'proposed', 'rehabilitation'])

# Set zero values for all rows by default
    grouped_data.loc[~mask, ['min_capital_cost_USD_2025', 'max_capital_cost_USD_2025', 
                            'median_capital_cost_USD_2025', 'min_OM_cost_USD_2025', 
                            'max_OM_cost_USD_2025', 'median_OM_cost_USD_2025',
                            'investment_min_USD_2025', 'investment_max_USD_2025', 
                            'investment_median_USD_2025']] = 0

    # Only update rows where status matches
    grouped_data.loc[mask, 'min_capital_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'construction and upgrading', 'cost_min'].values[0] * 1.37
    grouped_data.loc[mask, 'max_capital_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'construction and upgrading', 'cost_max'].values[0] * 1.37
    grouped_data.loc[mask, 'median_capital_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'construction and upgrading', 'cost_median'].values[0] * 1.37

    grouped_data.loc[mask, 'min_OM_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_min'].values[0] * 1.8
    grouped_data.loc[mask, 'max_OM_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_max'].values[0] * 1.8
    grouped_data.loc[mask, 'median_OM_cost_USD_2025'] = grouped_data['length_km'] * costs_df.loc[costs_df['cost_type'] == 'O&M', 'cost_median'].values[0] * 1.8


    maintain_years = calculate_discounting_rate_factor(
                discount_rate=2,
                skip_year_one=True,
            )
    grouped_data.loc[mask, 'investment_min_USD_2025'] = (grouped_data['min_capital_cost_USD_2025'] + (grouped_data['min_OM_cost_USD_2025'])) * sum(maintain_years)
    grouped_data.loc[mask, 'investment_max_USD_2025'] = (grouped_data['max_capital_cost_USD_2025'] + (grouped_data['max_OM_cost_USD_2025'])) * sum(maintain_years)
    grouped_data.loc[mask, 'investment_median_USD_2025'] = (grouped_data['median_capital_cost_USD_2025'] + (grouped_data['median_OM_cost_USD_2025'])) * sum(maintain_years)
            
    grouped_data=grouped_data.groupby(['line','status']).agg({'length_km':'sum','min_capital_cost_USD_2025':'sum','max_capital_cost_USD_2025':'sum','median_capital_cost_USD_2025':'sum','min_OM_cost_USD_2025':'sum','max_OM_cost_USD_2025':'sum','median_OM_cost_USD_2025':'sum','investment_min_USD_2025':'sum','investment_max_USD_2025':'sum','investment_median_USD_2025':'sum'}).reset_index()
        

    grouped_data.to_csv(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_rails_costs.csv"))
   
    
   

    



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)

    