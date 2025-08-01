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

    
    rail_df = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_railways_network.gpkg"
                 ), layer = 'edges')
    
    
    rail_df['length_km'] = rail_df['length_m'] / 1000
    # Group the data by country and status, summing the length_m column
    grouped_data = rail_df.groupby(['country', 'status'])['length_km'].sum().reset_index()

    # Pivot the data to prepare for stacked bar plot
    grouped_data['status'] = grouped_data['status'].str.capitalize()
    pivot_data = grouped_data.pivot(index='country', columns='status', values='length_km').fillna(0)
    # Preview the pivot table
    print(pivot_data.head())
    
    # Create a font property for bold text
    bold_font = font_manager.FontProperties(weight='bold')
    # Select a colormap (e.g., 'viridis', 'plasma', 'tab20', 'Set1', etc.)
    # colormap = [
    # '#fddbcc',  
    # '#f97306',  
    # '#c1272d',  
    # '#801515',  
    # '#fbb03b',  
    # '#d0e4f7',  
    # '#8c8ccf',  
    # '#6a5acd',  
    # '#800080',  
    # '#d3d3d3',  
    # ]
    colormap = {
    'Abandoned': '#fddbcc',       # very light peach
    'Disused': '#f97306',         # bright orange
    'Razed': '#c1272d',           # deep red
    'Suspended': '#801515',       # dark maroon
    'Open': '#fbb03b',            # golden orange
    'Planned': '#d0e4f7',         # light sky blue
    'Proposed': '#8c8ccf',        # soft lavender-blue
    'Construction': '#6a5acd',    # medium slate blue
    'Rehabilitation': '#800080',  # purple
    'Unknown': '#d3d3d3',         # light gray
    }

    
    # Get color values from the colormap
    # num_colors = len(pivot_data.columns)
    # colors = [colormap[i] for i in range(num_colors)]
    colors = [colormap[status] for status in pivot_data.columns]

    # Plot with colormap
    pivot_data.plot(kind='bar', stacked=True, figsize=(12, 8), color=colors)

    # Add labels and title
    plt.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.7)
    plt.title('Length by Country and Status')
    plt.xlabel('Country')
    plt.ylabel('Total Length (km)')
    # Adjust x-axis labels
    plt.xticks(rotation=30, ha='right')
    plt.legend(title='Status',title_fontproperties=bold_font, fontsize='small')
    
    plt.subplots_adjust(bottom=0.1)
    plt.tight_layout()

    save_fig(os.path.join(figures,"rail_hist_cap_withgrid.png"))
    
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
