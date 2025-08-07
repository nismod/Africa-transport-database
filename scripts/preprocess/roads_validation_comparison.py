import geopandas as gpd
import glob
import os
from utils_new import *
import numpy as np

def main(config):
    input_folder = config['paths']['incoming_data']
    output_folder = config['paths']['data']

    epsg_meters = 3395
    # Write to a new GeoPackage
    heigit_lines=gpd.read_parquet(os.path.join(
                            output_folder,
                            "infrastructure",
                            "validation_file_merge.geoparquet"))
    database_lines=gpd.read_parquet(os.path.join(
                            output_folder,
                            "infrastructure",
                            "africa_roads_edges_FINAL_last.geoparquet"))
    global_boundaries = gpd.read_file(os.path.join(output_folder,
                                    "admin_boundaries",
                                    "gadm36_levels_gpkg",
                                    "gadm36_levels_continents.gpkg"))
    countries = list(set(database_lines["from_iso_a3"].values.tolist() + database_lines["to_iso_a3"].values.tolist()))
    global_boundaries = global_boundaries[global_boundaries["ISO_A3"].isin(countries)]

    # 1. Ensure all GeoDataFrames use the same CRS
    heigit_lines = heigit_lines.to_crs(epsg=epsg_meters)
    database_lines = database_lines.to_crs(epsg=epsg_meters)
    global_boundaries = global_boundaries.to_crs(epsg=epsg_meters)

    # 2. Drop duplicate geometries (as you already had)
    heigit_lines = heigit_lines.drop_duplicates(subset=['geometry','osm_id'])

    # Heigit data is big, so we only select the roads which occur in our database
    select_osm_ids = list(set(database_lines["osm_way_id"].values.tolist()))
    heigit_lines = heigit_lines[heigit_lines["osm_id"].isin(select_osm_ids)]
    heigit_lines["country"] = heigit_lines["country"].str.upper()

    heigit_clipped_df = []
    database_clipped_df = []
    for country in countries:
        boundary_df = global_boundaries[global_boundaries["ISO_A3"] == country]
        # Select and clip HEIGIT lines for each country boundary
        h_df = heigit_lines[heigit_lines["country"] == country]
        if len(h_df.index) > 0:
            # df = gpd.clip(b_df,boundary_df)
            # hf = h_df.intersection(boundary_df)
            hf = gpd.overlay(h_df,boundary_df,how="intersection")
            if len(hf.index) > 0:
                hf["length"] = hf.geometry.length
                hf["country_iso_a3"] = country
                heigit_clipped_df.append(hf)
        # Clip the database road based on the identification of border roads
        b_df = database_lines[
                            (
                                database_lines["from_iso_a3"] == country
                            ) | (
                                database_lines["to_iso_a3"] == country
                            )]
        b_df["country_iso_a3"] = country
        database_clipped_df.append(b_df[b_df["border_road"] == 0])
        b_df = b_df[b_df["border_road"] == 1]
        # df = gpd.clip(b_df,boundary_df)
        # df = b_df.intersection(boundary_df)
        df = gpd.overlay(b_df,boundary_df,how="intersection")
        if len(df.index) > 0:
            df["length_m"] = df.geometry.length
            database_clipped_df.append(df)

    heigit_lines = pd.concat(heigit_clipped_df, axis=0, ignore_index=True)
    database_lines = pd.concat(database_clipped_df, axis=0, ignore_index=True)

    # 4. Group database_lines to get summed lengths per osm_id/paved
    database_lines["paved_type"
        ] = np.where(database_lines["asset_type"] == 'road_paved',"paved","unpaved")
    database_lines = database_lines.groupby(['osm_way_id','country_iso_a3', 'paved_type'])['length_m'].sum().reset_index()
    database_lines.rename(columns={'osm_way_id': 'osm_id'}, inplace=True)
    print (database_lines)

    print (heigit_lines)
    heigit_lines = heigit_lines.groupby(['osm_id','country_iso_a3', 'combined_surface_DL_priority'])['length'].sum().reset_index()
    print (heigit_lines)
    # 5. Merge the two datasets on osm_id 
    merged = heigit_lines.merge(database_lines, on=['osm_id','country_iso_a3'], suffixes=('_heigit', '_db'))
    
    # Make sure surface and paved are in consistent format (e.g., lowercase strings)
    merged['combined_surface_DL_priority'] = merged['combined_surface_DL_priority'].str.lower()
    # merged['paved'] = merged['paved'].astype(str).str.lower()

    # Now create 'paved_match' column using vectorized logic
    # merged['paved_match'] = np.where(
    #     ((merged['combined_surface_DL_priority'] == 'paved') & (merged['paved'] == 'true')) |
    #     ((merged['combined_surface_DL_priority'] == 'unpaved') & (merged['paved'] == 'false')),
    #     1,
    #     0
    # )

    merged.rename(columns={'length': 'length_heigit_m', 'length_m': 'length_db_m'}, inplace=True)

    # Filter only matches
    # matches = merged[merged['paved_match'] == 1]

    # Group by ISO3 and surface class
    # Heigit grouping
    heigit_summary = (
        merged.groupby(['country_iso_a3', 'combined_surface_DL_priority'])['length_heigit_m']
        .sum()
        .unstack(fill_value=0)
        .add_prefix('length_heigit_m_')
    )

    # DB grouping
    db_summary = (
        merged.groupby(['country_iso_a3', 'paved_type'])['length_db_m']
        .sum()
        .unstack(fill_value=0)
        .add_prefix('length_db_m_')
    )

    # Merge both
    pivot_table = heigit_summary.join(db_summary, how='outer').fillna(0).reset_index()
    

    pivot_table
    # 7. Select the columns you're interested in
    # Export the full merged dataset
    merged.to_parquet(os.path.join(
                            output_folder,
                            "infrastructure",
                            "merged_validation_datasets.parquet"))

    # Export the pivot table
    pivot_table.to_csv(os.path.join(
                            output_folder,
                            "infrastructure",
                            "merged_validation_datasets.csv"))   

    print(merged.head())
    print(pivot_table.head())
   

    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)    
