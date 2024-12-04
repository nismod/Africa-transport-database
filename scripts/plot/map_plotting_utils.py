"""Road network risks and adaptation maps
"""
import os
import sys
import json
from collections import namedtuple, OrderedDict
import ast
import math
import numpy as np
import geopandas as gpd
import pandas as pd
import cartopy.crs as ccrs
from shapely.geometry.point import Point
import cartopy.io.shapereader as shpreader
from matplotlib_scalebar.scalebar import ScaleBar
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import haversine_distances
import matplotlib.patches as mpatches
from shapely.geometry import LineString
from matplotlib.lines import Line2D
from scalebar import scale_bar
from htb import htb
import jenkspy

Style = namedtuple('Style', ['color', 'zindex', 'label'])
Style.__doc__ += """: class to hold an element's styles
Used to generate legend entries, apply uniform style to groups of map elements
(See network_map.py for example.)
"""

def load_config():
    """Read config.json
    """
    config_path = os.path.join(os.path.dirname(__file__), '..','..', 'config.json')
    with open(config_path, 'r') as config_fh:
        config = json.load(config_fh)
    return config

def within_extent(x, y, extent):
    """Test x, y coordinates against (xmin, xmax, ymin, ymax) extent
    """
    xmin, xmax, ymin, ymax = extent
    return (xmin < x) and (x < xmax) and (ymin < y) and (y < ymax)

def set_ax_bg(ax, color='#ffffff'):
    """Set axis background color
        white=#ffffff
        blue=#c6e0ff
    """
    # ax.background_patch.set_facecolor(color)
    ax.set_facecolor(color)

def get_projection(extent=(-74.04, -52.90, -20.29, -57.38), epsg=None):
    """Get map axes

    Default to Argentina extent // Lambert Conformal projection
    """
    if epsg == 4326:
        ax_proj = ccrs.PlateCarree()
    elif epsg is not None:
        ax_proj = ccrs.epsg(epsg)
    else:
        x0, x1, y0, y1 = extent
        cx = x0 + ((x1 - x0) / 2)
        cy = y0 + ((y1 - y0) / 2)
        ax_proj = ccrs.TransverseMercator(central_longitude=cx, central_latitude=cy)

    return ax_proj

def get_axes(ax,extent=(-74.04, -52.90, -20.29, -57.38), epsg=None):
    """Get map axes

    Default to Lambert Conformal projection
    """

    print(" * Setup axes")
    proj = get_projection(extent=(-74.04, -52.90, -20.29, -57.38), epsg=epsg)
    ax.set_extent(extent, crs=proj)
    set_ax_bg(ax)
    return ax

def plot_basemap_labels(ax,labels=None,label_column="Region",label_size=8.0,include_zorder=20):
    """Plot countries and regions background
    """
    proj = ccrs.PlateCarree()
    extent = ax.get_extent()
    if labels is not None:
        for label in labels.itertuples():
            text = getattr(label,label_column)
            geom = label.geometry.centroid
            x = float(geom.x)
            y = float(geom.y)
            size = label_size
            if within_extent(x, y, extent):
                ax.text(
                    x, y,
                    text,
                    alpha=0.7,
                    size=size,
                    horizontalalignment='center',
                    zorder = include_zorder,
                    transform=proj)

def plot_scale_bar(ax,scalebar_location=(0.88,0.05),scalebar_distance=25,zorder=20):
    """Draw a scale bar and direction arrow

    Parameters
    ----------
    ax : axes
    scalebar_location: tuple 
        location of scalebar on axes
    scalebar_distance : int
        length of the scalebar in km.
    zorder: int
        Order of scalebar on plot
    """
    scale_bar(ax, scalebar_location, scalebar_distance, color='k',zorder=zorder)

