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
from shapely.geometry import LineString

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
    fig_legend.savefig(os.path.join(figures,"roads_corridors_legend_LAST.png"))
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

    label_spacing = 1000  # distance in meters/units between labels (adjust as needed)
    max_labels = 5  # optional: cap number of labels to avoid overplotting

    # for idx, row in grouped_gdf.iterrows():
    #     geom = row.geometry

    #     line_length = geom.length

    #     if line_length > label_spacing:
    #         num_labels = min(int(line_length // label_spacing), max_labels)
    #         for i in range(1, num_labels + 1):
    #             point = geom.interpolate(i * line_length / (num_labels + 1))
    #             ax.annotate(
    #                 text=str(idx + 1),
    #                 xy=(point.x, point.y),
    #                 xytext=(3, 10),
    #                 textcoords="offset points",
    #                 fontsize=9,
    #                 color="black",
    #                 alpha=1,
    #                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
    #                 zorder=8
    #             )
    #     else:
    #         centroid = geom.centroid
    #         ax.annotate(
    #             text=str(idx + 1),
    #             xy=(centroid.x, centroid.y),
    #             xytext=(3, 10),
    #             textcoords="offset points",
    #             fontsize=9,
    #             color="black",
    #             alpha=1,
    #             bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
    #             zorder=8
    #         )

# Add labels only once at the centroid of each group
    for idx, row in grouped_gdf.iterrows():
        if idx != 0 and idx != 6 and idx != 9 and idx != 13 and idx != 14 and idx != 15 and idx != 16 and idx != 20 and idx != 4 and idx != 3 and idx != 2 and idx != 1 and idx != 25 and idx != 9 and idx != 28: # and idx != 26:
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
        elif idx == 0:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(3, -15),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 20:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(-50, -40),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
                
        elif idx == 9:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(-10, 0),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 13:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(10, -240),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(-10, 200),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 14:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(3, 200),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(-55, -250),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 15:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(3, 20),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 16:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(3, -10),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 3:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(3, 5),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 4:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(3, 0),  # Small offset for visibility
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
                xytext=(-10, 10),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 2:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(-5, 10),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 25:
            if row.geometry is not None and not row.geometry.is_empty:
                centroid = row.geometry.centroid  # Get average centroid
                ax.annotate(
                text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                xy=(centroid.x, centroid.y),
                xytext=(-10,10),  # Small offset for visibility
                textcoords="offset points",
                fontsize=9,
                color="black",
                alpha=1,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                zorder=8
                )
        elif idx == 6:
                if row.geometry is not None and not row.geometry.is_empty:
                    centroid = row.geometry.centroid  # Get average centroid
                    ax.annotate(
                    text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                    xy=(centroid.x, centroid.y),
                    xytext=(150, -5),  # Small offset for visibility
                    textcoords="offset points",
                    fontsize=9,
                    color="black",
                    alpha=1,
                    bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                    zorder=8
                    )
                    ax.annotate(
                    text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                    xy=(centroid.x, centroid.y),
                    xytext=(-100, 10),  # Small offset for visibility
                    textcoords="offset points",
                    fontsize=9,
                    color="black",
                    alpha=1,
                    bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                    zorder=8
                    )
        elif idx == 9:
                if row.geometry is not None and not row.geometry.is_empty:
                    centroid = row.geometry.centroid  # Get average centroid
                    ax.annotate(
                    text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                    xy=(centroid.x, centroid.y),
                    xytext=(10, 15),  # Small offset for visibility
                    textcoords="offset points",
                    fontsize=9,
                    color="black",
                    alpha=1,
                    bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                    zorder=8
                    )
        elif idx == 28:
            if row.geometry is not None and not row.geometry.is_empty:
                    centroid = row.geometry.centroid  # Get average centroid
                    ax.annotate(
                    text=str(idx + 1),  # Show corridor_id (+1 for human-friendly numbering)
                    xy=(centroid.x, centroid.y),
                    xytext=(3, 40),  # Small offset for visibility
                    textcoords="offset points",
                    fontsize=9,
                    color="black",
                    alpha=1,
                    bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                    zorder=8
                    )
                    # Second label (below)
                    ax.annotate(
                        text=str(idx + 1),
                        xy=(centroid.x, centroid.y),
                        xytext=(20, -15),  # This pushes the label down
                        textcoords="offset points",
                        fontsize=9,
                        color="black",
                        alpha=1,
                        bbox=dict(boxstyle="round,pad=0.3", edgecolor="none", facecolor="white", alpha=0.6),
                        zorder=8
                    )
                    

    plt.tight_layout()
    
    save_fig(os.path.join(figures,"roads_corridors_LAST.png"))
    plt.close()
    
    
    
    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
