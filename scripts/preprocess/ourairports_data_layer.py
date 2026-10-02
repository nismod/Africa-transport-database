import click
import geopandas as gpd
from tqdm import tqdm

tqdm.pandas()


@click.command()
@click.option("--ourairports", required=True, type=click.Path(exists=True))
@click.option("--airport-network", required=True, type=click.Path(exists=True))
@click.option("--output-ourairports", required=True, type=click.Path())
@click.option("--output-network", required=True, type=click.Path())
def main(ourairports, airport_network, output_ourairports, output_network):
    """Filter the OurAirports layer to the airports already in the network"""
    df_airports_ourairports = gpd.read_file(ourairports)

    df_airports_nodes = gpd.read_file(
        airport_network,
        layer="nodes",
    )
    df_airports_edges = gpd.read_file(
        airport_network,
        layer="edges",
    )

    df_airports_ourairports = df_airports_ourairports.to_crs(epsg=4326)

    df_airports_ourairports_filtered = df_airports_ourairports[
        df_airports_ourairports["iata_code"].isin(df_airports_nodes["Orig"])
    ]
    df_airports_nodes.rename(columns={"Orig": "iata_code"}, inplace=True)

    df_airports_ourairports_filtered = df_airports_ourairports_filtered.to_crs(
        epsg=4326
    )

    df_airports_nodes = df_airports_nodes.to_crs(epsg=4326)
    df_airports_edges = df_airports_edges.to_crs(epsg=4326)

    print(df_airports_nodes)
    print(df_airports_ourairports_filtered)

    df_airports_ourairports_filtered.to_file(
        output_ourairports,
        layer="nodes",
        driver="GPKG",
    )

    df_airports_nodes.to_file(
        output_network,
        layer="nodes",
        driver="GPKG",
    )
    df_airports_edges.to_file(
        output_network,
        layer="edges",
        driver="GPKG",
    )


if __name__ == "__main__":
    main()