def scale_bar_and_direction(ax,arrow_location=(0.80,0.08),
                    scalebar_location=(0.88,0.05),
                    scalebar_distance=25,zorder=20):
    """Draw a scale bar and direction arrow

    Parameters
    ----------
    ax : axes
    length : int
        length of the scalebar in km.
    ax_crs: projection system of the axis
        to be provided in Jamaica grid coordinates
    location: tuple
        center of the scalebar in axis coordinates (ie. 0.5 is the middle of the plot)
    linewidth: float
        thickness of the scalebar.
    """
    # lat-lon limits
    scale_bar(ax, scalebar_location, scalebar_distance, color='k',zorder=zorder)

    ax.text(*arrow_location,transform=ax.transAxes, s='N', fontsize=14,zorder=zorder)
    arrow_location = np.asarray(arrow_location) + np.asarray((0.008,-0.03))
    # arrow_location[1] = arrow_location[1] - 0.02
    ax.arrow(*arrow_location, 0, 0.02, length_includes_head=True,
          head_width=0.01, head_length=0.04, overhang=0.2,transform=ax.transAxes, 
          facecolor='k',zorder=zorder)

def save_fig(output_filename):
    print(" * Save", os.path.basename(output_filename))
    plt.savefig(output_filename)

def plot_basemap(ax,include_labels=False):
    data_path = load_config()['paths']['data']  # "/Users/raghavpant/Desktop/china_study"
    boundary_gdp = gpd.read_file(os.path.join(data_path,'admin_boundaries','China_regions.gpkg'),encoding="utf-8")

    proj = ccrs.PlateCarree() # See more on projections here: https://scitools.org.uk/cartopy/docs/v0.15/crs/projections.html#cartopy-projections
    bounds = boundary_gdp.geometry.total_bounds # this gives your boundaries of the map as (xmin,ymin,xmax,ymax)
    # print (bounds)
    ax = get_axes(ax,extent = (bounds[0]+5,bounds[2]-10,bounds[1],bounds[3])) # extent requires (xmin,xmax,ymin,ymax) you might have to adjust the offsets a bit manually as I have done here by +/-0.1
    # labels = []
    # label_font = 10
    for boundary in boundary_gdp.itertuples():
        ax.add_geometries(
            [boundary.geometry],
            crs=proj,
            edgecolor='white',
            facecolor='#e0e0e0',
            zorder=1)

    if include_labels is True:
        # labels = pd.read_csv(os.path.join(data_path,'region_names.csv'))
        labels = boundary_gdp[['Region','geometry']]
    else:
        labels = None
    plot_basemap_labels(ax,labels=labels)
    plot_scale_bar(ax,scalebar_location=(0.57,0.04),scalebar_distance=100,zorder=20)
    return ax

def plot_global_basemap(ax,include_countries=None,
                        include_labels=False,label_countries=None,
                        scalebar_location=(0.88,0.05),
                        arrow_location=(0.82,0.08),
                        scalebar_distance=100,
                        label_size=6.0):
    data_path = load_config()['paths']['data']  # "/Users/raghavpant/Desktop/china_study"
    boundary_gdp = gpd.read_file(os.path.join(
                    data_path,'admin_boundaries',
                    'ne_10m_admin_0_countries',
                    'ne_10m_admin_0_countries.shp'),encoding="utf-8")
    if include_countries is not None:
        boundary_gdp = boundary_gdp[boundary_gdp["ADM0_A3_US"].isin(include_countries)]

    proj = ccrs.PlateCarree() # See more on projections here: https://scitools.org.uk/cartopy/docs/v0.15/crs/projections.html#cartopy-projections
    bounds = boundary_gdp.geometry.total_bounds # this gives your boundaries of the map as (xmin,ymin,xmax,ymax)
    if include_countries is not None:
        xmin = bounds[0]+2.0
        xmax = bounds[2]+6.0
        ymin = bounds[1]+4.0
        ymax = bounds[3]+2.0
    else:
        xmin = bounds[0]
        xmax = bounds[2]
        ymin = bounds[1]
        ymax = bounds[3]

    ax = get_axes(ax,extent = (xmin,xmax,ymin,ymax),epsg=4326) # extent requires (xmin,xmax,ymin,ymax) you might have to adjust the offsets a bit manually as I have done here by +/-0.1
    ax.set_facecolor("#c6e0ff")
    for boundary in boundary_gdp.itertuples():
        ax.add_geometries(
            [boundary.geometry],
            crs=proj,
            edgecolor='white',
            facecolor='#e0e0e0',
            zorder=1)

    if include_labels is True:
        # labels = pd.read_csv(os.path.join(data_path,'region_names.csv'))
        labels = boundary_gdp[['ADM0_A3_US','geometry']]
        labels = labels[labels["ADM0_A3_US"].isin(label_countries)]
        plot_basemap_labels(ax,labels=labels,label_column="ISO_A3_EH",label_size=label_size)
    
    scale_bar_and_direction(ax,arrow_location=arrow_location,
                    scalebar_location=scalebar_location,
                    scalebar_distance=100,zorder=20)
    return ax

