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
@click.option("--road-edges", required=True, type=click.Path(exists=True))
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(road_edges, countries, lakes, output_figure):
    """Map the road network coloured by highway typology"""

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    roads_df = gpd.read_parquet(road_edges)

    # Filter the category we want to show
    allowed = {"primary", "secondary", "trunk", "motorway"}

    roads_df["tag_highway"] = roads_df["tag_highway"].apply(
        lambda x: x.capitalize() if str(x).lower() in allowed else "Other"
    )

    print(roads_df.columns)

    output_column = "tag_highway"

    ax = plot_africa_basemap2(ax_plots, countries, lakes)

    bold_font = font_manager.FontProperties(weight="bold", size=18)

    ax = plot_africa_basemap2(ax_plots, countries, lakes)
    # Categories in the order you want
    categories = ["Primary", "Secondary", "Trunk", "Motorway", "Other"]

    # Define colors in the same order
    colors = ["#a50026", "#1f78b4", "#33a02c", "#ffae42", "grey"]

    # Build a colormap
    cmap = ListedColormap(colors)
    roads_df[output_column] = pd.Categorical(
        roads_df[output_column], categories=categories, ordered=True
    )

    roads_df.plot(
        ax=ax,
        zorder=5,
        column=output_column,
        cmap=cmap,
        linewidth=1,
        legend=True,
        legend_kwds={
            "title": "Road Typology",
            "title_fontproperties": bold_font,
            "fontsize": 14,
            "loc": "lower left",
            "fancybox": True,
            "frameon": True,
            "edgecolor": "black",
            "facecolor": "white",
        },
        missing_kwds={"color": "lightgrey", "linewidth": 1},
    )

    plt.tight_layout()
    save_fig(output_figure)
    plt.close()


if __name__ == "__main__":
    main()
