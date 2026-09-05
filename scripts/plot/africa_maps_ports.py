import click

"""Road network risks and adaptation maps"""


import geopandas as gpd
import matplotlib.pyplot as plt
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    plot_africa_basemap,
    save_fig,
)

tqdm.pandas()


@click.command()
@click.option("--maritime", required=True, type=click.Path(exists=True))
@click.option("--iww", required=True, type=click.Path(exists=True))
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--ccg-countries", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(maritime, iww, countries, lakes, ccg_countries, output_figure):
    """Map maritime ports, inland ports and their routes"""

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    maritime_edges = gpd.read_file(
        maritime,
        layer="edges",
    )
    maritime_nodes = gpd.read_file(
        maritime,
        layer="nodes",
    )
    IWW_edges = gpd.read_file(
        iww,
        layer="edges",
    )
    IWW_nodes = gpd.read_file(
        iww,
        layer="nodes",
    )

    maritime_nodes = maritime_nodes[maritime_nodes["infra"].isin(["port"])]
    IWW_nodes = IWW_nodes[IWW_nodes["infra"].isin(["IWW port"])]

    maritime_nodes["geometry"] = maritime_nodes.geometry.centroid
    IWW_nodes["geometry"] = IWW_nodes.geometry.centroid

    ax = plot_africa_basemap(ax_plots, countries, lakes, ccg_countries)

    ax = plot_africa_basemap(ax_plots, countries, lakes, ccg_countries)
    maritime_nodes.plot(
        ax=ax, zorder=4, color="blue", markersize=10, label="maritime port"
    )
    IWW_nodes.plot(ax=ax, zorder=4, color="royalblue", markersize=10, label="IWW port")
    maritime_edges.plot(
        ax=ax, zorder=4, color="darkblue", linewidth=1, label="maritime route"
    )
    IWW_edges.plot(
        ax=ax, zorder=4, color="cornflowerblue", linewidth=1, label="IWW route"
    )
    plt.legend(loc="upper right")

    plt.tight_layout()
    save_fig(output_figure)
    plt.close()


if __name__ == "__main__":
    main()
