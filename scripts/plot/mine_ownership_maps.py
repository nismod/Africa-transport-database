#!/usr/bin/env python
# coding: utf-8

import sys
import os
import ast
import pandas as pd
import numpy as np
pd.options.mode.copy_on_write = True
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from map_plotting_utils import *
from tqdm import tqdm
tqdm.pandas()

config = load_config()
processed_data_path = config['paths']['data']
output_data_path = config['paths']['results']
figure_path = config['paths']['figures']

def draw_pie(dist, xpos, ypos, size, color_map, ax=None):
    """A function to plot pie charts on a map"""
    """https://gis.stackexchange.com/questions/429006/making-spatial-pie-chart-using-two-columns-in-geopandas"""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10,8))

    # for incremental pie slices
    cumsum = np.cumsum(dist)
    cumsum = cumsum/ cumsum[-1]
    pie = [0] + cumsum.tolist()

    xy = []
    s = []
    for r1, r2 in zip(pie[:-1], pie[1:]):
        angles = np.linspace(2 * np.pi * r1, 2 * np.pi * r2)
        x = [0] + np.cos(angles).tolist()
        y = [0] + np.sin(angles).tolist()

        xy1 = np.column_stack([x, y])
        s1 = np.abs(xy1).max()

        xy.append(xy1)
        s.append(s1)
    for xyi, si in zip(xy,s):
        ax.scatter([xpos], [ypos], marker=xyi, s=size*si**2, linewidth=0, edgecolor='none',color=color_map.pop(0))

    return ax

