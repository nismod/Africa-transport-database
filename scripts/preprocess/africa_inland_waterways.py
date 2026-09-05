import click
import geopandas as gpd
import igraph as ig
import numpy as np
import pandas as pd
from shapely.geometry import LineString
from tqdm import tqdm

from aftdb.utils import (
    add_iso_code,
    components,
    create_network_from_nodes_and_edges,
    network_od_path_estimations,
)

tqdm.pandas()


def get_components_and_size(
    edges,
    nodes,
    node_id_column="node_id",
    edge_id_column="edge_id",
    from_node_column="from_node",
    to_node_column="to_node",
    network_crs=4326,
):
    edges, nodes = components(
        edges,
        nodes,
        node_id_column=node_id_column,
        edge_id_column=edge_id_column,
        from_node_column=from_node_column,
        to_node_column=to_node_column,
    )
    edges["component_size"] = edges.groupby(["component"])["component"].transform(
        "count"
    )
    nodes["component_size"] = nodes.groupby(["component"])["component"].transform(
        "count"
    )

    edges = gpd.GeoDataFrame(edges, geometry="geometry", crs=f"EPSG:{network_crs}")
    nodes = gpd.GeoDataFrame(nodes, geometry="geometry", crs=f"EPSG:{network_crs}")

    return edges, nodes


def network_creation(
    nodes_df,
    edges_df,
    edges_path,
    nodes_path,
    mode="iww",
    snap_distance=None,
    network_crs=4326,
    node_id_column="node_id",
    edge_id_column="edge_id",
    from_node_column="from_node",
    to_node_column="to_node",
):
    network = create_network_from_nodes_and_edges(
        nodes_df, edges_df, mode, snap_distance=snap_distance
    )
    edges, nodes = get_components_and_size(
        network.edges,
        network.nodes,
        node_id_column=node_id_column,
        edge_id_column=edge_id_column,
        from_node_column=from_node_column,
        to_node_column=to_node_column,
        network_crs=network_crs,
    )

    if network_crs != 4326:
        edges = edges.to_crs(epsg=4326)
        nodes = nodes.to_crs(epsg=4326)

    edges.to_parquet(edges_path)
    nodes.to_parquet(nodes_path)

    return edges, nodes


