"""Road network risks and adaptation maps"""

import os

import geopandas as gpd
import matplotlib.pyplot as plt
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    load_config,
    plot_africa_basemap,
    save_fig,
)

tqdm.pandas()


def main(config):
    data_path = config["paths"]["data"]
    figure_path = config["paths"]["figures"]

    figures = os.path.join(figure_path)
    if os.path.exists(figures) is False:
        os.mkdir(figures)

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    maritime_edges = gpd.read_file(
        os.path.join(data_path, "infrastructure", "africa_maritime_network.gpkg"),
        layer="edges",
    )
    maritime_nodes = gpd.read_file(
        os.path.join(data_path, "infrastructure", "africa_maritime_network.gpkg"),
        layer="nodes",
    )
    IWW_edges = gpd.read_file(
        os.path.join(data_path, "infrastructure", "africa_iww_network.gpkg"),
        layer="edges",
    )
    IWW_nodes = gpd.read_file(
        os.path.join(data_path, "infrastructure", "africa_iww_network.gpkg"),
        layer="nodes",
    )

    maritime_nodes = maritime_nodes[maritime_nodes["infra"].isin(["port"])]
    IWW_nodes = IWW_nodes[IWW_nodes["infra"].isin(["IWW port"])]

    maritime_nodes["geometry"] = maritime_nodes.geometry.centroid
    IWW_nodes["geometry"] = IWW_nodes.geometry.centroid

    ax = plot_africa_basemap(ax_plots)

    ax = plot_africa_basemap(ax_plots)
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
    save_fig(os.path.join(figures, "IWW_and_ports.png"))
    plt.close()


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
