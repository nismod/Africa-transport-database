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
    road_paths = os.path.join(incoming_data_path,"africa_roads","africa_main_roads.gpkg")
    print(road_paths)
    road_database=gpd.read_file(road_paths)
    print(road_database.head())
    road_database_original=gpd.read_file("C:\\Users\\cenv1075\\OneDrive - Nexus365\\Africa Database\\Infrastructure\\africa_main_roads.gpkg")
    print(road_database_original.head())

    difference=road_database.compare(road_database_original, align_axis=1, keep_shape=False, keep_equal=False, result_names=('self', 'other'))
    print(difference)


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)