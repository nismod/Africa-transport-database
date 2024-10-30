#!/usr/bin/env python
# coding: utf-8
import sys
import os
import re
import json
import pandas as pd
import igraph as ig
import geopandas as gpd
from utils import *
from tqdm import tqdm
tqdm.pandas()



def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    # Read the different location data from different extracts
    location_attributes = [
                            {
                                'type':'mine',
                                'data_path':os.path.join(incoming_data_path,
                                                    "mines_spatial_locations",
                                                    "all_mines_adm.gpkg"),
                                'layer_name':None,
                                'id_column':'mine_id',
                                'iso_column': "shapeGroup_primary_admin0",
                                'geometry_type':'Polygon'
                            },
                            {
                                'type':'mine_s_p',
                                'data_path':os.path.join(processed_data_path,
                                                        "Minerals",
                                                        "s_and_p_mines_global_all.gpkg"),
                                'layer_name':None,
                                'id_column':'property_ID',
                                'iso_column': "ISO_A3",
                                'geometry_type':'Polygon'
                            },
                            {
                                'type':'population',
                                'data_path':os.path.join(processed_data_path,
                                                        "admin_boudaries",
                                                        "un_urban_population",
                                                        "un_pop_df.gpkg"),
                                'layer_name':None,
                                'id_column':'city_id',
                                'iso_column': "ISO_A3",
                                'geometry_type':'Point'
                            },
                            {
                                'type':'active processing site',
                                'data_path':os.path.join(
                                                    processed_data_path,
                                                    "Minerals",
                                                    "africa_mineral_processing_sites_active.gpkg"
                                                    ),
                                'layer_name':'nodes',
                                'id_column':'FeatureUID',
                                'iso_column': "iso3",
                                'geometry_type':'Point'
                            },
                            {
                                'type':'inactive processing site',
                                'data_path':os.path.join(
                                                    processed_data_path,
                                                    "Minerals",
                                                    "africa_mineral_processing_sites_inactive.gpkg"
                                                    ),
                                'layer_name':'nodes',
                                'id_column':'FeatureUID',
                                'iso_column': "iso3",
                                'geometry_type':'Point'
                            },
                            {
                                'type':'maritime ports',
                                'data_path':os.path.join(
                                                    processed_data_path,
                                                    "infrastructure",
                                                    "africa_maritime_network.gpkg"
                                                    ),
                                'layer_name':'nodes',
                                'node_type_column':'infra',
                                'node_type':['port'],
                                'id_column':'id',
                                'iso_column': "iso3",
                                'geometry_type':'Point'
                            },
                            {
                                'type':'inland ports',
                                'data_path':os.path.join(
                                                    processed_data_path,
                                                    "infrastructure",
                                                    "africa_iww_network.gpkg"
                                                    ),
                                'layer_name':'nodes',
                                'node_type_column':'infra',
                                'node_type':['IWW port'],
                                'id_column':'node_id',
                                'iso_column': "iso3",
                                'geometry_type':'Point'
                            },
                            {
                                'type':'railways',
                                'data_path':os.path.join(
                                                    processed_data_path,
                                                    "infrastructure",
                                                    "africa_railways_network.gpkg"
                                                    ),
                                'layer_name':'nodes',
                                'node_type_column':'type',
                                'node_type':['stop','station'],
                                'id_column':'id',
                                'iso_column': "iso3",
                                'geometry_type':'Point'
                            },


                        ]

    # Read the road edges data for Africa
    road_id_column = "id"
    node_id_column = "road_id"
    road_type_column = "tag_highway"
    main_road_types = ["trunk","motorway","primary","secondary"]
    road_edges = gpd.read_parquet(os.path.join(incoming_data_path,
                            "africa_roads",
                            "edges_with_topology.geoparquet"))
    road_nodes = gpd.read_parquet(os.path.join(incoming_data_path,
                            "africa_roads",
                            "nodes_with_topology.geoparquet"))
    road_nodes.rename(columns={"id":node_id_column},inplace=True)
    road_edges = road_edges.to_crs(epsg=epsg_meters)
    road_nodes = road_nodes.to_crs(epsg=epsg_meters) 
    main_roads = road_edges[
                        road_edges[road_type_column].isin(main_road_types)
                        ][road_id_column].values.tolist() 

    # We assume all the mines intersect the networks of the countries they are within
    # Seems like only a few mines are border mines, so our assumption is fine
    countries = []
    for location in location_attributes:
        location_df = gpd.read_file(location['data_path'],layer=location['layer_name'])
        if location['type'] in ('maritime ports','inland ports','railways'):
            location_df = location_df[
                                location_df[
                                    location['node_type_column']
                                    ].isin(location['node_type'])
                                ]
        elif location['type'] == "mine":
            location_df = location_df[location_df["continent"] == "Africa"]
        elif location['type'] in ("mine_s_p","population"):
            location_df = location_df[location_df["CONTINENT"] == "Africa"]
        location_df = location_df.to_crs(epsg=epsg_meters)
        location['gdf'] = location_df
        countries += list(set(location_df[location['iso_column']].values.tolist()))
    countries = list(set(countries))

    nearest_roads = []
    for m_c in countries[0]:
        country_roads = road_edges[(
                    road_edges["from_iso_a3"] == m_c
                    ) & (road_edges["to_iso_a3"] == m_c)]
        if len(country_roads.index) > 0:
            graph = create_igraph_from_dataframe(
                    country_roads[["from_id","to_id",road_id_column,"length_m"]])
            A = sorted(graph.conected_components().subgraphs(),key=lambda l:len(l.es[road_id_column]),reverse=True)
            connected_edges = A[0].es[road_id_column]
            country_roads = country_roads[country_roads[road_id_column].isin(connected_edges)]
            connected_nodes = list(set(country_roads.from_id.values.tolist() + country_roads.to_id.values.tolist()))
            country_nodes = road_nodes[road_nodes[node_id_column].isin(connected_nodes)]
            del connected_edges, connected_nodes, graph
            """Proximity to different kinds of locations of interest
            """
            # We just need access to one road in the main roud network, since the rest are connected
            source = country_roads[country_roads[road_type_column].isin(main_road_types)].from_id.values[0]
            for l in location_attributes:
                id_col = l['id_column']
                iso_col = l['iso_column']
                location_df = l['gdf'][[id_col,iso_col,'geometry']]
                location_df = location_df[location_df[iso_col] == m_c]
                if len(location_df.index) > 0:
                    if l['geometry_type'] == "Polygon":
                        # intersect mines with roads first to find which mines have roads on them
                        loc_intersects = gpd.sjoin_nearest(location_df[[id_col,"geometry"]],
                                            country_roads[[road_id_column,road_type_column,"geometry"]],
                                            how="left").reset_index()
                        # get the intersected roads which are not the main roads
                        # intersected_roads_df = loc_intersects[~loc_intersects[road_type_column].isin(main_road_types)]
                        # selected_edges = list(set(intersected_roads_df[road_id_column].values.tolist()))
                        selected_edges = list(set(loc_intersects[road_id_column].values.tolist()))
                        mining_roads = country_roads[country_roads[road_id_column].isin(selected_edges)]
                        targets = list(set(mining_roads.from_id.values.tolist() + mining_roads.to_id.values.tolist()))

                        del selected_edges, mining_roads
                    else:
                        loc_intersects = ckdnearest(location_df[[id_col,"geometry"]],
                                                country_nodes[[node_id_column,"geometry"]])
                        targets = list(set(loc_intersects[node_id_column].tolist()))
                    del loc_intersects
     
            
                    n_r, _ = network_od_path_estimations(A[0],source, targets,"length_m",road_id_column)
                    connected_roads = list(set([item for sublist in n_r for item in sublist]))
                
                    # nearest_roads.append(country_roads[country_roads[road_id_column].isin(connected_roads)])
                    nearest_roads += connected_roads

        print (f"* Done with country - {m_c}")

    # print (nearest_roads)
    nearest_roads = list(set(nearest_roads + main_roads))
    nearest_roads = road_edges[
                        road_edges[road_id_column].isin(nearest_roads)
                        ]
    nearest_roads = nearest_roads.to_crs(epsg=4326)
    connected_nodes = list(set(nearest_roads.from_id.values.tolist() + nearest_roads.to_id.values.tolist()))
    nearest_nodes = road_nodes[road_nodes[node_id_column].isin(connected_nodes)]
    nearest_nodes.rename(columns={node_id_column:"id"},inplace=True)
    nearest_nodes = nearest_nodes.to_crs(epsg=4326)

    edges = nearest_roads[[
            'from_id','to_id','id','osm_way_id','from_iso_a3','to_iso_a3',
            'tag_highway', 'tag_surface','tag_bridge','tag_maxspeed','tag_lanes',
            'bridge','paved','material','lanes','width_m','length_m','asset_type','geometry']]
    """Find the network components
    """
    edges, nearest_nodes = components(edges,nearest_nodes,node_id_column="id")
    
    """Assign border roads
    """
    edges["border_road"] = np.where(edges["from_iso_a3"] == edges["to_iso_a3"],0,1)

    nearest_nodes = gpd.GeoDataFrame(nearest_nodes,
                    geometry="geometry",
                    crs="EPSG:4326")

    edges = gpd.GeoDataFrame(edges,
                    geometry="geometry",
                    crs="EPSG:4326")

    nearest_nodes.to_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_nodes.geoparquet"))
    edges.to_parquet(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_roads_edges.geoparquet"))

    nearest_roads.to_file(os.path.join(
                            incoming_data_path,
                            "africa_roads",
                            "africa_main_roads.gpkg"),
                        layer="nodes",driver="GPKG")
    edges.to_file(os.path.join(
                            incoming_data_path,
                            "africa_roads",
                            "africa_main_roads.gpkg"),
                        layer="edges",driver="GPKG")






if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)