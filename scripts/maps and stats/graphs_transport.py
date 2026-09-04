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
    processed_data_path = config["paths"]["data"]
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

    roads_df = gpd.read_parquet(
        os.path.join(
            processed_data_path, "infrastructure", "africa_roads_edges_FINAL.geoparquet"
        )
    )

    print(roads_df.columns)

    roads_df.plot()
    plt.tight_layout()
    save_fig(os.path.join(figures, "roads_test.png"))
    plt.close()


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
