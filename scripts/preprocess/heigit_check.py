import geopandas as gpd
import glob
import os
from utils_new import *

def create_tag(x):
    if (x["osm_class"] == x["combined_surface_DL_priority"]) & (x["osm_class"] == x["paved"]):
        return 0
    elif (x["paved"] == x["osm_class"]):
        return 1
    elif (x["paved"] == x["combined_surface_DL_priority"]):
        return 2
    else:
        return 3

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    output_path = config['paths']['results']
    figure_path = config['paths']['figures']
    
    epsg_meters = 3395
    # Write to a new GeoPackage
    database_lines = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges.geoparquet"))
    heigit_lines = gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "validation_file_merge.geoparquet"))
    global_boundaries = gpd.read_file(os.path.join(processed_data_path,
                                    "admin_boundaries",
                                    "gadm36_levels_gpkg",
                                    "gadm36_levels_continents.gpkg"))
    countries = list(set(database_lines["from_iso_a3"].values.tolist() + database_lines["to_iso_a3"].values.tolist()))
    global_boundaries = global_boundaries[global_boundaries["ISO_A3"].isin(countries)]

    edge_ids = list(set(database_lines["osm_way_id"].values.tolist()))
    heigit_lines = heigit_lines[heigit_lines["osm_id"].isin(edge_ids)]
    heigit_lines = heigit_lines.drop_duplicates(subset=["osm_id"],keep="first")
    heigit_lines.rename(columns={"country":"country_iso_a3"},inplace=True)
    
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

        b_df = heigit_lines[heigit_lines["country_iso_a3"] == country]
        df = gpd.overlay(b_df,boundary_df,how="intersection")
        if len(df.index) > 0:
            df["heigit_length_m"] = df.geometry.length
            heigit_clipped_df.append(df)


        print (f"* Done with {country}")

    database_lines = pd.concat(database_clipped_df, axis=0, ignore_index=True)
    # 4. Group database_lines to get summed lengths per osm_id/paved
    database_lines["paved"] = database_lines["paved"].str.lower()
    database_lines["paved_type"
        ] = np.where(database_lines["paved"] == "true","paved","unpaved")
    database_lines = database_lines.groupby(['osm_way_id','country_iso_a3','paved_type'])['length_m'].sum().reset_index()
    database_lines.rename(columns={'osm_way_id': 'osm_id'}, inplace=True)

    heigit_lines = pd.concat(heigit_clipped_df, axis=0, ignore_index=True)
    heigit_lines = heigit_lines.groupby(['osm_id','country_iso_a3','combined_surface_DL_priority'])['heigit_length_m'].sum().reset_index()
    matched_df = pd.merge(heigit_lines,database_lines,how="left",on=["osm_id","country_iso_a3"])
    
    matched_df["length_heigit_m"] = matched_df["length_m"]
    matched_df["length_db_m"] = matched_df["length_m"]
    matched_df.drop("length_m",axis=1,inplace=True)
    matched_df.to_parquet(os.path.join(output_path,"merged_validation_datasets.parquet"))

    # Group by ISO3 and surface class
    # Heigit grouping
    heigit_summary = (
        matched_df.groupby(['country_iso_a3', 'combined_surface_DL_priority'])['length_heigit_m']
        .sum()
        .unstack(fill_value=0)
        .add_prefix('length_heigit_m_')
    )

    # DB grouping
    db_summary = (
        matched_df.groupby(['country_iso_a3', 'paved'])['length_db_m']
        .sum()
        .unstack(fill_value=0)
        .add_prefix('length_db_m_')
    )

    # Merge both
    pivot_table = heigit_summary.join(db_summary, how='outer').fillna(0).reset_index()
    # Export the pivot table
    pivot_table.to_csv(os.path.join(
                            output_path,
                            "merged_validation_datasets_corrected.csv"))   
    
    
if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)    
