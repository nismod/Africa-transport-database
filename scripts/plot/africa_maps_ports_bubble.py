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
from matplotlib import font_manager
tqdm.pandas()



def main(config):
    data_path = config['paths']['data']
    figure_path = config['paths']['figures']

    figures = os.path.join(figure_path)
    os.makedirs(figures,exist_ok=True)

    marker_size_max = 2000

    maritime_nodes = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_maritime_network.gpkg"
                 ), layer = 'nodes')
    maritime_edges = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_maritime_network.gpkg"
                 ), layer = 'edges')
    
    
    

    IWW_nodes = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_iww_network.gpkg"
                 ), layer = 'nodes')
    IWW_edges = gpd.read_file(os.path.join(
                 data_path,
                 "infrastructure",
                 "africa_iww_network.gpkg"
                 ), layer = 'edges')
    
    IWW_nodes = IWW_nodes[
                        IWW_nodes['infra'].isin(['IWW port'])
                        ]
    maritime_nodes = maritime_nodes[
                        maritime_nodes['infra'].isin(['port'])
                        ]
    
    tmax = maritime_nodes["vessel_count_total"].max()
    target_crs = "EPSG:4326"
    maritime_nodes = maritime_nodes.to_crs(target_crs)
    IWW_nodes = IWW_nodes.to_crs(target_crs)
    IWW_edges = IWW_edges.to_crs(target_crs)
    maritime_edges = maritime_edges.to_crs(target_crs)
    print(maritime_nodes.head())
    

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    fig, ax_plots = plt.subplots(1,1,
                    subplot_kw={'projection': ax_proj},
                    figsize=(12,12),
                    dpi=500)
    
    ax = plot_africa_basemap2(ax_plots)

    # Expand limits a bit
    bounds = maritime_nodes.total_bounds  # [minx, miny, maxx, maxy]
    pad_x = (bounds[2] - bounds[0]) * 0.05
    pad_y = (bounds[3] - bounds[1]) * 0.2

    ax.set_extent([bounds[0] - pad_x, bounds[2] + pad_x,
                bounds[1] - pad_y, bounds[3] + pad_y],
                crs=ccrs.PlateCarree())  # Because data is now in EPSG:4326
    # merged_gdf.plot(ax=ax,zorder=4, column='TotalSeats', cmap='YlOrRd',markersize=15,legend=True, scheme="quantiles", label="Airport total seats")
    maritime_nodes["markersize"] = marker_size_max*(maritime_nodes["vessel_count_total"]/tmax)**0.5
    maritime_nodes["markersize"].describe()
    maritime_nodes = maritime_nodes.sort_values(by="vessel_count_total",ascending=False)
    maritime_nodes.geometry.plot(
        ax=ax, 
        color="#3690c0", 
        edgecolor='none',
        markersize=maritime_nodes["markersize"],
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
    
    t_key = 10**np.arange(0.7,np.ceil(np.log10(tmax)),0.6)[:-1]
    
    # t_key = maritime_nodes["vessel_count_total"].quantile([0.25, 0.5, 0.75, 1.0]).values
    t_key = t_key[::-1]
    Nk = t_key.size
    yk = np.linspace(-2.45,0.8,Nk)
    yt = 1.5
    size_key = marker_size_max*(t_key/tmax)**0.5
    key = gpd.GeoDataFrame(geometry=gpd.points_from_xy(np.ones(Nk)*xk, yk))
    key.geometry.plot(ax=ins,markersize=size_key,color="#3690c0")
    ins.text(xt,yt,'Port annual vessel count',weight='bold',va='center',fontsize=12)
    for k in range(Nk):
        ins.text(xk,yk[k],'       {:,.0f}'.format(t_key[k]),va='center',fontsize=12)

    IWW_edges.plot(ax=ax, zorder=3, color='#01665e', linewidth=1, label="IWW route")
    
    IWW_nodes.plot(ax=ax, zorder=4, color='#01665e', markersize=25, label="IWW port")
    
    maritime_edges.plot(ax=ax, zorder=3, color='#3690c0', linewidth=1, label="Maritime route")
    
    maritime_nodes.plot(ax=ax, zorder=4, color='#3690c0', markersize=25, label="Maritime port")

    # Add legend manually
    bold_font = font_manager.FontProperties(weight='bold',size=12)
    ax.legend(loc=(0.015, 0.35),title='Water networks', facecolor="#c6e0ff",fontsize=12,frameon = False, title_fontproperties= bold_font) 
    ax.get_legend()._legend_box.align = "left"

    plt.tight_layout()
    
    save_fig(os.path.join(figures,"ports_with_edges_v2.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)