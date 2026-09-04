import os

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
from tqdm import tqdm

from aftdb.utils import load_config

tqdm.pandas()


def add_iso_code(df, df_id_column, incoming_data_path):
    # Insert countries' ISO CODE
    africa_boundaries = gpd.read_file(
        os.path.join(
            incoming_data_path,
            "Africa_GIS Supporting Data",
            "a. Africa_GIS Shapefiles",
            "AFR_Political_ADM0_Boundaries.shp",
            "AFR_Political_ADM0_Boundaries.shp",
        )
    )
    africa_boundaries.rename(columns={"DsgAttr03": "iso3"}, inplace=True)
    # Spatial join
    m = gpd.sjoin(
        df, africa_boundaries[["geometry", "iso3"]], how="left", predicate="within"
    ).reset_index()
    m = m[~m["iso3"].isna()]
    un = df[~df[df_id_column].isin(m[df_id_column].values.tolist())]
    un = gpd.sjoin_nearest(
        un, africa_boundaries[["geometry", "iso3"]], how="left"
    ).reset_index()
    m = pd.concat([m, un], axis=0, ignore_index=True)
    return m


def main(config):

    processed_data_path = config["paths"]["data"]

    df_airports_flow = gpd.read_file(
        os.path.join(
            processed_data_path, "infrastructure", "africa_airport_network.gpkg"
        ),
        layer="edges",
    )

    df_airports_nodes = gpd.read_file(
        os.path.join(
            processed_data_path, "infrastructure", "africa_airport_network.gpkg"
        ),
        layer="nodes",
    )

    df_airports_flow = df_airports_flow.to_crs(epsg=4326)
    df_airports_flow = df_airports_flow.drop_duplicates(
        subset=["from_id", "to_id"], keep="first"
    )
    df_airports_flow.drop(["from_iso3", "to_iso3"], axis=1, inplace=True)
    id_to_geom = df_airports_nodes.set_index("id")["geometry"].to_dict()

    def create_linestring(row):
        from_geom = id_to_geom.get(row["from_id"])
        to_geom = id_to_geom.get(row["to_id"])
        if from_geom and to_geom:
            return LineString([from_geom, to_geom])
        return None

    # Apply the function to each row in flows
    df_airports_flow["geometry"] = df_airports_flow.apply(create_linestring, axis=1)

    # First merge: from_id → from_iso3
    df_airports_flow = df_airports_flow.merge(
        df_airports_nodes[["id", "iso3"]].rename(
            columns={"id": "from_node_id", "iso3": "from_iso3"}
        ),
        left_on="from_id",
        right_on="from_node_id",
        how="left",
    ).drop(columns="from_node_id")

    # Second merge: to_id → to_iso3
    df_airports_flow = df_airports_flow.merge(
        df_airports_nodes[["id", "iso3"]].rename(
            columns={"id": "to_node_id", "iso3": "to_iso3"}
        ),
        left_on="to_id",
        right_on="to_node_id",
        how="left",
    ).drop(columns="to_node_id")

    print(df_airports_flow.head())

    # Convert to GeoDataFrame
    df_airports_flow = gpd.GeoDataFrame(
        df_airports_flow, geometry="geometry", crs="EPSG:4326"
    )
    df_airports_flow = df_airports_flow[df_airports_flow.geometry.notnull()]

    df_airports_nodes.to_file(
        os.path.join(
            processed_data_path, "infrastructure", "africa_airport_network_last.gpkg"
        ),
        layer="nodes",
        driver="GPKG",
    )
    df_airports_flow.to_file(
        os.path.join(
            processed_data_path, "infrastructure", "africa_airport_network_last.gpkg"
        ),
        layer="edges",
        driver="GPKG",
    )


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
