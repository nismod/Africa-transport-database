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
import matplotlib.patches as mpatches

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
    
    roads_df['corridor_name'] = roads_df['corridor_name'].str.split('/')

    # Explode the data to separate overlapping corridors into individual rows
    gdf_exploded = roads_df.explode('corridor_name', ignore_index=True)
    gdf_exploded['corridor_id'], corridor_labels = pd.factorize(gdf_exploded['corridor_name'])
    # roads_df["geometry"] = roads_df.geometry.centroid
    # gdf_exploded['corridor_id'] = gdf_exploded['corridor_id'].fillna(-1)
    gdf_exploded = gdf_exploded.to_crs(epsg=4326)
    output_column = "corridor_id"
    
    bold_font = font_manager.FontProperties(weight='bold',size=18)
     
    fig, ax_plots = plt.subplots(1,1,
                    subplot_kw={'projection': ax_proj},
                    figsize=(12,12),
                    dpi=500)
    # Define color mapping with grey for 'Missing' or -1
    n_colors = len(corridor_labels)
    colors = plt.cm.Set1.colors
    color_map = {i: colors[i % len(colors)] for i in range(n_colors)}
    # color_map[-1] = 'grey'  # Assign grey to missing corridors
    legend_items = [mpatches.Patch(color=color_map[i], label=f"{i + 1} - {name}" if name != 'Missing' else 'Other')
    for i, name in enumerate(corridor_labels)
    ]
  
    fig_legend, ax_legend = plt.subplots(figsize=(12, 12))
    legend=ax_legend.legend(handles=legend_items, title="Corridor Names", title_fontproperties = bold_font,ncol=2, fontsize= 9,loc='center' ,fancybox=True,frameon= True,edgecolor= 'black',facecolor='white')

    ax_legend.axis('off')
    # Save the legend as a separate image
    fig_legend.savefig(os.path.join(figures,"roads_corridors_legend.png"))
    plt.close()

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    
    ax = plot_africa_basemap2(ax_plots)
    # ax.set_aspect('equal')
    gdf_na = gdf_exploded[gdf_exploded['corridor_name'].isna()]
    gdf_colored = gdf_exploded[~gdf_exploded['corridor_name'].isna()]

# Plot NaN/grey geometries first (lower zorder)
    if not gdf_na.empty:
        gdf_na.plot(
            ax=ax,
            zorder=5,
            linewidth=0.5,
            color='grey',
            legend=False
          )

# Plot colored geometries on top (higher zorder)
    gdf_colored.plot(
        ax=ax,
        zorder=7,  # Higher order
        column=output_column,
        linewidth=3,
        legend=False,
        color=gdf_colored['corridor_id'].map(color_map)
        )

    grouped_gdf = gdf_exploded.dissolve(by='corridor_id')
    grouped_gdf = grouped_gdf[~grouped_gdf['corridor_name'].isna()]



# Add labels only once at the centroid of each group
    for idx, row in grouped_gdf.iterrows():
        if idx != 1 and idx != 7:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(3, 10),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 1:
                if row.geometry is not None and not row.geometry.is_empty:
                    centroid = row.geometry.centroid  # Get average centroid
                    ax.annotate(
                    text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                    xy=(centroid.x, centroid.y),
                    xytext=(3, 50),  # Small offset for visibility
                    textcoords="offset points",
                    fontsize=9,
                    color="black",
                    alpha=1,
                    bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                    zorder=8
                    )
        elif idx == 7:
            if row.geometry is not None and not row.geometry.is_empty:
                    centroid = row.geometry.centroid  # Get average centroid
                    ax.annotate(
                    text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                    xy=(centroid.x, centroid.y),
                    xytext=(1, 180),  # Small offset for visibility
                    textcoords="offset points",
                    fontsize=9,
                    color="black",
                    alpha=1,
                    bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                    zorder=8
                    )


    plt.tight_layout()
    save_fig(os.path.join(figures,"roads_corridors2.png"))
    plt.close()
    
    
    
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
