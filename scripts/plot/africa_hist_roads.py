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
    
    
    roads_df['length_km'] = roads_df['length_m'] / 1000
    # Split the 'corridor_name' by '/' to account for multiple corridors
    roads_df['corridor_name'] = roads_df['corridor_name'].str.split('/')

    # Explode the data to separate overlapping corridors into individual rows
    gdf_exploded = roads_df.explode('corridor_name', ignore_index=True)

    # Group by the single corridor and tag_highway, then sum length_km
    grouped_data = gdf_exploded.groupby(['corridor_name', 'tag_highway'])['length_km'].sum().reset_index()

    # Pivot the data for stacked bar plot
    pivot_data = grouped_data.pivot(index='corridor_name', columns='tag_highway', values='length_km').fillna(0)

    
    # Create a font property for bold text
    bold_font = font_manager.FontProperties(weight='bold')
    # Select a colormap (e.g., 'viridis', 'plasma', 'tab20', 'Set1', etc.)
    colormap = cm.get_cmap('Pastel1')
    # Get color values from the colormap
    num_colors = len(pivot_data.columns)
    colors = [colormap(i / num_colors) for i in range(num_colors)]

    # Plot with colormap
    pivot_data.plot(kind='bar', stacked=True, figsize=(12, 8), color=colors)

    # Add labels and title
    plt.title('Length by corridor and typology')
    plt.xlabel('Corridor')
    plt.ylabel('Total Length (km)')
    # Adjust x-axis labels
    plt.xticks(rotation=30, ha='right')
    plt.legend(title='Typology',title_fontproperties=bold_font, fontsize='small')
    plt.subplots_adjust(bottom=0.1)
    plt.tight_layout()

    # Show the plot
    plt.show()
    plt.close()
    save_fig(os.path.join(figures,"roads_hist.png"))
    
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
