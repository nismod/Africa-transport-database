import geopandas as gpd
import glob
import os
from utils_new import *

def main(config):
    input_folder = config['paths']['incoming_data']
    output_folder = config['paths']['data']
    # Folder containing your GPKG files
    
    output_file = 'merged_roadsurface_lines.gpkg'

    # Match all GPKG files
    gpkg_files = glob.glob(os.path.join(input_folder,"Randhawaetal_2025_Locations",'heigit_*_roadsurface_lines.gpkg'))

    if not gpkg_files:
        raise FileNotFoundError(f"No files found in '{input_folder}' matching pattern 'heigit_*_roadsurface_lines.gpkg'.")

    merged_gdf = []
    layer_name = None

    for gpkg_path in gpkg_files:
        try:
            # Read GeoDataFrame
            gdf = gpd.read_file(gpkg_path, layer=layer_name)
            country_code = os.path.basename(gpkg_path).split('_')[1]
            gdf['country'] = country_code
            merged_gdf.append(gdf)
        except Exception as e:
            print(f"Skipping {gpkg_path}: {e}")

    # Final merge
    if not merged_gdf:
        raise ValueError("No valid GeoDataFrames were loaded. Nothing to merge.")

    final_gdf = gpd.GeoDataFrame(
                        pd.concat(merged_gdf, axis=0, ignore_index=True),
                        geometry="geometry",
                        crs="EPSG:4326")

    # Save to GeoPackage
    
    

    # Write to a new GeoPackage
    final_gdf.to_parquet(os.path.join(
                            output_folder,
                            "infrastructure",
                            "validation_file_merge.geoparquet"))
   

    

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)    
