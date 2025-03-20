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

    roads_df = gpd.read_parquet(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_roads_edges_FINAL.geoparquet"
                 ))
    
    
    # roads_df["geometry"] = roads_df.geometry.centroid

    print(roads_df.columns)
    
    output_column = "corridor_name"
    # values_range = roads_df[output_column].values.tolist()
    # null_types = ["NULL"]
    # main_roads = roads_df[
    #                     roads_df[output_column].isin(['primary','secondary','tertiary','trunk','motorway'])
    #                     ]
    

    # ax_proj = get_projection(epsg=4326)
    # fig, ax_plots = plt.subplots(1,1,
    #                      subplot_kw={'projection': ax_proj},
    #                      figsize=(12,12),
    #                      dpi=500)
    # ax_plots = ax_plots.flatten()
    
    ax = plot_africa_basemap2(ax_plots)
    
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

   
    colors = ['orange','lightgrey']
    lines = [Line2D([0], [0], color=c, linewidth=3, linestyle='-') for c in colors]
    labels = ['Road Corridors','Other Roads']
    plt.legend(lines, labels)
    ax = plot_africa_basemap2(ax_plots)
    # main_roads.plot(ax=ax,zorder=5, column=output_column, cmap='magma', linewidth=2, legend=True)
    roads_df.plot(ax=ax,zorder=6,column=output_column, cmap='tab20',linewidth=5,missing_kwds={'color': 'lightgrey', 'linewidth': 1,'zorder':5})
   
    plt.tight_layout()
    save_fig(os.path.join(figures,"roads_test2.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
