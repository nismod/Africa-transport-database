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

    
    air_nodes = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_airport_network.gpkg"
                 ), layer = 'nodes')
    air_edges = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_airport_network.gpkg"
                 ), layer = 'edges')
    
    
    air_nodes["geometry"] = air_nodes.geometry.centroid
    

    
    
    
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

   
    
    
    # colors = ['darkblue','mediumblue']
    # colors2 = ['blue','royalblue']
    
    # lines = [Line2D([0], [0], color=c, linewidth=3, linestyle='-') for c in colors]
    # points =[Line2D([0], [0], color=c, markersize=5, linestyle='dotted') for c in colors2]
    # labels = ['maritime route','IWW route']
    # labels2 = ['maritime port','IWW port']

    # plt.legend([lines,points], [labels,labels2])

    ax = plot_africa_basemap(ax_plots)
    # colors1 = ['black','blue','blue','red']
    air_nodes.plot(ax=ax,zorder=4, column='TotalSeats', cmap='YlOrRd',markersize=15,legend=True, scheme="quantiles", label="Airport total seats")
    # air_edges.plot(ax=ax,zorder=1, color='cornflowerblue',linewidth=2,label="air route", linestyles='dotted')
    
    
    # corridors.plot(ax=ax,zorder=2,column=output_column, cmap='tab20',linewidth=5)
   
    plt.tight_layout()
    save_fig(os.path.join(figures,"airports.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