@click.command()
@click.option("--waterways", required=True, type=click.Path(exists=True))
@click.option("--iww-ports", required=True, type=click.Path(exists=True))
@click.option("--africa-adm0", required=True, type=click.Path(exists=True))
@click.option("--output-river-edges", required=True, type=click.Path())
@click.option("--output-river-nodes", required=True, type=click.Path())
@click.option("--output-network-edges", required=True, type=click.Path())
@click.option("--output-network-nodes", required=True, type=click.Path())
@click.option("--output-network", required=True, type=click.Path())
def main(
    waterways,
    iww_ports,
    africa_adm0,
    output_river_edges,
    output_river_nodes,
    output_network_edges,
    output_network_nodes,
    output_network,
):
    """Build the inland waterway network from the OpenStreetMap rivers extract"""
    epsg_meters = 3395
    # Step 1: Take the OSM rivers data and convert it into a network
    edges = gpd.read_parquet(waterways)

    edges = edges[
        edges["waterway"] == "river"
    ]  # Only select the rivers because they will be used for navigation
    edges, nodes = network_creation(None, edges, output_river_edges, output_river_nodes)

    # Step 2: Select the big connected rivers across Africa based on the largest component sizes
    component_size_threshold = (
        750  # We checked this from the result of the previous step
    )
    edges = gpd.read_parquet(output_river_edges)
    edges = edges[edges["component_size"] > component_size_threshold]
    edges.drop(
        ["edge_id", "from_node", "to_node", "component", "component_size"],
        axis=1,
        inplace=True,
    )

    # IWW_ports: IWW ports data from different datasets were taken and combined,
    # then we produced a final version of the selected ports and routes between them by manual cleaning
    # IWW ports
    df_ports = pd.read_excel(
        iww_ports,
        sheet_name="selected_ports",
    )
    df_ports["geometry"] = gpd.points_from_xy(df_ports["lon"], df_ports["lat"])
    df_ports["infra"] = df_ports.progress_apply(lambda x: f"IWW {x.infra}", axis=1)
    df_ports = gpd.GeoDataFrame(df_ports, geometry="geometry", crs="EPSG:4326")

    # known lake routes connecting ports - merge ports and routing files

    df_lake_routes = pd.read_excel(
        iww_ports,
        sheet_name="known_connections",
    )

    df_lake_routes = pd.merge(
        df_lake_routes,
        df_ports[["name", "geometry"]],
        how="left",
        left_on=["from_port"],
        right_on=["name"],
    )
    df_lake_routes.drop("name", axis=1, inplace=True)
    df_lake_routes.rename(columns={"geometry": "from_geometry"}, inplace=True)
    df_lake_routes = pd.merge(
        df_lake_routes,
        df_ports[["name", "geometry"]],
        how="left",
        left_on=["to_port"],
        right_on=["name"],
    )
    df_lake_routes.drop("name", axis=1, inplace=True)
    df_lake_routes.rename(columns={"geometry": "to_geometry"}, inplace=True)
    df_lake_routes["geometry"] = df_lake_routes.progress_apply(
        lambda x: LineString([x.from_geometry, x.to_geometry]), axis=1
    )
    df_lake_routes.drop(["from_geometry", "to_geometry"], axis=1, inplace=True)

    df_routes = gpd.GeoDataFrame(
        pd.concat(
            [df_lake_routes[["geometry"]], edges[["geometry"]]],
            axis=0,
            ignore_index=True,
        ),
        geometry="geometry",
        crs="EPSG:4326",
    )

    edges, nodes = network_creation(
        df_ports.to_crs(epsg=epsg_meters),
        df_routes.to_crs(epsg=epsg_meters),
        output_network_edges,
        output_network_nodes,
        snap_distance=6000,
        network_crs=epsg_meters,
    )

    # Step 3: Get the specific routes that connect IWW ports in Congo basin, reject other routes
    edges = gpd.read_parquet(output_network_edges)
    nodes = gpd.read_parquet(output_network_nodes)

    edges = edges.to_crs(epsg=epsg_meters)
    nodes = nodes.to_crs(epsg=epsg_meters)
    routing_edges = edges[["from_node", "to_node", "edge_id", "geometry"]]
    routing_edges["distance"] = routing_edges.geometry.length
    G = ig.Graph.TupleList(
        routing_edges.itertuples(index=False),
        edge_attrs=list(routing_edges.columns)[2:],
    )  # could just go?

    all_edges = []
    ports = nodes[~nodes["infra"].isna()]["node_id"].values.tolist()
    for o in range(len(ports) - 1):
        origin = ports[o]
        destinations = ports[o + 1 :]
        e, _c = network_od_path_estimations(
            G, origin, destinations, "distance", "edge_id"
        )
        all_edges += e

    all_edges = list({item for sublist in all_edges for item in sublist})
    africa_edges = edges[edges["edge_id"].isin(all_edges)]

    all_nodes = list(
        set(
            africa_edges["from_node"].values.tolist()
            + africa_edges["to_node"].values.tolist()
        )
    )
    africa_nodes = nodes[nodes["node_id"].isin(all_nodes)]

    africa_nodes["infra"] = np.where(
        africa_nodes["infra"].isna(), "IWW route", africa_nodes["infra"]
    )
    # Adding missing iso3 codes

    missing_isos = africa_nodes[africa_nodes["iso3"].isna()]
    missing_isos = add_iso_code(missing_isos, "node_id", africa_adm0, epsg=epsg_meters)
    for del_col in ["index", "index_right", "lat", "lon"]:
        if del_col in missing_isos.columns.values.tolist():
            missing_isos.drop(del_col, axis=1, inplace=True)
    iso_nodes = africa_nodes[~africa_nodes["iso3"].isna()]

    # Clean and create final Africa nodes and edges

    africa_nodes = pd.concat([iso_nodes, missing_isos], axis=0, ignore_index=True)

    africa_edges = pd.merge(
        africa_edges,
        africa_nodes[["node_id", "iso3", "infra"]],
        how="left",
        left_on=["from_node"],
        right_on=["node_id"],
    )
    africa_edges.rename(
        columns={"iso3": "from_iso_a3", "infra": "from_infra"}, inplace=True
    )
    africa_edges.drop("node_id", axis=1, inplace=True)
    africa_edges = pd.merge(
        africa_edges,
        africa_nodes[["node_id", "iso3", "infra"]],
        how="left",
        left_on=["to_node"],
        right_on=["node_id"],
    )
    africa_edges.rename(
        columns={"iso3": "to_iso_a3", "infra": "to_infra"}, inplace=True
    )
    africa_edges.drop("node_id", axis=1, inplace=True)
    africa_edges["length_m"] = africa_edges.geometry.length
    africa_edges, africa_nodes = get_components_and_size(
        africa_edges, africa_nodes, network_crs=epsg_meters
    )
    africa_edges.rename(
        columns={"edge_id": "id", "from_node": "from_id", "to_node": "to_id"},
        inplace=True,
    )
    africa_nodes.rename(columns={"node_id": "id"}, inplace=True)

    # Save nodes and edges

    africa_edges = africa_edges.to_crs(epsg=4326)
    africa_nodes = africa_nodes.to_crs(epsg=4326)
    africa_nodes[
        [
            "id",
            "name",
            "country",
            "iso3",
            "infra",
            "waterbody",
            "component",
            "geometry",
        ]
    ].to_file(
        output_network,
        layer="nodes",
        driver="GPKG",
    )
    africa_edges[
        [
            "id",
            "from_id",
            "to_id",
            "from_infra",
            "to_infra",
            "from_iso_a3",
            "to_iso_a3",
            "component",
            "length_m",
            "geometry",
        ]
    ].to_file(
        output_network,
        layer="edges",
        driver="GPKG",
    )


if __name__ == "__main__":
    main()
