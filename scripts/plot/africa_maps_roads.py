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
tqdm.pandas()
from matplotlib import font_manager
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
    

    roads_df = gpd.read_parquet(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_roads_edges_FINAL.geoparquet"
                 ))
    
    # Filter the category we want to show
    allowed = {"primary", "secondary", "trunk", "motorway"}

    
    roads_df["tag_highway"] = roads_df["tag_highway"].apply(
        lambda x: x.capitalize() if str(x).lower() in allowed else "Other"
    )
   
    print(roads_df.columns)
    
    output_column = "tag_highway"
    
    ax = plot_africa_basemap2(ax_plots)
    

    bold_font = font_manager.FontProperties(weight='bold',size=18)
    
    ax = plot_africa_basemap2(ax_plots)
    # main_roads.plot(ax=ax,zorder=5, column=output_column, cmap='magma', linewidth=2, legend=True)
    # roads_df.plot(ax=ax,zorder=6,column=output_column, cmap='tab20',linewidth=5,missing_kwds={'color': 'black', 'linewidth': 1,'zorder':4})
    # Categories in the order you want
    categories = ["Primary", "Secondary", "Trunk", "Motorway", "Other"]

    # Define colors in the same order
    colors = ["#a50026", "#1f78b4", "#33a02c", "#ffae42", "grey"]

    # Build a colormap
    cmap = ListedColormap(colors)
    roads_df[output_column] = pd.Categorical(
                                roads_df[output_column],
                                categories=categories,
                                ordered=True
                            )

    roads_df.plot(
        ax=ax,
        zorder=5,
        column=output_column,   
        cmap=cmap,
        linewidth=1,
        legend=True,            
        legend_kwds={
            'title': "Road Typology",
            'title_fontproperties': bold_font,
            'fontsize': 14,
            'loc': "lower left",
            'fancybox': True,
            'frameon': True,
            'edgecolor': 'black',
            'facecolor': 'white'
        },
        missing_kwds={'color': 'lightgrey', 'linewidth': 1}
    )

    
    plt.tight_layout()
    save_fig(os.path.join(figures,"roads_typology2_LAST.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
