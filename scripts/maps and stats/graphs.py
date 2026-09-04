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

    # reference_mineral_colors = ["#cc4c02","#3690c0","#88419d","#d7301f","#252525","#737373"]

    roads_df = gpd.read_file(
        os.path.join(incoming_data_path, "africa_roads", "africa_main_roads.gpkg"),
        layer="edges",
    )

    # roads_df["geometry"] = roads_df.geometry.centroid

    # print(roads_df.columns)

    ax_proj = get_projection(epsg=4326)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )
    # ax_plots = ax_plots.flatten()

    plot_africa_basemap(ax_plots)
    roads_df.plot()
    # ax = point_map_plotting_colors_width(ax,roads_df,
    #                                 output_column,
    #                                 values_range,
    #                                 point_classify_column="asset_type",
    #                                 #point_categories=["Unrefined","Refined"],
    #                                 #point_colors=["#e31a1c","#41ae76"],
    #                                 #point_labels=[s.upper() for s in ["Unrefined","Refined"]],
    #                                 #point_zorder=[6,7,8,9],
    #                                 #point_steps=8,
    #                                 #width_step = 40.0,
    #                                 #interpolation = 'fisher-jenks',
    #                                 legend_label="Paved and unpaved roads",
    #                                 legend_size=16,
    #                                 legend_weight=2.0,
    #                                 no_value_label="No output",
    #                                 )
    plt.tight_layout()
    save_fig(os.path.join(figures, "roads_test.png"))
    plt.close()


# africa_boundaries = gpd.read_file(os.path.join(
#                             incoming_data_path,
#                             "Africa_GIS Supporting Data",
#                             "a. Africa_GIS Shapefiles",
#                             "AFR_Political_ADM0_Boundaries.shp",
#                             "AFR_Political_ADM0_Boundaries.shp"))
# africa_boundaries.rename(columns={"DsgAttr03":"iso3"},inplace=True)
# #africa_boundaries.plot()
# #plt.show()

# roads = gpd.read_file(os.path.join(
#                  incoming_data_path,
#                  "africa_roads",
#                  "africa_main_roads.gpkg"))
# roads.plot()
# plt.show()

if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