def plot_africa_basemap(ax):
    data_path = load_config()['paths']['data']
    global_map_df = gpd.read_file(os.path.join(data_path,"admin_boundaries",
                                    "ne_10m_admin_0_countries",
                                    "ne_10m_admin_0_countries.shp"))
    global_lake_df = gpd.read_file(os.path.join(data_path,"admin_boundaries",
                                    "ne_10m_lakes",
                                    "ne_10m_lakes.shp"))
    africa_isos = list(
                    set(
                        global_map_df[
                            global_map_df["CONTINENT"] == "Africa"
                            ]["ADM0_A3_US"].values.tolist()
                        )
                    )
    del global_map_df
    ax = plot_global_basemap(ax,
                        include_countries=africa_isos)
    for lake in global_lake_df.itertuples():
        ax.add_geometries(
            [lake.geometry],
            crs=ccrs.PlateCarree(),
            edgecolor="#c6e0ff",
            facecolor="#c6e0ff",
            zorder=3)
    return ax

def plot_point_assets(ax,nodes,colors,size,marker,zorder,label):
    proj_lat_lon = ccrs.PlateCarree()
    ax.scatter(
        list(nodes.geometry.x),
        list(nodes.geometry.y),
        transform=proj_lat_lon,
        facecolor=colors,
        s=size,
        marker=marker,
        zorder=zorder,
        label=label
    )
    return ax

def plot_line_assets(ax,edges,colors,size,zorder):
    proj_lat_lon = ccrs.PlateCarree()
    ax.add_geometries(
        list(edges.geometry),
        crs=proj_lat_lon,
        linewidth=size,
        edgecolor=colors,
        facecolor='none',
        zorder=zorder
    )
    return ax

def legend_from_style_spec(ax, styles, fontsize = 10, loc='lower left'):
    """Plot legend
    """
    handles = [
        mpatches.Patch(color=style.color, label=style.label)
        for style in styles.values() if style.label is not None
    ]
    ax.legend(
        handles=handles,
        fontsize = fontsize,
        loc=loc
    )

def generate_weight_bins(weights, n_steps=9, width_step=0.01, interpolation='linear'):
    """Given a list of weight values, generate <n_steps> bins with a width
    value to use for plotting e.g. weighted network flow maps.
    """
    min_weight = min(weights)
    max_weight = max(weights)
    # print (min_weight,max_weight)
    if min(weights) > 0:
        min_order = math.floor(math.log10(min(weights)))
        min_decimal_one = min_weight/(10**min_order)
        min_nearest = round(min_weight/(10**min_order),1)
        if min_nearest > min_decimal_one:
            min_nearest = min_nearest - 0.1
        min_weight = (10**min_order)*min_nearest
    
    if max(weights) > 0:
        max_order = math.floor(math.log10(max(weights)))
        max_decimal_one = max_weight/(10**max_order)
        max_nearest = round(max_weight/(10**max_order),1)
        if max_nearest < max_decimal_one:
            max_nearest += 0.1
        max_weight = (10**max_order)*max_nearest

    width_by_range = OrderedDict()

    if interpolation == 'linear':
        mins = np.linspace(min_weight, max_weight, n_steps,endpoint=True)
        # mins = numpy.linspace(min_weight, max_weight, n_steps)
    elif interpolation == 'log':
        mins = np.geomspace(min_weight, max_weight, n_steps,endpoint=True)
        # mins = numpy.geomspace(min_weight, max_weight, n_steps)
    elif interpolation == 'quantiles':
        weights = np.array([min_weight] + list(weights) + [max_weight])
        mins = np.quantile(weights,q=np.linspace(0,1,n_steps,endpoint=True))
    elif interpolation == 'equal bins':
        mins = np.array([min_weight] + list(sorted(set([cut.right for cut in pd.qcut(sorted(weights),n_steps-1)])))[:-1] + [max_weight])  
    # elif interpolation == 'htb':
    #     weights = [min_weight] + list(weights) + [max_weight]
    #     mins = htb(weights)
    #     print (mins)
    elif interpolation == 'fisher-jenks':
        weights = np.array([min_weight] + list(weights) + [max_weight])
        mins = jenkspy.jenks_breaks(weights, n_classes=n_steps-1)
    else:
        raise ValueError('Interpolation must be log or linear')
    maxs = mins[1:]
    mins = mins[:-1]
    assert len(maxs) == len(mins)

    if interpolation in ('log','fisher-jenks'):
        scale = np.geomspace(1, len(mins),len(mins))
    else:
        scale = np.linspace(1,len(mins),len(mins))


    for i, (min_, max_) in enumerate(zip(mins, maxs)):
        width_by_range[(min_, max_)] = scale[i] * width_step

    return width_by_range

