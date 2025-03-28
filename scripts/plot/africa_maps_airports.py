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
    figure_path = config['paths']['figures']

    figures = os.path.join(figure_path)
    os.makedirs(figures,exist_ok=True)

    marker_size_max = 2000
    air_nodes = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_airport_network.gpkg"
                 ), layer = 'nodes')
    tmax = air_nodes["TotalSeats"].max()
    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    fig, ax_plots = plt.subplots(1,1,
                    subplot_kw={'projection': ax_proj},
                    figsize=(12,12),
                    dpi=500)
    
    ax = plot_africa_basemap2(ax_plots)
    # air_nodes.plot(ax=ax,zorder=4, column='TotalSeats', cmap='YlOrRd',markersize=15,legend=True, scheme="quantiles", label="Airport total seats")
    air_nodes["markersize"] = marker_size_max*(air_nodes["TotalSeats"]/tmax)**0.5
    air_nodes = air_nodes.sort_values(by="TotalSeats",ascending=False)
    air_nodes.geometry.plot(
        ax=ax, 
        color="#3690c0", 
        edgecolor='none',
        markersize=air_nodes["markersize"],
        alpha=0.7,
        zorder=10)

    ins = ax.inset_axes([0.02,-0.2,0.15,0.8])
    ins.spines[['top','right','bottom','left']].set_visible(False)
    ins.set_xticks([])
    ins.set_yticks([])
    ins.set_ylim([-3,2])
    ins.set_xlim([-1,1.5])
    ins.set_facecolor("#c6e0ff")
    xk = -0.6
    xt = -0.95
    t_key = 10**np.arange(1,np.ceil(np.log10(tmax)),1)[:-1]
    t_key = t_key[::-1]
    Nk = t_key.size
    yk = np.linspace(-2.45,0.8,Nk)
    yt = 1.5
    size_key = marker_size_max*(t_key/tmax)**0.5
    key = gpd.GeoDataFrame(geometry=gpd.points_from_xy(np.ones(Nk)*xk, yk))
    key.geometry.plot(ax=ins,markersize=size_key,color="#3690c0")
    ins.text(xt,yt,'Total Seats (annual)',weight='bold',va='center',fontsize=12)
    for k in range(Nk):
        ins.text(xk,yk[k],'       {:,.0f}'.format(t_key[k]),va='center',fontsize=12)
    plt.tight_layout()
    save_fig(os.path.join(figures,"airports.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
