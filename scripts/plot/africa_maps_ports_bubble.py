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
    maritime_values = pd.read_csv(os.path.join(
                 data_path,
                 "port_statistics",
                 "port_vessel_types_and_capacities.csv"
                 ))
    

   
    
    merged_gdf = maritime_nodes.merge(maritime_values, on=['id'])
    print(merged_gdf['annual_vessel_capacity_tons'])
    

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
    
    tmax = merged_gdf["annual_vessel_capacity_tons"].max()
    print(type(tmax))
    print(type(merged_gdf["annual_vessel_capacity_tons"]))
    

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    fig, ax_plots = plt.subplots(1,1,
                    subplot_kw={'projection': ax_proj},
                    figsize=(12,12),
                    dpi=500)
    
    ax = plot_africa_basemap2(ax_plots)
    # merged_gdf.plot(ax=ax,zorder=4, column='TotalSeats', cmap='YlOrRd',markersize=15,legend=True, scheme="quantiles", label="Airport total seats")
    merged_gdf["markersize"] = marker_size_max*(merged_gdf["annual_vessel_capacity_tons"]/tmax)**0.5
    merged_gdf = merged_gdf.sort_values(by="annual_vessel_capacity_tons",ascending=False)
    merged_gdf.geometry.plot(
        ax=ax, 
        color="#3690c0", 
        edgecolor='none',
        markersize=merged_gdf["markersize"],
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
    ins.text(xt,yt,'Port annual vessel capacity (tons)',weight='bold',va='center',fontsize=12)
    for k in range(Nk):
        ins.text(xk,yk[k],'       {:,.0f}'.format(t_key[k]),va='center',fontsize=12)

    IWW_edges.plot(ax=ax, zorder=3, color='#01665e', linewidth=1, label="IWW route")
    
    IWW_nodes.plot(ax=ax, zorder=4, color='#01665e', markersize=30, label="IWW port")
    
    maritime_edges.plot(ax=ax, zorder=3, color='#3690c0', linewidth=1, label="Maritime route")

    # Add legend manually
    bold_font = font_manager.FontProperties(weight='bold',size=12)
    ax.legend(loc=(0.015, 0.35),title='Water networks', facecolor="#c6e0ff",fontsize=12,frameon = False, title_fontproperties= bold_font) 
    ax.get_legend()._legend_box.align = "left"

    plt.tight_layout()
    
    save_fig(os.path.join(figures,"ports_with_edges.png"))
    plt.close()
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