def find_significant_digits(divisor,significance,width_by_range):
    divisor = divisor
    significance_ndigits = significance
    max_sig = []
    for (i, ((nmin, nmax), line_style)) in enumerate(width_by_range.items()):
        if round(nmin/divisor, significance_ndigits) < round(nmax/divisor, significance_ndigits):
            max_sig.append(significance_ndigits)
        elif round(nmin/divisor, significance_ndigits+1) < round(nmax/divisor, significance_ndigits+1):
            max_sig.append(significance_ndigits+1)
        elif round(nmin/divisor, significance_ndigits+2) < round(nmax/divisor, significance_ndigits+2):
            max_sig.append(significance_ndigits+2)
        else:
            max_sig.append(significance_ndigits+3)

    significance_ndigits = max(max_sig)
    return significance_ndigits

def create_figure_legend(divisor,significance,
                        width_by_range,
                        max_weight,
                        legend_type,
                        legend_colors,
                        legend_weight,marker='o'):
    legend_handles = []
    significance_ndigits = find_significant_digits(divisor,significance,width_by_range)
    for (i, ((nmin, nmax), width)) in enumerate(width_by_range.items()):
        value_template = '{:,.' + str(significance_ndigits) + \
            'f} - {:,.' + str(significance_ndigits) + 'f}'
        label = value_template.format(
            round(nmin/divisor, significance_ndigits), round(nmax/divisor, significance_ndigits))

        if legend_type == 'marker':
            legend_handles.append(plt.plot([],[],
                                marker=marker, 
                                ms=width/legend_weight, 
                                ls="",
                                color=legend_colors[i],
                                label=label)[0])
        else:
            legend_handles.append(Line2D([0], [0], 
                            color=legend_colors[i], lw=width/legend_weight, label=label))

    return legend_handles

def line_map_plotting(ax,df,df_column,line_color,divisor,legend_label,value_label,
                    width_step=0.02,line_steps=4,plot_title=False,figure_path=False,significance=0):
    column = df_column

    weights = [
        getattr(record,column)
        for record in df.itertuples() if getattr(record,column) > 0
    ]
    max_weight = max(weights)
    width_by_range = generate_weight_bins(weights, width_step=width_step, n_steps=line_steps,interpolation='log')
    # print (width_by_range)
    line_geoms_by_category = {
        '1': [],
        '2': []
    }
    for record in df.itertuples():
        geom = record.geometry
        val = getattr(record,column)
        if val == 0:
            cat = '2'
        else:
            cat = '1'

        buffered_geom = None
        for (nmin, nmax), width in width_by_range.items():
            if nmin <= val and val < nmax:
                buffered_geom = geom.buffer(width)

        if buffered_geom is not None:
            line_geoms_by_category[cat].append(buffered_geom)
        else:
            print("Feature was outside range to plot", record.Index)

    styles = OrderedDict([
        ('1',  Style(color=line_color, zindex=9, label=value_label)),
        ('2', Style(color='#969696', zindex=7, label='No {}'.format(value_label)))
    ])

    for cat, geoms in line_geoms_by_category.items():
        cat_style = styles[cat]
        ax.add_geometries(
            geoms,
            crs=ccrs.PlateCarree(),
            linewidth=0,
            facecolor=cat_style.color,
            edgecolor='none',
            zorder=cat_style.zindex
        )

    legend_handles = create_figure_legend(divisor,
                        significance,
                        width_by_range,
                        max_weight,
                        'line',[line_color]*len(width_by_range),0.02)

    if plot_title:
        ax.set_title(plot_title, fontsize=9)
    print ('* Plotting ',plot_title)
    first_legend = ax.legend(handles=legend_handles,fontsize=9,title=f"$\\bf{legend_label}$",loc='lower left')
    ax.add_artist(first_legend)
    legend_from_style_spec(ax, styles,fontsize=8,loc='lower right')
    return ax

