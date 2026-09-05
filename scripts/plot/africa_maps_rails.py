import click

"""Road network risks and adaptation maps"""


import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    plot_africa_basemap2,
    save_fig,
)

tqdm.pandas()


@click.command()
@click.option("--railways", required=True, type=click.Path(exists=True))
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(railways, countries, lakes, output_figure):
    """Map the railway network coloured by gauge"""

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    rail_df = gpd.read_file(
        railways,
        layer="edges",
    )

    output_column = "gauge"

    rail_df[output_column] = pd.Categorical(rail_df[output_column])

    rail_df[output_column] = rail_df[output_column].cat.add_categories("Not Known")
    rail_df[output_column] = rail_df[output_column].fillna("Not Known")

    # Create a font property for bold text
    bold_font = font_manager.FontProperties(weight="bold", size=18)

    ax = plot_africa_basemap2(ax_plots, countries, lakes)

    num_colors = len(rail_df["gauge"].unique())
    colormap = [
        "#9e0142",
        "#d53e4f",
        "#f46d43",
        "#fdae61",
        "#abdda4",
        "#66c2a5",
        "#3288bd",
        "#5e4fa2",
        "lightgrey",
    ]
    custom_cmap = ListedColormap(colormap[:num_colors])
    # Get color values from the colormap

    rail_df.plot(
        ax=ax,
        zorder=5,
        column=output_column,
        cmap=custom_cmap,
        linewidth=3,
        legend=True,
        legend_kwds={
            "title": "Railway Gauges",
            "title_fontproperties": bold_font,
            "fontsize": 14,
            "loc": (0.1, 0.1),
            "fancybox": True,
            "frameon": True,
            "edgecolor": "black",
            "facecolor": "white",
        },
        missing_kwds={"color": "lightgrey", "linewidth": 1},
    )
    # Get the legend and modify labels to uppercase
    leg = ax.get_legend()
    for text in leg.get_texts():
        text.set_text(text.get_text().capitalize())

    plt.tight_layout()
    save_fig(output_figure)


if __name__ == "__main__":
    main()
