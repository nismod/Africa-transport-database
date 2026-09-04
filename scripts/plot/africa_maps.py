"""Road network risks and adaptation maps"""

import os

import matplotlib.pyplot as plt
from tqdm import tqdm

from aftdb.map.map_plotting_utils import *

tqdm.pandas()


def main(config):
    figure_path = config["paths"]["figures"]

    figures = os.path.join(figure_path)
    if os.path.exists(figures) is False:
        os.mkdir(figures)

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )
    plot_africa_basemap(ax_plots)
    plt.tight_layout()
    save_fig(os.path.join(figures, "africa_basemap.png"))
    plt.close()


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