def point_map_plotting(ax,df,df_column,
                point_color,marker,divisor,
                legend_label,value_label,
                plot_title=False,figure_path=False,significance=0):
    column = df_column

    weights = [
        getattr(record,column)
        for record in df.itertuples() if getattr(record,column) > 0
    ]
    max_weight = max(weights)
    width_by_range = generate_weight_bins(weights, width_step=20, n_steps=4)
    line_geoms_by_category = {
        '1': [],
        '2': []
    }
    for record in df.itertuples():
        geom = record.geometry
        val = getattr(record,column)
        if val == 0:
            cat = '2'
        else:
            cat = '1'
        for (nmin, nmax), width in width_by_range.items():
            if val == 0:
                line_geoms_by_category[cat].append((geom,width/2))
                break
            elif nmin <= val and val < nmax:
                line_geoms_by_category[cat].append((geom,width))

    styles = OrderedDict([
        ('1',  Style(color=point_color, zindex=9, label=value_label)),
        ('2', Style(color='#969696', zindex=7, label='No {}'.format(value_label)))
    ])

    for cat, geoms in line_geoms_by_category.items():
        cat_style = styles[cat]
        for g in geoms:
            ax.scatter(
                g[0].x,
                g[0].y,
                transform=ccrs.PlateCarree(),
                facecolor=cat_style.color,
                s=g[1],
                marker=marker,
                zorder=cat_style.zindex
            )

    legend_handles = create_figure_legend(divisor,
                        significance,
                        width_by_range,
                        max_weight,
                        'marker',[point_color]*len(width_by_range),10,marker=marker)
    if plot_title:
        plt.title(plot_title, fontsize=9)
    first_legend = ax.legend(handles=legend_handles,fontsize=9,title=legend_label,loc='lower left')
    ax.add_artist(first_legend)
    print ('* Plotting ',plot_title)
    legend_from_style_spec(ax, styles,fontsize=8,loc='lower right')
    return ax

