"""Basemaps for the database's maps and charts.

Every rule that draws a map calls one of the ``plot_*_basemap`` functions
here; the rest of this module is what they are built from.
"""

import os

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from aftdb.plot.scalebar import scale_bar


def within_extent(x, y, extent):
    """Test x, y coordinates against (xmin, xmax, ymin, ymax) extent"""
    xmin, xmax, ymin, ymax = extent
    return (xmin < x < xmax) and (ymin < y < ymax)


def set_ax_bg(ax, color="#ffffff"):
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


def get_axes(ax, extent=(-74.04, -52.90, -20.29, -57.38), epsg=None):
    """Get map axes

    Default to Lambert Conformal projection
    """

    print(" * Setup axes")
    proj = get_projection(extent=(-74.04, -52.90, -20.29, -57.38), epsg=epsg)
    ax.set_extent(extent, crs=proj)
    set_ax_bg(ax)
    return ax


def plot_basemap_labels(
    ax, labels=None, label_column="Region", label_size=8.0, include_zorder=20
):
    """Plot countries and regions background"""
    proj = ccrs.PlateCarree()
    extent = ax.get_extent()
    if labels is not None:
        for label in labels.itertuples():
            text = getattr(label, label_column)
            geom = label.geometry.centroid
            x = float(geom.x)
            y = float(geom.y)
            size = label_size
            if within_extent(x, y, extent):
                ax.text(
                    x,
                    y,
                    text,
                    alpha=0.7,
                    size=size,
                    horizontalalignment="center",
                    zorder=include_zorder,
                    transform=proj,
                )


def scale_bar_and_direction(
    ax,
    arrow_location=(0.80, 0.08),
    scalebar_location=(0.88, 0.05),
    scalebar_distance=25,
    zorder=20,
):
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
    scale_bar(ax, scalebar_location, scalebar_distance, color="k", zorder=zorder)

    ax.text(*arrow_location, transform=ax.transAxes, s="N", fontsize=14, zorder=zorder)
    arrow_location = np.asarray(arrow_location) + np.asarray((0.008, -0.03))
    # arrow_location[1] = arrow_location[1] - 0.02
    ax.arrow(
        *arrow_location,
        0,
        0.02,
        length_includes_head=True,
        head_width=0.01,
        head_length=0.04,
        overhang=0.2,
        transform=ax.transAxes,
        facecolor="k",
        zorder=zorder,
    )


def save_fig(output_filename):
    print(" * Save", os.path.basename(output_filename))
    plt.savefig(output_filename)


def plot_global_basemap(
    ax,
    countries,
    include_countries=None,
    include_labels=False,
    label_countries=None,
    scalebar_location=(0.88, 0.05),
    arrow_location=(0.82, 0.08),
    scalebar_distance=100,
    label_size=6.0,
    xmin_offset=2.0,
    xmax_offset=6.0,
    ymin_offset=4.0,
    ymax_offset=2.0,
):
    """Draw country outlines, either global or for a selection of countries

    Parameters
    ----------
    countries : str
        Path to the Natural Earth admin 0 countries shapefile.

    The ``*_offset`` arguments pad the extent around the selected countries, in
    degrees. They are only applied when ``include_countries`` is given.
    """
    boundary_gdp = gpd.read_file(countries, encoding="utf-8")
    if include_countries is not None:
        boundary_gdp = boundary_gdp[boundary_gdp["ADM0_A3_US"].isin(include_countries)]

    proj = ccrs.PlateCarree()  # See more on projections here: https://scitools.org.uk/cartopy/docs/v0.15/crs/projections.html#cartopy-projections
    bounds = (
        boundary_gdp.geometry.total_bounds
    )  # this gives your boundaries of the map as (xmin,ymin,xmax,ymax)
    if include_countries is not None:
        xmin = bounds[0] + xmin_offset
        xmax = bounds[2] + xmax_offset
        ymin = bounds[1] + ymin_offset
        ymax = bounds[3] + ymax_offset
    else:
        xmin = bounds[0]
        xmax = bounds[2]
        ymin = bounds[1]
        ymax = bounds[3]

    ax = get_axes(
        ax, extent=(xmin, xmax, ymin, ymax), epsg=4326
    )  # extent requires (xmin,xmax,ymin,ymax) you might have to adjust the offsets a bit manually as I have done here by +/-0.1
    ax.set_facecolor("#c6e0ff")
    for boundary in boundary_gdp.itertuples():
        ax.add_geometries(
            [boundary.geometry],
            crs=proj,
            edgecolor="white",
            facecolor="#e0e0e0",
            zorder=1,
        )

    if include_labels is True:
        labels = boundary_gdp[["ADM0_A3_US", "geometry"]]
        labels = labels[labels["ADM0_A3_US"].isin(label_countries)]
        plot_basemap_labels(
            ax, labels=labels, label_column="ISO_A3_EH", label_size=label_size
        )
    scale_bar_and_direction(
        ax,
        arrow_location=arrow_location,
        scalebar_location=scalebar_location,
        scalebar_distance=100,
        zorder=20,
    )
    return ax


