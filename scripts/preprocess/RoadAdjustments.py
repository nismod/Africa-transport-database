import click
import geopandas as gpd
import numpy as np
import pandas as pd
from tqdm import tqdm

from aftdb.utils import components

tqdm.pandas()


@click.command()
@click.option("--lobito-edges", required=True, type=click.Path(exists=True))
@click.option("--ta-edges", required=True, type=click.Path(exists=True))
@click.option("--tsh-edges", required=True, type=click.Path(exists=True))
@click.option("--ns-edges", required=True, type=click.Path(exists=True))
@click.option("--mdg-edges", required=True, type=click.Path(exists=True))
@click.option("--road-edges", required=True, type=click.Path(exists=True))
@click.option("--road-nodes", required=True, type=click.Path(exists=True))
@click.option("--output-nodes", required=True, type=click.Path())
@click.option("--output-edges", required=True, type=click.Path())
@click.option("--output-network", required=True, type=click.Path())
def main(
    lobito_edges,
    ta_edges,
    tsh_edges,
    ns_edges,
    mdg_edges,
    road_edges,
    road_nodes,
    output_nodes,
    output_edges,
    output_network,
):
    """Merge the per-corridor road extracts into the final road network"""
    epsg_meters = 3395  # To convert geometries to measure distances in meters

    # Read the road edges data for Africa
    node_id_column = "id"

    lobito_edges_df = gpd.read_parquet(lobito_edges)

    ta_edges_df = gpd.read_parquet(ta_edges)

    tsh_edges_df = gpd.read_parquet(tsh_edges)

    ns_edges_df = gpd.read_parquet(ns_edges)

    mdg_edges_df = gpd.read_parquet(mdg_edges)

    road_edges_df = gpd.read_parquet(road_edges)

    road_nodes_df = gpd.read_parquet(road_nodes)

    mdg_edges_df = mdg_edges_df[
        mdg_edges_df["corridor_name"] == "Madagascar – Port Beira Corridor"
    ]

    ns_edges_df = ns_edges_df[
        ns_edges_df["corridor_name"] == "North-South Corridor (North section)"
    ]

    lobito_edges_df = lobito_edges_df[
        lobito_edges_df["corridor_name"] == "Lobito Corridor"
    ]

    ta_edges_df = ta_edges_df[ta_edges_df["corridor_name"] == "Tunisia – Algeria"]

    tsh_edges_df = tsh_edges_df[
        tsh_edges_df["corridor_name"] == "Central Corridor of the TSH"
    ]

    road_edges_df = road_edges_df.to_crs(epsg=epsg_meters)
    mdg_edges_df = mdg_edges_df.to_crs(epsg=epsg_meters)
    ns_edges_df = ns_edges_df.to_crs(epsg=epsg_meters)
    lobito_edges_df = lobito_edges_df.to_crs(epsg=epsg_meters)
    ta_edges_df = ta_edges_df.to_crs(epsg=epsg_meters)
    tsh_edges_df = tsh_edges_df.to_crs(epsg=epsg_meters)

    road_edges_df = pd.concat(
        [
            road_edges_df,
            mdg_edges_df,
            ns_edges_df,
            lobito_edges_df,
            ta_edges_df,
            tsh_edges_df,
        ]
    )

    connected_nodes = list(
        set(road_edges_df.from_id.values.tolist() + road_edges_df.to_id.values.tolist())
    )
    nearest_nodes = road_nodes_df[road_nodes_df[node_id_column].isin(connected_nodes)]
    nearest_nodes.rename(columns={node_id_column: "id"}, inplace=True)
    nearest_nodes = nearest_nodes.to_crs(epsg=4326)

    # Find the network components

    edges = road_edges_df[
        [
            "from_id",
            "to_id",
            "id",
            "osm_way_id",
            "from_iso_a3",
            "to_iso_a3",
            "tag_highway",
            "tag_surface",
            "tag_bridge",
            "tag_maxspeed",
            "tag_lanes",
            "bridge",
            "paved",
            "material",
            "lanes",
            "length_m",
            "asset_type",
            "corridor_name",
            "geometry",
        ]
    ]
    edges, nearest_nodes = components(edges, nearest_nodes, node_id_column="id")

    edges["border_road"] = np.where(edges["from_iso_a3"] == edges["to_iso_a3"], 0, 1)

    nearest_nodes = gpd.GeoDataFrame(
        nearest_nodes, geometry="geometry", crs="EPSG:4326"
    )

    edges = gpd.GeoDataFrame(edges, geometry="geometry", crs="EPSG:3395")
    edges = edges.to_crs(epsg=4326)

    nearest_nodes.to_parquet(output_nodes)
    edges.to_parquet(output_edges)
    nearest_nodes.to_file(
        output_network,
        layer="nodes",
        driver="GPKG",
    )
    edges.to_file(
        output_network,
        layer="edges",
        driver="GPKG",
    )


if __name__ == "__main__":
    main()
