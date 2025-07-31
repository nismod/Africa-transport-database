import geopandas as gpd
import glob
import os
from utils_new import *
import numpy as np

def main(config):
    input_folder = config['paths']['incoming_data']
    output_folder = config['paths']['data']

    # Write to a new GeoPackage
    heigit_lines=gpd.read_parquet(os.path.join(
                            output_folder,
                            "infrastructure",
                            "validation_file_merge.geoparquet"))
    database_lines=gpd.read_parquet(os.path.join(
                            output_folder,
                            "infrastructure",
                            "africa_roads_edges_FINAL_last.geoparquet"))

    # 1. Ensure both GeoDataFrames use the same CRS
    heigit_lines = heigit_lines.to_crs(epsg=4326)
    database_lines = database_lines.to_crs(epsg=4326)

    # 2. Drop duplicate geometries (as you already had)
    heigit_lines = heigit_lines.drop_duplicates(subset=['geometry','osm_id'])

    # 3. Calculate length in meters using an appropriate projected CRS (since EPSG:4326 gives degrees)
    # Reproject temporarily to a metric CRS (like EPSG:3857)
    heigit_lines_metric = heigit_lines.to_crs(epsg=3395)
    heigit_lines['length'] = heigit_lines_metric.geometry.length

    # 4. Group database_lines to get summed lengths per osm_id/paved
    database_lines = database_lines.groupby(['osm_way_id', 'paved'])['length_m'].sum().reset_index()
    database_lines.rename(columns={'osm_way_id': 'osm_id'}, inplace=True)

    # 5. Merge the two datasets on osm_id 
    merged = heigit_lines.merge(database_lines, on='osm_id', suffixes=('_heigit', '_db'))
    
    # Make sure surface and paved are in consistent format (e.g., lowercase strings)
    merged['combined_surface_DL_priority'] = merged['combined_surface_DL_priority'].str.lower()
    merged['paved'] = merged['paved'].astype(str).str.lower()

    # Now create 'paved_match' column using vectorized logic
    merged['paved_match'] = np.where(
        ((merged['combined_surface_DL_priority'] == 'paved') & (merged['paved'] == 'true')) |
        ((merged['combined_surface_DL_priority'] == 'unpaved') & (merged['paved'] == 'false')),
        1,
        0
    )

    merged.rename(columns={'length': 'length_heigit_m', 'length_m': 'length_db_m'}, inplace=True)

    # Filter only matches
    matches = merged[merged['paved_match'] == 1]

    # Group by ISO3 and surface class
    summary = matches.groupby(['country_iso_a3', 'combined_surface_DL_priority'])[['length_heigit_m', 'length_db_m']].sum().reset_index()
    
    # Optional: Pivot the table to have 'paved' and 'unpaved' as rows under each ISO3
    pivot_table = summary.pivot(index='country_iso_a3', columns='combined_surface_DL_priority', values=['length_heigit_m', 'length_db_m'])

    # Flatten the MultiIndex columns
    pivot_table.columns = [f'{metric}_{surface}' for metric, surface in pivot_table.columns]
    pivot_table = pivot_table.reset_index()

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
