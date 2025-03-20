import os
import sys
from collections import OrderedDict
import pandas as pd
import geopandas as gpd
import numpy as np
import cartopy.crs as ccrs
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from map_plotting_utils import *
#from utils_new import *
from tqdm import tqdm
tqdm.pandas()


def main(config):
    config = load_config()
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
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
    ax = plot_africa_basemap(ax_plots)
    
    roads_df = gpd.read_parquet(os.path.join(
                 processed_data_path,
                 "infrastructure",
                 "africa_roads_edges_FINAL.geoparquet"
                 ))
    
    
    # roads_df["geometry"] = roads_df.geometry.centroid

    print(roads_df.columns)
    
    output_column = "corridor_name"
    values_range = roads_df[output_column].values.tolist()

    
    breakpoint()

    # ax_proj = get_projection(epsg=4326)
    # fig, ax_plots = plt.subplots(1,1,
    #                      subplot_kw={'projection': ax_proj},
    #                      figsize=(12,12),
    #                      dpi=500)
    # ax_plots = ax_plots.flatten()
    
    # ax = plot_africa_basemap(ax_plots)
    roads_df.plot()
    # ax = point_map_plotting_colors_width(ax,roads_df,
    #                                 output_column,
    #                                 values_range,
    #                                 point_classify_column="asset_type",
    #                                 #point_categories=["Unrefined","Refined"],
    #                                 #point_colors=["#e31a1c","#41ae76"],
    #                                 #point_labels=[s.upper() for s in ["Unrefined","Refined"]],
    #                                 #point_zorder=[6,7,8,9],
    #                                 #point_steps=8,
    #                                 #width_step = 40.0,
    #                                 #interpolation = 'fisher-jenks',
    #                                 legend_label="Paved and unpaved roads",
    #                                 legend_size=16,
    #                                 legend_weight=2.0,
    #                                 no_value_label="No output",
    #                                 )
    plt.tight_layout()
    save_fig(os.path.join(figures,"roads_test.png"))
    plt.close()
    breakpoint()
# africa_boundaries = gpd.read_file(os.path.join(
#                             incoming_data_path,
#                             "Africa_GIS Supporting Data",
#                             "a. Africa_GIS Shapefiles",
#                             "AFR_Political_ADM0_Boundaries.shp",
#                             "AFR_Political_ADM0_Boundaries.shp"))
# africa_boundaries.rename(columns={"DsgAttr03":"iso3"},inplace=True)
# africa_boundaries.plot()
# plt.show()

# roads = gpd.read_file(os.path.join(
#                  incoming_data_path,
#                  "africa_roads",
#                  "africa_main_roads.gpkg"))
# roads.plot()
# plt.show()

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)