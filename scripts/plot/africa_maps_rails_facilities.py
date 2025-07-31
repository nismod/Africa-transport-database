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
import matplotlib.ticker as mticker
from matplotlib.colors import ListedColormap

def main(config):
    data_path = config['paths']['data']
    output_path = config['paths']['results']
    figure_path = config['paths']['figures']

    figures = os.path.join(figure_path)
    if os.path.exists(figures) is False:
        os.mkdir(figures)

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    fig, ax_plots = plt.subplots(1,1,
                    subplot_kw={'projection': ax_proj},
                    figsize=(12,12),
                    dpi=500)
    
    # save_fig(os.path.join(figures,"africa_basemap.png"))
    #plt.close()

    edges_df = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_railways_network.gpkg"
                 ), layer = 'edges')
    nodes_df = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_railways_network.gpkg"
                 ), layer = 'nodes')
    
    
    # roads_df["geometry"] = roads_df.geometry.centroid



    output_column = 'facility'

    # Clean and standardize values
    nodes_df[output_column] = nodes_df[output_column].astype(str).str.strip().str.title()

    # Filter out bad values
    nodes_df = nodes_df[~nodes_df[output_column].isin(["Not Known", "Unknown", "", "Nan","None"])]
    nodes_df = nodes_df[nodes_df[output_column].notna()]

    # Count occurrences
    facility_counts = nodes_df[output_column].value_counts().to_dict()

    # Convert to categorical and drop unused categories
    nodes_df[output_column] = pd.Categorical(nodes_df[output_column])
    nodes_df[output_column] = nodes_df[output_column].cat.remove_unused_categories()

    # Number of colors
    num_colors = len(nodes_df[output_column].unique())
    print("Number of facilities:", num_colors)

    # Build colormap
    cmap = plt.get_cmap('hsv', num_colors)
    custom_cmap = ListedColormap([cmap(i) for i in range(num_colors)])

    # Plot base
    bold_font = font_manager.FontProperties(weight='bold', size=14)
    ax = plot_africa_basemap2(ax_plots)

    # Plot edges
    edges_df.plot(ax=ax, zorder=3, color='black', linewidth=1)

    # Plot nodes
    plot = nodes_df.plot(
        ax=ax,
        zorder=5,
        column=output_column,
        cmap=custom_cmap,
        markersize=25,
        legend=True,
        legend_kwds={
            'title': "Railway Node Facility Type",
            'title_fontproperties': bold_font,
            'fontsize': 10,
            'loc': 'lower left',
            'fancybox': True,
            'frameon': True,
            'edgecolor': 'black',
            'facecolor': 'white',
            'ncol': 2
        },
        missing_kwds={'color': 'lightgrey', 'linewidth': 1}
    )

    # Format legend labels to include counts
    legend = ax.get_legend()
    for text in legend.get_texts():
        label = text.get_text()
        count = facility_counts.get(label.lower().title(), 0)
        text.set_text(f"{label} ({count})")

    # Save
    plt.tight_layout()
    save_fig(os.path.join(figures, "rail_test_facility.png"))


        

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
