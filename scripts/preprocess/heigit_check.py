import click
import geopandas as gpd
import numpy as np
import pandas as pd


def create_tag(x):
    if (x["osm_class"] == x["combined_surface_DL_priority"]) & (
        x["osm_class"] == x["paved"]
    ):
        return 0
    elif x["paved"] == x["osm_class"]:
        return 1
    elif x["paved"] == x["combined_surface_DL_priority"]:
        return 2
    else:
        return 3


@click.command()
@click.option("--database-lines", required=True, type=click.Path(exists=True))
@click.option("--heigit-lines", required=True, type=click.Path(exists=True))
@click.option("--boundaries", required=True, type=click.Path(exists=True))
@click.option("--output-merged", required=True, type=click.Path())
@click.option("--output-pivot", required=True, type=click.Path())
@click.option("--output-pivot-corrected", required=True, type=click.Path())
def main(
    database_lines,
    heigit_lines,
    boundaries,
    output_merged,
    output_pivot,
    output_pivot_corrected,
):
    """Compare database road surfaces against the merged HeiGIT dataset"""
    epsg_meters = 3395
    # Write to a new GeoPackage
    database_lines = gpd.read_parquet(database_lines)
    heigit_lines = gpd.read_parquet(heigit_lines)
    global_boundaries = gpd.read_file(boundaries)
    countries = list(
        set(
            database_lines["from_iso_a3"].values.tolist()
            + database_lines["to_iso_a3"].values.tolist()
        )
    )
    global_boundaries = global_boundaries[global_boundaries["ISO_A3"].isin(countries)]

    edge_ids = list(set(database_lines["osm_way_id"].values.tolist()))
    heigit_lines = heigit_lines[heigit_lines["osm_id"].isin(edge_ids)]
    heigit_lines = heigit_lines.drop_duplicates(subset=["osm_id"], keep="first")

    # Ensure all GeoDataFrames use the same CRS
    database_lines = database_lines.to_crs(epsg=epsg_meters)
    heigit_lines = heigit_lines.to_crs(epsg=epsg_meters)
    global_boundaries = global_boundaries.to_crs(epsg=epsg_meters)

    database_clipped_df = []
    heigit_clipped_df = []
    for country in countries:
        boundary_df = global_boundaries[global_boundaries["ISO_A3"] == country]
        # Clip the database road based on the identification of border roads
        b_df = database_lines[
            (database_lines["from_iso_a3"] == country)
            | (database_lines["to_iso_a3"] == country)
        ]
        b_df["country_iso_a3"] = country
        database_clipped_df.append(b_df[b_df["border_road"] == 0])
        b_df = b_df[b_df["border_road"] == 1]
        df = gpd.overlay(b_df, boundary_df, how="intersection")
        if len(df.index) > 0:
            df["length_m"] = df.geometry.length
            database_clipped_df.append(df)

        b_df = heigit_lines[heigit_lines["country_iso_a3"] == country]
        df = gpd.overlay(b_df, boundary_df, how="intersection")
        if len(df.index) > 0:
            df["heigit_length_m"] = df.geometry.length
            heigit_clipped_df.append(df)

        print(f"* Done with {country}")

    database_lines = pd.concat(database_clipped_df, axis=0, ignore_index=True)
    # 4. Group database_lines to get summed lengths per osm_id/paved
    database_lines["paved"] = database_lines.apply(
        lambda x: str(x["paved"]).lower(), axis=1
    )
    database_lines["paved_type"] = np.where(
        database_lines["paved"] == "true", "paved", "unpaved"
    )
    database_lines = (
        database_lines.groupby(["osm_way_id", "country_iso_a3", "paved_type"])[
            "length_m"
        ]
        .sum()
        .reset_index()
    )
    database_lines.rename(columns={"osm_way_id": "osm_id"}, inplace=True)

    heigit_lines = pd.concat(heigit_clipped_df, axis=0, ignore_index=True)
    heigit_lines = (
        heigit_lines.groupby(
            ["osm_id", "country_iso_a3", "combined_surface_DL_priority"]
        )["heigit_length_m"]
        .sum()
        .reset_index()
    )
    matched_df = pd.merge(
        heigit_lines, database_lines, how="left", on=["osm_id", "country_iso_a3"]
    )

    matched_df["length_heigit_m"] = matched_df["length_m"]
    matched_df["length_db_m"] = matched_df["length_m"]
    matched_df.drop("length_m", axis=1, inplace=True)
    matched_df.to_parquet(output_merged)

    # Group by ISO3 and surface class
    # Heigit grouping
    heigit_summary = (
        matched_df.groupby(["country_iso_a3", "combined_surface_DL_priority"])[
            "heigit_length_m"
        ]
        .sum()
        .unstack(fill_value=0)
        .add_prefix("length_heigit_m_")
    )

    heigit_summary_corr = (
        matched_df.groupby(["country_iso_a3", "combined_surface_DL_priority"])[
            "length_heigit_m"
        ]
        .sum()
        .unstack(fill_value=0)
        .add_prefix("length_heigit_m_")
    )

    # DB grouping
    db_summary = (
        matched_df.groupby(["country_iso_a3", "paved_type"])["length_db_m"]
        .sum()
        .unstack(fill_value=0)
        .add_prefix("length_db_m_")
    )

    # Merge both
    pivot_table = heigit_summary.join(db_summary, how="outer").fillna(0).reset_index()
    # Export the pivot table
    pivot_table.to_csv(output_pivot)

    # Merge both
    pivot_table = (
        heigit_summary_corr.join(db_summary, how="outer").fillna(0).reset_index()
    )
    # Export the pivot table
    pivot_table.to_csv(output_pivot_corrected)


if __name__ == "__main__":
    main()
