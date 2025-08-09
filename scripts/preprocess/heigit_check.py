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
    
    country = "ZAF"
    epsg_meters = 32736

    database_lines=gpd.read_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges_FINAL.geoparquet"))
    database_lines["paved"] = database_lines['paved'].astype(str).str.lower()
    database_lines["paved"
        ] = np.where(database_lines["paved"] == 'true',"paved","unpaved")
    print (database_lines["paved"])

    merged = pd.read_parquet(os.path.join(
                            output_path,
                            "merged_validation_datasets.parquet"))
    merged.rename(columns={"paved_type":"paved"},inplace=True)
    merged["check"] = merged.apply(lambda x:create_tag(x),axis=1)
    merged = merged.value_counts(subset=['country_iso_a3','check'], sort=False).reset_index()
    merged["country_total"] = merged.groupby(["country_iso_a3"])["count"].transform("sum")
    merged["proportion"] = 100.0*merged["count"]/merged["country_total"]
    print (merged)
    
if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)    
