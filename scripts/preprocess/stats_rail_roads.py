import click
import geopandas as gpd
from tqdm import tqdm

tqdm.pandas()


@click.command()
@click.option("--road-edges", required=True, type=click.Path(exists=True))
@click.option("--rail-network", required=True, type=click.Path(exists=True))
@click.option("--output-rail-stats", required=True, type=click.Path())
@click.option("--output-paved-stats", required=True, type=click.Path())
def main(road_edges, rail_network, output_rail_stats, output_paved_stats):
    """Summarise rail length by status and road length by corridor and surface"""
    roads_df = gpd.read_parquet(road_edges)
    rail_df = gpd.read_file(rail_network, layer="edges")

    # Convert length from meters to kilometers - railways
    rail_df["length_km"] = rail_df["length_m"] / 1000
    grouped_data_rail = rail_df.groupby(["status"])["length_km"].sum().reset_index()
    grouped_data_rail["percentage"] = (
        grouped_data_rail["length_km"] / grouped_data_rail["length_km"].sum()
    ) * 100
    print(grouped_data_rail)
    # Save the grouped data to a CSV file
    grouped_data_rail.to_csv(output_rail_stats, index=False)

    # Convert length from meters to kilometers - roads
    roads_df["length_km"] = roads_df["length_m"] / 1000
    total_length_km = roads_df["length_km"].sum()
    print(f"Total length in km: {total_length_km}")
    grouped_roads_df = (
        roads_df.groupby(["tag_highway"])["length_km"].sum().reset_index()
    )
    grouped_roads_df["percentage"] = (
        grouped_roads_df["length_km"] / grouped_roads_df["length_km"].sum()
    ) * 100
    print(grouped_roads_df)

    # Split the 'corridor_name' by '/' to account for multiple corridors
    roads_df["corridor_name"] = roads_df["corridor_name"].str.split("/")

    # Explode the data to separate overlapping corridors into individual rows
    gdf_exploded = roads_df.explode("corridor_name", ignore_index=True)
    # Define valid highway types
    valid_highways = ["trunk", "motorway", "primary", "secondary", "tertiary"]

    # Replace values not in the valid list with 'Other'
    gdf_exploded.loc[
        ~gdf_exploded["tag_highway"].isin(valid_highways), "tag_highway"
    ] = "Other"

    grouped_data = gdf_exploded.groupby(["corridor_name", "paved"], as_index=False).agg(
        {"length_km": "sum"}
    )

    # Calculate total length per corridor
    grouped_data["total_km"] = grouped_data["length_km"].sum()

    # Calculate percentage for each paved/unpaved group
    grouped_data["percentage"] = (
        grouped_data["length_km"] / grouped_data["total_km"]
    ) * 100

    grouped_data.to_csv(output_paved_stats, index=False)


if __name__ == "__main__":
    main()
