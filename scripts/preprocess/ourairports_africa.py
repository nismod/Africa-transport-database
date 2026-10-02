import click
import geopandas as gpd
import pandas as pd


@click.command()
@click.option("--airports", required=True, type=click.Path(exists=True))
@click.option("--output-airports", required=True, type=click.Path())
def main(airports, output_airports):
    """Turn the OurAirports CSV into a point layer of the African airports"""
    airports_df = pd.read_csv(airports, low_memory=False)
    airports_df = airports_df[airports_df["continent"] == "AF"]

    airports_gdf = gpd.GeoDataFrame(
        airports_df,
        geometry=gpd.points_from_xy(
            airports_df["longitude_deg"], airports_df["latitude_deg"]
        ),
        crs="EPSG:4326",
    )
    airports_gdf.to_file(output_airports, driver="GPKG")


if __name__ == "__main__":
    main()
