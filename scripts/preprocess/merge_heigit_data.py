import glob
import os

import click
import geopandas as gpd
import pandas as pd


@click.command()
@click.option("--heigit-folder", required=True, type=click.Path(exists=True))
@click.option("--output-merged", required=True, type=click.Path())
def main(heigit_folder, output_merged):
    """Merge the per-country HeiGIT road surface GeoPackages into one file"""
    # Folder containing your GPKG files

    # Match all GPKG files
    gpkg_files = glob.glob(
        os.path.join(heigit_folder, "heigit_*_roadsurface_lines.gpkg")
    )

    if not gpkg_files:
        raise FileNotFoundError(
            f"No files found in '{heigit_folder}' matching 'heigit_*_roadsurface_lines.gpkg'."
        )

    merged_gdf = []
    layer_name = None

    for gpkg_path in gpkg_files:
        try:
            # Read GeoDataFrame
            gdf = gpd.read_file(gpkg_path, layer=layer_name)
            country_code = os.path.basename(gpkg_path).split("_")[1]
            gdf["country_iso_a3"] = str(country_code).upper()
            merged_gdf.append(gdf)
        except Exception as e:  # noqa: BLE001
            print(f"Skipping {gpkg_path}: {e}")

    # Final merge
    if not merged_gdf:
        raise ValueError("No valid GeoDataFrames were loaded. Nothing to merge.")

    final_gdf = gpd.GeoDataFrame(
        pd.concat(merged_gdf, axis=0, ignore_index=True),
        geometry="geometry",
        crs="EPSG:4326",
    )

    # Save to GeoPackage

    # Write to a new GeoPackage
    final_gdf.to_parquet(output_merged)


if __name__ == "__main__":
    main()
