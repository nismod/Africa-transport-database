import os

import geopandas as gpd
from tqdm import tqdm

from aftdb.utils import load_config

tqdm.pandas()


def main(config):

    processed_data_path = config["paths"]["data"]

    roads_nodes = gpd.read_parquet(
        os.path.join(
            processed_data_path, "infrastructure", "africa_roads_nodes_FINAL.geoparquet"
        )
    )
    roads_edges = gpd.read_parquet(
        os.path.join(
            processed_data_path, "infrastructure", "africa_roads_edges_FINAL.geoparquet"
        )
    )

    roads_nodes = roads_nodes.rename(columns={"iso_a3": "iso3"})

    roads_edges = roads_edges.sort_values(by="id")
    mask = roads_edges["lanes"] > 8

    for i in roads_edges.index[mask]:  # Iterate over indices where "lanes" > 8
        if i > 0:  # Ensure it's not the first row
            roads_edges.at[i, "lanes"] = roads_edges.at[i - 1, "lanes"]

    print(roads_edges)
    print("Max lanes:", max(roads_edges["lanes"]))

    roads_edges = roads_edges.rename(
        columns={"from_iso_a3": "from_iso3", "to_iso_a3": "to_iso3"}
    )
    roads_edges = roads_edges[
        [
            "id",
            "from_id",
            "to_id",
            "from_iso3",
            "to_iso3",
            "component",
            "border_road",
            "corridor_name",
            "length_m",
            "osm_way_id",
            "tag_highway",
            "tag_surface",
            "tag_bridge",
            "tag_maxspeed",
            "tag_lanes",
            "bridge",
            "paved",
            "material",
            "lanes",
            "asset_type",
            "geometry",
        ]
    ]

    print(roads_nodes.columns)
    roads_nodes = roads_nodes[["id", "iso3", "component", "geometry"]]

    # Save files

    roads_edges = gpd.GeoDataFrame(roads_edges, geometry="geometry", crs="EPSG:4326")
    roads_nodes = gpd.GeoDataFrame(roads_nodes, geometry="geometry", crs="EPSG:4326")

    roads_nodes.to_file(
        os.path.join(
            processed_data_path, "infrastructure", "africa_roads_network.gpkg"
        ),
        layer="nodes",
        driver="GPKG",
    )
    roads_edges.to_file(
        os.path.join(
            processed_data_path, "infrastructure", "africa_roads_network.gpkg"
        ),
        layer="edges",
        driver="GPKG",
    )

    roads_nodes.to_parquet(
        os.path.join(
            processed_data_path, "infrastructure", "africa_roads_nodes_FINAL.geoparquet"
        )
    )
    roads_edges.to_parquet(
        os.path.join(
            processed_data_path, "infrastructure", "africa_roads_edges_FINAL.geoparquet"
        )
    )


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