def line_map_plotting_colors_width(ax,df,df_column,
                        weights,
                        divisor,
                        legend_label,
                        value_label,
                        line_colors = ['#c6dbef','#6baed6','#2171b5','#08306b'],
                        no_value_color = '#969696',
                        line_steps = 4,
                        width_step = 0.02,
                        plot_title=False,
                        significance=0,
                        interpolation='log'):
    column = df_column
    all_colors = [no_value_color] + line_colors
    line_geoms_by_category = {'{}'.format(j):[] for j in range(len(all_colors))}
    # weights = [
    #     getattr(record,column)
    #     for record in df.itertuples() if getattr(record,column) > 0
    # ]
    # weights = [
    #     getattr(record,column)
    #     for record in df.itertuples()
    # ]
    max_weight = max(weights)
    width_by_range = generate_weight_bins(weights, 
                                width_step=width_step, 
                                n_steps=line_steps,
                                interpolation=interpolation)
    # print (min(weights),max(weights))
    # print (width_by_range)
    min_width = 0.8*width_step
    for record in df.itertuples():
        geom = record.geometry
        val = getattr(record,column)
        buffered_geom = None
        for (i, ((nmin, nmax), width)) in enumerate(width_by_range.items()):
            if val == 0:
                buffered_geom = geom.buffer(min_width)
                cat = str(i)
                # min_width = width
                break
            elif nmin <= val and val <= nmax:
                buffered_geom = geom.buffer(width)
                cat = str(i+1)

        if buffered_geom is not None:
            line_geoms_by_category[cat].append(buffered_geom)
        else:
            print("Feature was outside range to plot", record.Index)

    style_noflood = [(str(0),  Style(color=no_value_color, zindex=7,label='No {}'.format(value_label)))]
    styles = OrderedDict(style_noflood + [
        (str(j+1),  Style(color=line_colors[j], zindex=8+j,label=None)) for j in range(len(line_colors))
    ])
    # print ()
    for cat, geoms in line_geoms_by_category.items():
        # print ('cat',cat)
        cat_style = styles[cat]
        ax.add_geometries(
            geoms,
            crs=ccrs.PlateCarree(),
            linewidth=0,
            facecolor=cat_style.color,
            edgecolor='none',
            zorder=cat_style.zindex
        )

    legend_handles = create_figure_legend(divisor,
                        significance,
                        width_by_range,
                        max_weight,
                        'line',line_colors,width_step)
    if plot_title:
        ax.set_title(plot_title, fontsize=9)
    print ('* Plotting ',plot_title)
    # first_legend = ax.legend(handles=legend_handles,fontsize=11,title=legend_label,title_fontsize=12,loc='lower left')
    # # print (styles)
    # ax.add_artist(first_legend)
    # legend_from_style_spec(ax, styles,fontsize=12,loc='upper right')
    return ax, legend_handles

def point_map_plotting_color_width(ax,df,df_column,
                weights,marker,divisor,
                legend_label,value_label,
                point_colors = ['#c6dbef','#6baed6','#2171b5','#08306b'],
                no_value_color = '#969696',
                point_steps = 4,
                width_step = 20,
                plot_title=False,
                significance=0,
                interpolation='linear'):
    column = df_column

    all_colors = [no_value_color] + point_colors
    point_geoms_by_category = {'{}'.format(j):[] for j in range(len(all_colors))}
    # weights = [
    #     getattr(record,column)
    #     for record in df.itertuples() if getattr(record,column) > 0
    # ]
    max_weight = max(weights)
    width_by_range = generate_weight_bins(weights, 
                                width_step=width_step, 
                                n_steps=point_steps,
                                interpolation=interpolation)

    for record in df.itertuples():
        geom = record.geometry
        val = getattr(record,column)
        for (i, ((nmin, nmax), width)) in enumerate(width_by_range.items()):
            if val == 0:
                point_geoms_by_category[str(i)].append((geom,width/2))
                min_width = width/5
                break
            elif nmin <= val and val <= nmax:
                point_geoms_by_category[str(i+1)].append((geom,width))

    style_noflood = [(str(0),  Style(color=no_value_color, zindex=7,label='No {}'.format(value_label)))]
    styles = OrderedDict(style_noflood + [
        (str(j+1),  Style(color=point_colors[j], zindex=8+j,label=None)) for j in range(len(point_colors))
    ])

    for cat, geoms in point_geoms_by_category.items():
        cat_style = styles[cat]
        for g in geoms:
            ax.scatter(
                g[0].x,
                g[0].y,
                transform=ccrs.PlateCarree(),
                facecolor=cat_style.color,
                s=g[1],
                marker=marker,
                zorder=cat_style.zindex
            )

    legend_handles = create_figure_legend(divisor,
                        significance,
                        width_by_range,
                        1.0,
                        'marker',point_colors,10,marker=marker)
    if plot_title:
        plt.title(plot_title, fontsize=9)
    first_legend = ax.legend(handles=legend_handles,fontsize=11,title=f"{legend_label}",loc='lower left')
    ax.add_artist(first_legend)
    print ('* Plotting ',plot_title)
    legend_from_style_spec(ax, styles,fontsize=10,loc='lower right')
    return ax