def plot_africa_basemap(ax, countries, lakes, ccg_country_codes):
    """Africa basemap with the CCG countries picked out in a darker grey"""
    ccg_countries = pd.read_csv(ccg_country_codes)
    ccg_isos = ccg_countries[ccg_countries["ccg_country"] == 1][
        "iso_3digit_alpha"
    ].values.tolist()
    del ccg_countries

    global_map_df = gpd.read_file(countries)
    ccg_map_df = global_map_df[global_map_df["ADM0_A3_US"].isin(ccg_isos)]
    global_lake_df = gpd.read_file(lakes)
    africa_isos = list(
        set(
            global_map_df[global_map_df["CONTINENT"] == "Africa"][
                "ADM0_A3_US"
            ].values.tolist()
        )
    )
    del global_map_df
    ax = plot_global_basemap(ax, countries, include_countries=africa_isos)
    for ccg_country in ccg_map_df.itertuples():
        ax.add_geometries(
            [ccg_country.geometry],
            crs=ccrs.PlateCarree(),
            edgecolor="white",
            facecolor="#d9d9d9",
            zorder=2,
        )
    plot_basemap_labels(ax, labels=ccg_map_df, label_column="ADM0_A3_US", label_size=10)
    for lake in global_lake_df.itertuples():
        ax.add_geometries(
            [lake.geometry],
            crs=ccrs.PlateCarree(),
            edgecolor="#c6e0ff",
            facecolor="#c6e0ff",
            zorder=3,
        )
    return ax


def plot_africa_basemap2(ax, countries, lakes):
    """Africa basemap with country names, no CCG highlight and a wider extent"""
    global_map_df = gpd.read_file(countries)
    global_lake_df = gpd.read_file(lakes)

    # Get list of African countries
    africa_df = global_map_df[global_map_df["CONTINENT"] == "Africa"]

    # Plot African basemap
    africa_isos = list(set(africa_df["ADM0_A3_US"].values.tolist()))
    ax = plot_global_basemap(
        ax,
        countries,
        include_countries=africa_isos,
        xmin_offset=0.0,
        xmax_offset=50.0,
        ymin_offset=0.0,
        ymax_offset=50.0,
    )

    # Plot lakes
    for lake in global_lake_df.itertuples():
        ax.add_geometries(
            [lake.geometry],
            crs=ccrs.PlateCarree(),
            edgecolor="#c6e0ff",
            facecolor="#c6e0ff",
            zorder=3,
        )

    # Add country names with larger, dark grey font
    for _, country in africa_df.iterrows():
        if country.geometry.is_empty:
            continue

        # Get centroid to position the label
        centroid = country.geometry.centroid
        ax.text(
            centroid.x,
            centroid.y,
            country["NAME"],  # Country name column
            horizontalalignment="center",
            fontsize=9,  # Increased font size
            color="darkgrey",  # Dark grey color
            fontweight="bold",  # Bold for emphasis
            transform=ccrs.PlateCarree(),
            zorder=5,
        )

    # Get bounds and set equal white space on left and right
    bounds = africa_df.total_bounds  # [minx, miny, maxx, maxy]
    width = bounds[2] - bounds[0]

    # Add padding for equal white space
    padding = width * 0.05  # 5% padding on each side
    ax.set_extent(
        [
            bounds[0] - padding,
            bounds[2] + 2.6 * padding,
            bounds[1],
            bounds[3] + 1.1 * padding,
        ],
        crs=ccrs.PlateCarree(),
    )

    return ax
