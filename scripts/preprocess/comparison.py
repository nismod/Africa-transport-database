import sys
import os
import re
import json
import pandas as pd
import geopandas as gpd
import snkit
from shapely.geometry import LineString
from utils_new import *
from tqdm import tqdm
tqdm.pandas()

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    rail_paths = os.path.join(processed_data_path,"infrastructure","africa_railways_network.gpkg")
    print(rail_paths)
    rail_database=gpd.read_file(rail_paths)
    print(rail_database.head())
    rail_database_original=gpd.read_file("C:\\Users\\cenv1075\\OneDrive - Nexus365\\Africa Database\\Infrastructure\\africa_railways_network.gpkg")
    print(rail_database_original.head())

    #rail_database_original["any"] = rail_database.any(axis=1,bool_only=True).values
    rail_database_comp=rail_database_original.merge(rail_database,indicator=True,how='left')
    rail_database_comp._merge=rail_database_comp._merge.eq('both')
    print(rail_database_comp._merge=="False")
    n_diff=len(rail_database_comp._merge=="False")
    print("%d values are different from the original file" %n_diff)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)