def point_map_plotting_colors_width(ax,df,column,
                        weights,
                        point_classify_column=None,
                        point_categories=["1","2","3","4","5"],
                        point_colors=['#7bccc4','#6baed6','#807dba','#2171b5','#08306b'],
                        point_labels=[None,None,None,None,None],
                        point_zorder=[6,7,8,9,10],
                        marker="o",
                        divisor=1.0,
                        legend_label="Legend",
                        no_value_label="No value",
                        no_value_color="#969696",
                        point_steps=6,
                        width_step=0.02,
                        interpolation="linear",
                        legend_size=6,
                        legend_weight=2.5,
                        plot_title=False,
                        significance=0):


    layer_details = list(
                        zip(
                            point_categories,
                            point_colors,
                            point_labels,
                            point_zorder
                            )
                        )
    # weights = [
    #     getattr(record,column)
    #     for record in df.itertuples() if getattr(record,column) > 0
    # ]
    max_weight = max(weights)
    width_by_range = generate_weight_bins(weights, 
                                width_step=width_step, 
                                n_steps=point_steps,
                                interpolation=interpolation)
    # print (width_by_range)
    min_width = 0.2*width_step
    min_order = min(point_zorder)

    if point_classify_column is None:
        point_geoms_by_category = {j:[] for j in point_categories + [no_value_label]}
        for record in df.itertuples():
            geom = record.geometry
            val = getattr(record,column)
            for (i, ((nmin, nmax), width)) in enumerate(width_by_range.items()):
                if val == 0:
                    point_geoms_by_category[no_value_label].append((geom,min_width))
                    break
                elif nmin <= val and val < nmax:
                    point_geoms_by_category[str(i+1)].append((geom,width))

        legend_handles = create_figure_legend(divisor,
                        significance,
                        width_by_range,
                        1.0,
                        'marker',point_colors,
                        width_step/legend_weight,marker=marker)
        styles = OrderedDict([
            (cat,  
                Style(color=color, zindex=zorder,label=label)) for j,(cat,color,label,zorder) in enumerate(layer_details)
        ] + [(no_value_label,  Style(color=no_value_color, zindex=min_order-1,label=no_value_label))])
    else:
        # point_geoms_by_category = OrderedDict()
        # point_geoms_by_category[no_value_label] = []
        point_geoms_by_category = OrderedDict([(j,[]) for j in point_labels + [no_value_label]])
        # point_geoms_by_category[label] = []
        for j,(cat,color,label,zorder) in enumerate(layer_details):
            for record in df[df[point_classify_column] == cat].itertuples():
                geom = record.geometry
                val = getattr(record,column)
                buffered_geom = None
                geom_key = label
                for (i, ((nmin, nmax), width)) in enumerate(width_by_range.items()):
                    if val == 0:
                        point_geoms_by_category[no_value_label].append((geom,min_width))
                        # geom_key = no_value_label
                        # min_width = width
                        break
                    elif nmin <= val and val < nmax:
                        point_geoms_by_category[label].append((geom,width))


            legend_handles = create_figure_legend(divisor,
                        significance,
                        width_by_range,
                        1.0,
                        'marker',["#023858"]*point_steps,
                            width_step/legend_weight,marker=marker)

        styles = OrderedDict([
            (label,  
                Style(color=color, zindex=zorder,label=label)) for j,(cat,color,label,zorder) in enumerate(layer_details)
        ] + [(no_value_label,  Style(color=no_value_color, zindex=min_order-1,label=no_value_label))])
    for cat, geoms in point_geoms_by_category.items():
        cat_style = styles[cat]
        # print (geoms)
        for g in geoms:
            ax.scatter(
                g[0].x,
                g[0].y,
                transform=ccrs.PlateCarree(),
                facecolor=cat_style.color,
                s=g[1],
                alpha=0.8,
                marker=marker,
                zorder=cat_style.zindex
            )

    # legend_handles = create_figure_legend(divisor,
    #                     significance,
    #                     width_by_range,
    #                     max_weight,
    #                     'marker',point_colors,10,marker=marker)
    # if plot_title:
    #     plt.title(plot_title, fontsize=12)
    # first_legend = ax.legend(handles=legend_handles,fontsize=legend_size,
    #                         title=legend_label,title_fontsize=legend_size,
    #                         loc='upper right')
    # ax.add_artist(first_legend).set_zorder(20)
    print ('* Plotting ',plot_title)
    # legend_from_style_spec(ax, styles,fontsize=legend_size,loc='lower left')
    return ax, legend_handles