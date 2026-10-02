import click
import geopandas as gpd
from shapely.geometry import LineString
from tqdm import tqdm

tqdm.pandas()


@click.command()
@click.option("--airport-network", required=True, type=click.Path(exists=True))
@click.option("--output-network", required=True, type=click.Path())
def main(airport_network, output_network):
    """Rebuild airport route geometries and attach origin and destination ISO3 codes"""
    df_airports_flow = gpd.read_file(
        airport_network,
        layer="edges",
    )

    df_airports_nodes = gpd.read_file(
        airport_network,
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
        output_network,
        layer="nodes",
        driver="GPKG",
    )
    df_airports_flow.to_file(
        output_network,
        layer="edges",
        driver="GPKG",
    )


if __name__ == "__main__":
    main()