def main():
    figures = os.path.join(figure_path,"mine_ownership")
    os.makedirs(figures,exist_ok=True)
    
    global_df = gpd.read_file(os.path.join(
                    processed_data_path,'admin_boundaries',
                    'ne_10m_admin_0_countries',
                    'ne_10m_admin_0_countries.shp'),encoding="utf-8")
    global_df = global_df[global_df["CONTINENT"] != 'Antarctica']
    continents = list(set(global_df["CONTINENT"].values.tolist()))
    countries = list(set(global_df["ADM0_A3"].values.tolist()))
    centroid_df = pd.read_csv(
                    os.path.join(
                        processed_data_path,
                        "admin_boundaries/centroids",
                        "countries_iso3_code.csv"
                        )
                    )
    centroid_df["geometry"] = gpd.points_from_xy(
                                    centroid_df["longitude_shift"],
                                    centroid_df["latitude_shift"])
    
        
    _,_,xl,yl = map_background_and_bounds(include_continents=continents)
    dxl = abs(np.diff(xl))[0]
    dyl = abs(np.diff(yl))[0]
    w = 0.003
    dt = 0.05
    panel_span = 2
    marker_size_max = 1500.0
    commodities = [
                    'Manganese', 'Uranium', 
                    'Bauxite', 'Copper', 
                    'Nickel', 'Iron Ore', 
                    'Gold', 'Cobalt', 
                    'Silver', 'Lithium', 
                    'Lead', 'Zinc'
                ]
    commodities_colors = [
                            "#e41a1c",
                            "#377eb8",
                            "#4daf4a",
                            "#1d91c0",
                            "#ff7f00",
                            "#49006a",
                            "#a65628",
                            "#f781bf",
                            "#999999",
                            "#ce1256",
                            "#a63603",
                            "#084081"
                        ] 
    color_df = pd.DataFrame(list(zip(commodities,commodities_colors)),columns=["commodity","color"])
    # textfontsize = 12

    """Test Map"""

    figwidth = 12
    figheight = figwidth/(1+1*w)/dxl*dyl/(1-dt)
    fig = plt.figure(figsize=(figwidth,figheight))
    # plt.subplots_adjust(left=0, bottom=0, right=1, top=1-dt,wspace=w)
    ax = plt.subplot2grid([1,1],[0,0],1,colspan=panel_span)
    ax.spines[['top','right','bottom','left']].set_visible(True)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    
    ax = plot_global_basemap(
                ax,
                include_continents=continents,
                include_countries=countries,
                facecolor=None
                )

    plt.tight_layout()
    save_fig(os.path.join(figures,"global_basemap"))
    plt.close()

    """Read the mine ownership data
    """
    ownership_df = pd.read_csv(os.path.join(output_data_path,"mine_ownership","df_maps_2022.csv"))
    df = pd.merge(
                centroid_df[["ADM0_A3","geometry"]],
                ownership_df,how="left",left_on=["ADM0_A3"],right_on=["region mine"]).fillna(0)
    df = df[df["Total"]>0]
    df["Local"] = df["Local"]*df["Total"]
    df["Unknown"] = df["Unknown"]*df["Total"]
    df["Foreign"] = df["Total"] - df["Local"] - df["Unknown"]
    df = pd.merge(df,color_df,how="left",on=["commodity"])
    df = gpd.GeoDataFrame(df,geometry="geometry",crs="EPSG:4326")
    tmax = df["Total"].max()

    sc_dfs = [
                ("Total","a. Total tonnage produced",df,0,1,1,panel_span),
                ("Local","b. Tonnage produced by domestic owners",df,0,3,1,panel_span),
                ("Foreign","c. Tonnage produced by foreign owners",df,1,1,1,panel_span),
                ("Unknown","d. Tonnage produced by unknown owners",df,1,3,1,panel_span),
                ("key","key",pd.DataFrame(),0,0,2,1)]
    figwidth = 24
    figheight = figwidth/(2+2*w)/dxl*dyl/(1-dt)
    figheight = 8
    fig = plt.figure(figsize=(figwidth,figheight))
    # plt.subplots_adjust(left=0, bottom=0, right=1, top=1-dt,wspace=0)
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1-dt,wspace=0,hspace=0)
    for jdx, (sc_n,sc_t,gdf,rowpos,colpos,rowspan,colspan) in enumerate(sc_dfs):
        ax = plt.subplot2grid([2,5],[rowpos,colpos],rowspan=rowspan,colspan=colspan)
        ax.spines[['top','right','bottom','left']].set_visible(False)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
        if sc_n == "key":
            ax.set_ylim(yl)
            ax.set_xlim(xl[0]+0.5*dxl,xl[1])
            xk = xl[0] + 0.65*dxl
            xt = xk-0.04*dxl
            keys = ['tonnage','mineral']
            for ky in range(len(keys)):
                key = keys[ky]
                if key == 'tonnage':
                    tonnage_key = 10**np.arange(1,np.ceil(np.log10(tmax)),1)[2:]
                    tonnage_key = tonnage_key[::-1]
                    Nk = tonnage_key.size
                    yk = yl[0] + np.linspace(0.05*dyl,0.4*dyl,Nk) + 0.4*ky*dyl
                    yt = 1.4*(yk[-1]+np.diff(yk[-3:-1]))
                    size_key = marker_size_max*(tonnage_key/tmax)**0.5
                    key = gpd.GeoDataFrame(geometry=gpd.points_from_xy(np.ones(Nk)*xk, yk))
                    key.geometry.plot(ax=ax,markersize=size_key,color='k')
                    ax.text(xt,yt,'Mine annual output (tonnes)',weight='bold',va='center',fontsize=16)
                    for k in range(Nk):
                        ax.text(xk,yk[k],'     {:,.0f}'.format(tonnage_key[k]),va='center',fontsize=13)
                else:
                    Nk = len(commodities)
                    yk = yl[0] + np.linspace(0.10*dyl,0.5*dyl,Nk) + 0.4*ky*dyl
                    yt = yk[-1]+np.diff(yk[-3:-1])
                    ax.text(xt,yt,'Mineral produced',weight='bold',va='center',fontsize=16)
                    for k in range(Nk):
                        ax.text(xk,yk[k],'   '+commodities[k].capitalize(),va='center',fontsize=13)
                        ax.plot(xk,yk[k],'s',
                                mfc=commodities_colors[k],
                                mec=commodities_colors[k],
                                ms=10)
        else:
            ax = plot_global_basemap(
                        ax,
                        include_continents=continents,
                        include_countries=countries,
                        facecolor=None
                        )
            gdf["markersize"] = marker_size_max*(gdf[sc_n]/tmax)**0.5
            gdf = gdf.sort_values(by=sc_n,ascending=False)
            gdf.geometry.plot(
                ax=ax, 
                color=df["color"], 
                edgecolor='none',
                markersize=gdf["markersize"],
                alpha=0.8)
            ax.text(
                        0.95*xl[0],0.90*yl[1],
                        sc_t,
                        fontsize=18,weight='bold',ha='left'
                    )

    plt.tight_layout()
    save_fig(os.path.join(figures,"mine_totals.svg"))
    plt.close()

    """Ownership Map"""

    sum_cols = ["Total","Local","Foreign","Unknown"]
    marker_size_max = 3000.0
    df = df.groupby(["region mine"]).agg(dict([(c,"sum") for c in sum_cols])).reset_index()
    df["Foreign"] = np.where(df["Foreign"] < 0, 0,df["Foreign"])
    df = pd.merge(
                centroid_df[["ADM0_A3","geometry"]],
                df,how="left",left_on=["ADM0_A3"],right_on=["region mine"]).fillna(0)
    df = df[df["Total"]>0]
    df = df.sort_values(by="Total",ascending=False)
    tmax = df["Total"].max()
    threshold = tmax
    pie_colors = ["#1f78b4","#e31a1c","#4d4d4d"]
    figwidth = 12
    figheight = figwidth/(1+1*w)/dxl*dyl/(1-dt)
    fig = plt.figure(figsize=(figwidth,figheight))
    # plt.subplots_adjust(left=0, bottom=0, right=1, top=1-dt,wspace=w)
    ax = plt.subplot2grid([1,1],[0,0],1,colspan=panel_span)
    ax.spines[['top','right','bottom','left']].set_visible(False)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    
    ax = plot_global_basemap(
                ax,
                include_continents=continents,
                include_countries=countries,
                facecolor=None
                )
    for row in df.itertuples():
        values = [row.Local,row.Foreign,row.Unknown]
        colors = pie_colors.copy()
        draw_pie(dist=values, 
                xpos=row.geometry.x, 
                ypos=row.geometry.y, 
                size=marker_size_max*(row.Total/tmax)**0.5, 
                color_map=colors,
                ax=ax)
        ax.scatter(
                    [row.geometry.x],[row.geometry.y],
                    s=0.2*marker_size_max*(row.Total/tmax)**0.5,
                    color="#ffffff")
        if row.Total > threshold:
            ax.text(row.geometry.x,row.geometry.y,row.ADM0_A3,ha='center',fontsize=5.5)

    ins = ax.inset_axes([-0.05,-0.05,0.2,0.8])
    # pie_colors = ["#1f78b4","#e31a1c","#969696"]
    # create inset plot
    keys = ['tonnage','Ownership']
    ins.spines[['top','right','bottom','left']].set_visible(False)
    ins.set_xticks([])
    ins.set_yticks([])
    ins.set_ylim([-3,2])
    ins.set_xlim([-1,1.5])
    xk = -0.6
    xt = -0.95
    for ky in range(len(keys)):
        key = keys[ky]
        if key == 'tonnage':
            tonnage_key = 10**np.arange(1,np.ceil(np.log10(tmax)),1)[:-1]
            tonnage_key = tonnage_key[::-1]
            Nk = tonnage_key.size
            yk = np.linspace(-2.45,0.8,Nk)
            yt = 1.0
            size_key = marker_size_max*(tonnage_key/tmax)**0.5
            key = gpd.GeoDataFrame(geometry=gpd.points_from_xy(np.ones(Nk)*xk, yk))
            key.geometry.plot(ax=ins,markersize=size_key,color='k')
            ins.text(xt,yt,'Mine annual output (tonnes)',weight='bold',va='center',fontsize=10)
            for k in range(Nk):
                ins.text(xk,yk[k],'       {:,.0f}'.format(tonnage_key[k]),va='center',fontsize=10)
            # for n, p in enumerate(size_key):
            #     circle = Circle(
            #                         (xk, yk[n]), 
            #                         radius=(p)**0.5, 
            #                         fc='k')
            #     ax.add_artist(circle)
        else:
            commodities = ["Unknown","Foreign","Domestic"]
            pie_colors = ["#4d4d4d","#e31a1c","#1f78b4"]
            Nk = len(commodities)
            yk = np.linspace(1.2,1.8,Nk)
            yt = 2.0
            ins.text(xt,yt,'Ownership',weight='bold',va='center',fontsize=10)
            for k in range(Nk):
                ins.text(xk,yk[k],'   '+commodities[k].capitalize(),va='center',fontsize=10)
                ins.plot(xk,yk[k],'s',
                        mfc=pie_colors[k],
                        mec=pie_colors[k],
                        ms=10)


    plt.tight_layout()
    save_fig(os.path.join(figures,"country_totals_by_ownership.svg"))
    plt.close()

if __name__ == '__main__':
    main()