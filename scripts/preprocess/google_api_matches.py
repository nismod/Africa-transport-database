import click
import geopandas as gpd
import numpy as np
import pandas as pd
from tqdm import tqdm

tqdm.pandas()


def match_and_merge(
    rail_dataframe,
    location_df,
    matches_dataframe,
    tuple_columns,
    distance_column="distance",
    name_column="name",
    type_column="type",
):
    if "id" in location_df.columns.values.tolist():
        location_df.rename(columns={"id": "location_id"}, inplace=True)

    matches = gpd.sjoin_nearest(
        rail_dataframe, location_df, distance_col=distance_column
    )
    matches = matches.drop_duplicates(subset=["id"], keep="first")
    matches_dataframe = pd.merge(
        matches_dataframe,
        matches[["id", name_column, type_column, distance_column]],
        how="left",
        on=["id"],
    )
    tuple_columns.append([name_column, type_column, distance_column])
    return matches_dataframe, tuple_columns


def get_closest_match(x, tuple_columns):
    sets = []
    for t in tuple_columns:
        sets.append(x[t])

    sets = sorted(sets, key=lambda y: y[-1])
    return tuple(sets[0].values.tolist())


@click.command()
@click.option("--rail-network", required=True, type=click.Path(exists=True))
@click.option("--google-points", required=True, type=click.Path(exists=True))
@click.option("--global-mines", required=True, type=click.Path(exists=True))
@click.option("--usgs-facilities", required=True, type=click.Path(exists=True))
@click.option("--airports", required=True, type=click.Path(exists=True))
@click.option("--maritime", required=True, type=click.Path(exists=True))
@click.option("--iww", required=True, type=click.Path(exists=True))
@click.option("--previous-matches", required=True, type=click.Path(exists=True))
@click.option("--output-matches", required=True, type=click.Path())
def main(
    rail_network,
    google_points,
    global_mines,
    usgs_facilities,
    airports,
    maritime,
    iww,
    previous_matches,
    output_matches,
):
    """Match rail facilities against mines, ports, airports and Google places"""
    epsg_meters = 3395

    rail_nodes = gpd.read_file(
        rail_network,
        layer="nodes",
    )
    rail_nodes = rail_nodes[~rail_nodes["facility"].isna()]
    rail_nodes = rail_nodes.to_crs(epsg=epsg_meters)

    tuple_columns = []
    # Get the google API matches
    google_matches = pd.read_csv(google_points)
    google_matches = google_matches.sort_values(by=["point_distance"], ascending=True)
    google_matches = google_matches.drop_duplicates(subset=["id"], keep="first")
    google_matches["google"] = "google"
    matches_dataframe = pd.merge(
        rail_nodes,
        google_matches[["id", "displayName.text", "google", "point_distance"]],
        how="left",
        on=["id"],
    )
    matches_dataframe["point_distance"] = matches_dataframe["point_distance"].fillna(
        1e9
    )
    tuple_columns.append(["displayName.text", "google", "point_distance"])

    # Get the mines layers
    global_mines = gpd.read_file(global_mines)
    global_mines = global_mines.to_crs(epsg=epsg_meters)
    global_mines["mines"] = "mine"
    matches_dataframe, tuple_columns = match_and_merge(
        rail_nodes,
        global_mines,
        matches_dataframe,
        tuple_columns,
        distance_column="distance_mines",
        name_column="Name",
        type_column="mines",
    )

    usgs_data = gpd.read_file(usgs_facilities)
    usgs_data = usgs_data.to_crs(epsg=epsg_meters)
    matches_dataframe, tuple_columns = match_and_merge(
        rail_nodes,
        usgs_data,
        matches_dataframe,
        tuple_columns,
        distance_column="distance_usgs",
        name_column="FeatureNam",
        type_column="FeatureTyp",
    )
    # Get the google API matches
    airports = gpd.read_file(
        airports,
        layer="nodes",
    )
    airports["infra_air"] = "air"
    airports["air_name"] = airports["name"]
    airports = airports.to_crs(epsg=epsg_meters)
    matches_dataframe, tuple_columns = match_and_merge(
        rail_nodes,
        airports,
        matches_dataframe,
        tuple_columns,
        distance_column="distance_airports",
        name_column="air_name",
        type_column="infra_air",
    )

    ports = gpd.read_file(
        maritime,
        layer="nodes",
    )
    ports = ports[ports["infra"] == "port"]
    ports["infra_maritime"] = "port"
    ports = ports.to_crs(epsg=epsg_meters)
    matches_dataframe, tuple_columns = match_and_merge(
        rail_nodes,
        ports,
        matches_dataframe,
        tuple_columns,
        distance_column="distance_maritime_ports",
        name_column="fullname",
        type_column="infra_maritime",
    )
    ports = gpd.read_file(
        iww,
        layer="nodes",
    )
    ports = ports[ports["infra"] == "IWW port"]
    ports["infra_iww"] = "IWW port"
    ports["name_iww"] = ports["name"]
    ports = ports.to_crs(epsg=epsg_meters)
    matches_dataframe, tuple_columns = match_and_merge(
        rail_nodes,
        ports,
        matches_dataframe,
        tuple_columns,
        distance_column="distance_iww_ports",
        name_column="name_iww",
        type_column="infra_iww",
    )
    matches_dataframe["closest_matches"] = matches_dataframe.progress_apply(
        lambda x: get_closest_match(x, tuple_columns), axis=1
    )
    matches_dataframe[["closest_name", "closest_type", "closest_distance"]] = (
        matches_dataframe["closest_matches"].apply(pd.Series)
    )
    matches_dataframe.drop(
        [x for xs in tuple_columns for x in xs] + ["closest_matches"],
        axis=1,
        inplace=True,
    )
    matches_dataframe = gpd.GeoDataFrame(
        matches_dataframe, geometry="geometry", crs=f"EPSG:{epsg_meters}"
    )
    matches_dataframe = matches_dataframe.to_crs(epsg=4326)
    final_matches = gpd.read_file(previous_matches)
    final_matches.rename(
        columns={
            "closest_type": "closest_type_final",
            "closest_distance": "closest_distance_final",
        },
        inplace=True,
    )
    matches_dataframe = pd.merge(
        matches_dataframe,
        final_matches[["id", "closest_type_final", "closest_distance_final"]],
        how="left",
        on=["id"],
    ).fillna(1e9)
    matches_dataframe["closest_distance"] = np.where(
        matches_dataframe["closest_type"] == matches_dataframe["closest_type_final"],
        matches_dataframe[["closest_distance", "closest_distance_final"]].min(axis=1),
        matches_dataframe["closest_distance"],
    )
    matches_dataframe["closest_distance"] = np.where(
        matches_dataframe["closest_type_final"] == "manual check",
        matches_dataframe["closest_distance_final"],
        matches_dataframe["closest_distance"],
    )
    matches_dataframe["closest_type"] = np.where(
        matches_dataframe["closest_type_final"] == "manual check",
        matches_dataframe["closest_type_final"],
        matches_dataframe["closest_type"],
    )
    matches_dataframe["closest_distance"] = np.where(
        (~matches_dataframe["closest_type"].isin(["port", "air", "IWW port"]))
        & (matches_dataframe["closest_type_final"] == "google"),
        matches_dataframe["closest_distance_final"],
        matches_dataframe["closest_distance"],
    )
    matches_dataframe["closest_type"] = np.where(
        (~matches_dataframe["closest_type"].isin(["port", "air", "IWW port"]))
        & (matches_dataframe["closest_type_final"] == "google"),
        matches_dataframe["closest_type_final"],
        matches_dataframe["closest_type"],
    )
    matches_dataframe["closest_type"] = np.where(
        matches_dataframe["closest_distance_final"]
        < matches_dataframe["closest_distance"],
        matches_dataframe["closest_type_final"],
        matches_dataframe["closest_type"],
    )
    matches_dataframe["closest_distance"] = np.where(
        matches_dataframe["closest_distance_final"]
        < matches_dataframe["closest_distance"],
        matches_dataframe["closest_distance_final"],
        matches_dataframe["closest_distance"],
    )
    matches_dataframe.drop(
        ["closest_type_final", "closest_distance_final"], axis=1, inplace=True
    )
    matches_dataframe.to_file(
        output_matches,
        driver="GPKG",
    )


if __name__ == "__main__":
    main()
