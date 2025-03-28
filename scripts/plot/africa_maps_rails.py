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

    rail_df = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_railways_network.gpkg"
                 ), layer = 'edges')
    
    
    # roads_df["geometry"] = roads_df.geometry.centroid

    print(rail_df.columns)
    
    output_column = "status"
    # values_range = roads_df[output_column].values.tolist()
    # null_types = ["NULL"]
    # main_rails = rail_df[
    #                     rail_df[output_column].isin(['open'])
    #                     ]
    # main_rails2 = rail_df[
    #                     rail_df[output_column].isin(['construction'])
    #                     ]
    # main_rails3 = rail_df[
    #                     rail_df[output_column].isin(['disused'])
    #                     ]
    

    # ax_proj = get_projection(epsg=4326)
    # fig, ax_plots = plt.subplots(1,1,
    #                      subplot_kw={'projection': ax_proj},
    #                      figsize=(12,12),
    #                      dpi=500)
    # ax_plots = ax_plots.flatten()
    
    ax = plot_africa_basemap(ax_plots)
    
   

    # Create a font property for bold text
    bold_font = font_manager.FontProperties(weight='bold',size=18)
    # colors = ['orange','grey']
    # lines = [Line2D([0], [0], color=c, linewidth=3, linestyle='-') for c in colors]
    # labels = ['Lines','Other (disused)']
    
    ax = plot_africa_basemap2(ax_plots)

    # colors1 = ['black','blue','blue','red']
    # main_rails.plot(ax=ax,zorder=4, column=output_column, color='black', linewidth=3)
    # main_rails2.plot(ax=ax,zorder=4, column=output_column, color='blue', linewidth=3)
    # main_rails3.plot(ax=ax,zorder=4, column=output_column, color='red', linewidth=3)
    
   
    rail_df.plot(
    ax=ax,
    zorder=5,
    column=output_column,  # The column you're using for coloring
    cmap='twilight_shifted',
    linewidth=3,
    legend=True,  # Add legend directly here
    legend_kwds={
        'title': "Railway Status",
        'title_fontproperties': bold_font,
        'fontsize': 14,
        'loc': (0.1, 0.1) ,
        'fancybox': True,
        'frameon': True,
        'edgecolor': 'black',
        'facecolor': 'white'
        },
    missing_kwds={'color': 'lightgrey', 'linewidth': 1}
    )
    # Get the legend and modify labels to uppercase
    leg = ax.get_legend()
    for text in leg.get_texts():
        text.set_text(text.get_text().capitalize()) 
    
    plt.tight_layout()
    save_fig(os.path.join(figures,"rail_test2.png"))
    
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
