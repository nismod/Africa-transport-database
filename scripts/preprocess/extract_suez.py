# Code to extract the suez canal navigation route
import re

import click
import geopandas as gpd
import pandas as pd
from tqdm import tqdm

from aftdb.utils import components, create_network_from_nodes_and_edges

tqdm.pandas()


@click.command()
@click.option("--waterways", required=True, type=click.Path(exists=True))
@click.option("--suez-ids", required=True, type=click.Path(exists=True))
@click.option("--global-ports", required=True, type=click.Path(exists=True))
@click.option("--output-network", required=True, type=click.Path())
def main(waterways, suez_ids, global_ports, output_network):
    """Turn the Suez Canal OpenStreetMap waterways into a topological network"""
    # Read the OSM data and the suez canal IDs
    waterways_df = gpd.read_file(waterways)
    waterways_df["osm_id"] = waterways_df["osm_id"].astype(int)
    suez_ids = pd.read_csv(suez_ids)
    suez_ids = [int(n) for n in suez_ids["osm_id"].values.tolist()]
    suez_canal = waterways_df[waterways_df["osm_id"].isin(suez_ids)]
    # Convert to a topological network
    network = create_network_from_nodes_and_edges(None, suez_canal, "water")
    edges, nodes = components(network.edges, network.nodes, "node_id")

    # Rename nodes to match global nodes layer
    df_global_ports = gpd.read_file(global_ports)

    nodes["infra"] = "maritime"
    prt = df_global_ports[df_global_ports["infra"] == "maritime"]
    max_port_id = max(
        [int(re.findall(r"\d+", v)[0]) for v in prt["id"].values.tolist()]
    )
    nodes["id"] = list(max_port_id + 1 + nodes.index.values)
    nodes["id"] = nodes.progress_apply(lambda x: f"maritime{x.id}", axis=1)
    edges = pd.merge(
        edges,
        nodes[["node_id", "id"]],
        how="left",
        left_on=["from_node"],
        right_on=["node_id"],
    )
    edges.drop("node_id", axis=1, inplace=True)
    edges.rename(columns={"id": "from_id"}, inplace=True)
    edges = pd.merge(
        edges,
        nodes[["node_id", "id"]],
        how="left",
        left_on=["to_node"],
        right_on=["node_id"],
    )
    edges.rename(columns={"id": "to_id"}, inplace=True)
    edges.drop("node_id", axis=1, inplace=True)
    edges["from_infra"] = "maritime"
    edges["to_infra"] = "maritime"
    # Write the Suez Canal routes to a GPKG
    gpd.GeoDataFrame(edges, geometry="geometry", crs=waterways_df.crs).to_file(
        output_network, layer="edges", driver="GPKG"
    )
    gpd.GeoDataFrame(nodes, geometry="geometry", crs=waterways_df.crs).to_file(
        output_network, layer="nodes", driver="GPKG"
    )


if __name__ == "__main__":
    main()
