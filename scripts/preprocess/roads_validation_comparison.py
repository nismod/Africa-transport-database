import os

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
@click.option("--boundaries", required=True, type=click.Path(exists=True))
@click.option("--heigit-folder", required=True, type=click.Path(exists=True))
@click.option("--output-merged", required=True, type=click.Path())
@click.option("--output-pivot", required=True, type=click.Path())
@click.option("--output-counts", required=True, type=click.Path())
def main(
    database_lines,
    boundaries,
    heigit_folder,
    output_merged,
    output_pivot,
    output_counts,
):
    """Clip database and HeiGIT roads by country and compare paved lengths"""
    epsg_meters = 32736
    # Write to a new GeoPackage
    database_lines = gpd.read_parquet(database_lines)
    global_boundaries = gpd.read_file(boundaries)
    countries = list(
        set(
            database_lines["from_iso_a3"].values.tolist()
            + database_lines["to_iso_a3"].values.tolist()
        )
    )
    global_boundaries = global_boundaries[global_boundaries["ISO_A3"].isin(countries)]

    # Ensure all GeoDataFrames use the same CRS
    database_lines = database_lines.to_crs(epsg=epsg_meters)
    global_boundaries = global_boundaries.to_crs(epsg=epsg_meters)

    # Heigit data is big, so we only select the roads which occur in our database
    select_osm_ids = list(set(database_lines["osm_way_id"].values.tolist()))

    heigit_clipped_df = []
    database_clipped_df = []
    for country in countries:
        heigit_file = os.path.join(
            heigit_folder, f"heigit_{country.lower()}_roadsurface_lines.gpkg"
        )
        boundary_df = global_boundaries[global_boundaries["ISO_A3"] == country]
        if os.path.exists(heigit_file):
            h_df = gpd.read_file(heigit_file)
            # Drop duplicate geometries (as you already had)
            h_df = h_df.drop_duplicates(subset=["geometry", "osm_id"])
            h_df = h_df.to_crs(epsg=epsg_meters)
            h_df = h_df[h_df["osm_id"].isin(select_osm_ids)]

            # Select and clip HEIGIT lines for each country boundary
            if len(h_df.index) > 0:
                hf = gpd.overlay(h_df, boundary_df, how="intersection")
                if len(hf.index) > 0:
                    hf["length"] = hf.geometry.length
                    hf["country_iso_a3"] = country
                    heigit_clipped_df.append(hf)
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

    heigit_lines = pd.concat(heigit_clipped_df, axis=0, ignore_index=True)
    database_lines = pd.concat(database_clipped_df, axis=0, ignore_index=True)

    # Group database_lines to get summed lengths per osm_id/paved
    database_lines["paved"] = database_lines["paved"].astype(str).str.lower()
    database_lines["paved"] = np.where(
        database_lines["paved"] == "true", "paved", "unpaved"
    )
    database_lines = (
        database_lines.groupby(["osm_way_id", "country_iso_a3", "paved"])["length_m"]
        .sum()
        .reset_index()
    )
    database_lines.rename(columns={"osm_way_id": "osm_id"}, inplace=True)
    heigit_lines["osm_class"] = np.where(
        heigit_lines["osm_surface_class"].isin(["paved", "unpaved"]),
        heigit_lines["osm_surface_class"],
        "untagged",
    )
    heigit_lines = (
        heigit_lines.groupby(
            ["osm_id", "country_iso_a3", "osm_class", "combined_surface_DL_priority"]
        )["length"]
        .sum()
        .reset_index()
    )
    print(heigit_lines)
    # Merge the two datasets on osm_id
    merged = heigit_lines.merge(
        database_lines, on=["osm_id", "country_iso_a3"], suffixes=("_heigit", "_db")
    )

    # Make sure surface and paved are in consistent format (e.g., lowercase strings)
    merged["combined_surface_DL_priority"] = merged[
        "combined_surface_DL_priority"
    ].str.lower()

    merged.rename(
        columns={"length": "length_heigit_m", "length_m": "length_db_m"}, inplace=True
    )

    # Group by ISO3 and surface class
    # Heigit grouping
    heigit_summary = (
        merged.groupby(["country_iso_a3", "combined_surface_DL_priority"])[
            "length_heigit_m"
        ]
        .sum()
        .unstack(fill_value=0)
        .add_prefix("length_heigit_m_")
    )

    # DB grouping
    db_summary = (
        merged.groupby(["country_iso_a3", "paved"])["length_db_m"]
        .sum()
        .unstack(fill_value=0)
        .add_prefix("length_db_m_")
    )

    # Merge both
    pivot_table = heigit_summary.join(db_summary, how="outer").fillna(0).reset_index()

    # Select the columns you're interested in
    # Export the full merged dataset
    merged.to_parquet(output_merged)

    # Export the pivot table
    pivot_table.to_csv(output_pivot)

    merged["check"] = merged.apply(lambda x: create_tag(x), axis=1)
    merged = merged.value_counts(
        subset=["country_iso_a3", "check"], sort=False
    ).reset_index()
    merged["country_total"] = merged.groupby(["country_iso_a3"])["count"].transform(
        "sum"
    )
    merged["proportion"] = 100.0 * merged["count"] / merged["country_total"]

    merged.to_csv(output_counts)


if __name__ == "__main__":
    main()
