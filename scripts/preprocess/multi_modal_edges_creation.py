#!/usr/bin/env python
# coding: utf-8
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from utils_new import *
from tqdm import tqdm
tqdm.pandas()

config = load_config()
incoming_data_path = config['paths']['incoming_data']
processed_data_path = config['paths']['data']


def get_mode_dataframe(
                        mode,
                        rail_status=["open","planned","construction"],
                        rail_to_mode_connection=False,
                        rail_facilities=None,
                        node_degree=None):
    if mode == "air":
        nodes =  gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_airport_network.gpkg"
                                    ), layer="nodes"
                                )  
        nodes = nodes[nodes["infra"] == "airport"]   
    elif mode == "sea":
        nodes =  gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_maritime_network.gpkg"
                                    ), layer="nodes"
                                )  
        nodes = nodes[nodes["infra"] == "port"]
    elif mode == "IWW":
        nodes = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_iww_network.gpkg"
                                    ), layer="nodes"
                                ) 
        nodes = nodes[nodes["infra"] != "IWW route"]
    elif mode == "rail":
        rail_edges = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_railways_network.gpkg"
                                    ), layer="edges"
                        )
        rail_edges = rail_edges[rail_edges["status"].isin(rail_status)]
        rail_node_ids = list(set(rail_edges["from_id"].values.tolist() + rail_edges["to_id"].values.tolist()))
        nodes = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_railways_network.gpkg"
                                    ), layer="nodes"
                        )
        nodes = nodes[(nodes["id"].isin(rail_node_ids)) & (nodes["infra"].isin(['stop','station']))]

        degree_df = rail_edges[["from_id","to_id"]].stack().value_counts().rename_axis('id').reset_index(name='degree')
        nodes = pd.merge(nodes,degree_df,how="left",on=["id"])

        if rail_to_mode_connection is True:
            freight_facility_types = rail_facilities
            if node_degree is None:
                nodes = nodes[
                                                (
                                                    nodes["facility"].isin(freight_facility_types)
                                                )
                                            ]
            else:
                nodes = nodes[
                                                (
                                                    nodes["facility"].isin(freight_facility_types)
                                                ) | (
                                                    nodes["degree"] == node_degree
                                                )
                                            ]
    elif mode == "road": 
        nodes = gpd.read_parquet(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_roads_nodes.geoparquet"))
        nodes.rename(columns={"iso_a3":"iso3"},inplace=True)

    return nodes

def main():
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    from_modes = ["sea","sea","IWW","IWW","rail", "air","air"]
    to_modes = ["rail","road","rail","road","road","rail","road"]
    rail_facility_types = {
                                "air":["airport"]
                            ,
                                "sea":["port"]
                            ,
                                "IWW":["port (inland)","port (river)"]
                            ,
                                "road":[
                                        "port","port (dry)",
                                        "port (inland)",
                                        "port (river)",
                                        "road-rail transfer",
                                        "container terminal",
                                        "freight terminal",
                                        "freight marshalling yard",
                                        "agriculture",
                                        "coal terminal",
                                        "food storage",
                                        "food production",
                                        "fuel storage",
                                        "industrial area",
                                        "manufacturing",
                                        "military",
                                        "storage"
                                        ]
                            }

    multi_df = []
    for idx,(f_m,t_m) in enumerate(zip(from_modes,to_modes)):
        if f_m == "road" or t_m == "road":
            distance_threshold = 4000   # Found this by manual check
        else:
            distance_threshold = 3000   # Found this by manual check

        if f_m == "rail":
            f_df = get_mode_dataframe(
                                        f_m,
                                        rail_to_mode_connection=True,
                                        rail_facilities=rail_facility_types[t_m]
                                    )
            t_df = get_mode_dataframe(t_m)
        elif t_m == "rail":
            t_df = get_mode_dataframe(
                                        t_m,
                                        rail_to_mode_connection=True,
                                        rail_facilities=rail_facility_types[f_m]
                                    )
            f_df = get_mode_dataframe(f_m)
        else:
            f_df = get_mode_dataframe(f_m)
            t_df = get_mode_dataframe(t_m)
        f_t_df = create_edges_from_nearest_node_joins(
                            f_df.to_crs(epsg=epsg_meters),
                            t_df.to_crs(epsg=epsg_meters),
                            "id","id",
                            "iso3","iso3",
                            f_m,t_m,distance_threshold=distance_threshold)
        f_t_df = f_t_df.rename(columns={"from_iso_a3":"from_iso3","to_iso_a3":"to_iso3"})
        print(f_t_df)

        if len(f_t_df) > 0:
            multi_df.append(f_t_df)
            c_t_df = f_t_df[["from_id","to_id","from_infra",
                        "to_infra","from_iso3","to_iso3",
                        "link_type","length_m","geometry"]].copy()
            c_t_df.columns = ["to_id","from_id",
                        "to_infra","from_infra",
                        "to_iso3",
                        "from_iso3",
                        "link_type","length_m","geometry"]
            multi_df.append(c_t_df)

    multi_df = gpd.GeoDataFrame(
                    pd.concat(multi_df,axis=0,ignore_index=True),
                    geometry="geometry",crs=f"EPSG:{epsg_meters}")
    multi_df = multi_df.to_crs(epsg=4326)
    multi_df["id"] = multi_df.index.values.tolist()
    multi_df["id"] = multi_df.progress_apply(lambda x:f"intermodale_{x.id}",axis=1)
    
    
    multi_df.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_multimodal.gpkg"
                                ), 
                            layer="edges",
                            driver="GPKG"
                            )

if __name__ == '__main__':
    main()