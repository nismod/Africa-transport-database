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
    config = load_config()
    incoming_data_path = config["paths"]["incoming_data"]
    figure_path = config["paths"]["figures"]

    figures = os.path.join(figure_path)

    roads_df = gpd.read_file(
        os.path.join(incoming_data_path, "africa_roads", "africa_main_roads.gpkg"),
        layer="edges",
    )

    ax_proj = get_projection(epsg=4326)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    plot_africa_basemap(ax_plots)
    roads_df.plot()
    plt.tight_layout()
    save_fig(os.path.join(figures, "roads_test.png"))
    plt.close()


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
