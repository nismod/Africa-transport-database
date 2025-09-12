"""Road network risks and adaptation maps
"""
import os
import sys
from collections import OrderedDict
import pandas as pd
import geopandas as gpd
import numpy as np
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from map_plotting_utils import *
from tqdm import tqdm
from matplotlib import cm
tqdm.pandas()
from matplotlib import font_manager



def main(config):
    data_path = config['paths']['data']
    output_path = config['paths']['results']
    figure_path = config['paths']['figures']

    figures = os.path.join(figure_path)
    if os.path.exists(figures) is False:
        os.mkdir(figures)

    
    roads_df = gpd.read_parquet(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_roads_edges_FINAL.geoparquet"
                 ))
    
    
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

    grouped_data = gdf_exploded.groupby(['corridor_name', 'tag_highway'], as_index=False).agg({'length_km': 'sum'})
    
    # Check again for duplicates
    print(grouped_data.duplicated(subset=['corridor_name', 'tag_highway']).sum())

    # Clean and format tag_highway names (capitalize and replace underscores with space)
    grouped_data['tag_highway'] = grouped_data['tag_highway'].str.replace('_', ' ').str.title()

    # Group all non-standard highways under 'Other'
    
    # Pivot the data for a stacked bar plot
    desired_order = ['Motorway', 'Trunk', 'Primary', 'Secondary', 'Tertiary', 'Other']

    # Pivot the data as usual
    pivot_data = grouped_data.pivot(
        index='corridor_name',
        columns='tag_highway',
        values='length_km'
    ).fillna(0)

    # Reorder the columns according to desired_order
    pivot_data = pivot_data.reindex(columns=desired_order, fill_value=0)
    
    # Create a font property for bold text
    bold_font = font_manager.FontProperties(weight='bold')
    # Select a colormap 
    colormap =  ['#d7191c','#fdae61','#ffffbf','#abd9e9','#2c7bb6','#d9d9d9']
    # Get color values from the colormap
    num_colors = len(pivot_data.columns)
    colors = [colormap[i] for i in range(num_colors)]

    # Plot with colormap
    pivot_data.plot(kind='bar', stacked=True, figsize=(12, 8), color=colors)

    # Add labels and title
    plt.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.7)
    plt.title('Length by corridor and typology')
    plt.xlabel('Corridor')
    plt.ylabel('Total Length (km)')
    # Adjust x-axis labels
    plt.xticks(rotation=30, ha='right')
    plt.legend(title='Typology',title_fontproperties=bold_font, fontsize='small')
    plt.subplots_adjust(bottom=0.1)
    plt.tight_layout()

    save_fig(os.path.join(figures,"roads_hist_cap2_grid.png"))
    
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
