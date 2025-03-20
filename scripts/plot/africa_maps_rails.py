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
    
    output_column = "line"
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
    
    #save_fig(os.path.join(figures,"roads_test.png"))
    #plt.close()
    # ax = point_map_plotting_colors_width(ax,roads_df,
    #                                 output_column,
    #                                 values_range,
    #                                 point_classify_column="length_m",
    #                                 #point_categories=["Unrefined","Refined"],
    #                                 #point_colors=["#e31a1c","#41ae76"],
    #                                 #point_labels=[s.upper() for s in ["Unrefined","Refined"]],
    #                                 #point_zorder=[6,7,8,9],
    #                                 #point_steps=8,
    #                                 #width_step = 40.0,
    #                                 #interpolation = 'fisher-jenks',
    #                                 legend_label="Road Corridors",
    #                                 legend_size=16,
    #                                 legend_weight=2.0,
    #                                 no_value_label="No value",
    #                               )

   
    colors = ['orange','grey']
    lines = [Line2D([0], [0], color=c, linewidth=3, linestyle='-') for c in colors]
    labels = ['lines','other (disused)']
    plt.legend(lines, labels)
    ax = plot_africa_basemap2(ax_plots)

    # colors1 = ['black','blue','blue','red']
    # main_rails.plot(ax=ax,zorder=4, column=output_column, color='black', linewidth=3)
    # main_rails2.plot(ax=ax,zorder=4, column=output_column, color='blue', linewidth=3)
    # main_rails3.plot(ax=ax,zorder=4, column=output_column, color='red', linewidth=3)
    rail_df.plot(ax=ax,zorder=5,column=output_column, cmap='tab20b',linewidth=3, missing_kwds={'color': 'lightgrey', 'linewidth': 1})
   
    plt.tight_layout()
    save_fig(os.path.join(figures,"rail_test3.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
