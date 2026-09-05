import click

"""Road network risks and adaptation maps"""


import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    plot_africa_basemap2,
    save_fig,
)

tqdm.pandas()


@click.command()
@click.option("--airports", required=True, type=click.Path(exists=True))
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(airports, countries, lakes, output_figure):
    """Map airports sized by total annual seats"""

    marker_size_max = 2000
    air_nodes = gpd.read_file(
        airports,
        layer="nodes",
    )
    tmax = air_nodes["TotalSeats"].max()
    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    ax = plot_africa_basemap2(ax_plots, countries, lakes)
    air_nodes["markersize"] = marker_size_max * (air_nodes["TotalSeats"] / tmax) ** 0.5
    air_nodes = air_nodes.sort_values(by="TotalSeats", ascending=False)
    air_nodes.geometry.plot(
        ax=ax,
        color="#3690c0",
        edgecolor="none",
        markersize=air_nodes["markersize"],
        alpha=0.7,
        zorder=10,
    )

    ins = ax.inset_axes([0.02, -0.2, 0.15, 0.8])
    ins.spines[["top", "right", "bottom", "left"]].set_visible(False)
    ins.set_xticks([])
    ins.set_yticks([])
    ins.set_ylim([-3, 2])
    ins.set_xlim([-1, 1.5])
    ins.set_facecolor("#c6e0ff")
    xk = -0.6
    xt = -0.95
    t_key = 10 ** np.arange(1, np.ceil(np.log10(tmax)), 1)[:-1]
    t_key = t_key[::-1]
    Nk = t_key.size
    yk = np.linspace(-2.45, 0.8, Nk)
    yt = 1.5
    size_key = marker_size_max * (t_key / tmax) ** 0.5
    key = gpd.GeoDataFrame(geometry=gpd.points_from_xy(np.ones(Nk) * xk, yk))
    key.geometry.plot(ax=ins, markersize=size_key, color="#3690c0")
    ins.text(xt, yt, "Total Seats (annual)", weight="bold", va="center", fontsize=12)
    for k in range(Nk):
        ins.text(xk, yk[k], f"       {t_key[k]:,.0f}", va="center", fontsize=12)
    plt.tight_layout()
    save_fig(output_figure)
    plt.close()


if __name__ == "__main__":
    main()
