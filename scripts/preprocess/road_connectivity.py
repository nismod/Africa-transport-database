#!/usr/bin/env python
# coding: utf-8
import sys
import os
import re
import json
import pandas as pd
import igraph as ig
import geopandas as gpd
from utils_new import *
from tqdm import tqdm
tqdm.pandas()



def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters

    # Read the different location data from different extracts

    location_attributes = [
                            {
                                'type':'population',
                                'data_path':os.path.join(processed_data_path,
                                                        "admin_boundaries",
                                                        "un_urban_population",
                                                        "un_pop_df.gpkg"),
                                'layer_name':None,
                                'id_column':'city_id',
                                'iso_column': "ISO_A3",
                                'geometry_type':'Point'
                            },
                            {
                                'type':'airports',
                                'data_path':os.path.join(processed_data_path,
                                                        "infrastructure",
                                                        "africa_airport_network.gpkg"),
                                'node_type_column':'infra',
                                'layer_name':'nodes',
                                'node_type':['airport'],
                                'id_column':'id',
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
                                'id_column':'id',
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
                                'node_type_column':'infra',
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

    
    all_point_locations_df = []
    all_polygon_locations_df = []
    countries = []
    for location in location_attributes:
        id_col = location['id_column']
        iso_col = location['iso_column']
        location_df = gpd.read_file(location['data_path'],layer=location['layer_name'])
        if location['type'] in ('maritime ports','inland ports','railways','airports'):
            location_df = location_df[
                                location_df[
                                    location['node_type_column']
                                    ].isin(location['node_type'])
                                ]
        elif location['type'] in ("population"):
            location_df = location_df[location_df["CONTINENT"] == "Africa"]
        location_df = location_df.to_crs(epsg=epsg_meters)
        location_df = location_df[[id_col,iso_col,'geometry']]
        location_df.rename(columns={id_col:"location_id",iso_col:"location_iso"},inplace=True)
        countries += list(set(location_df["location_iso"].values.tolist()))
        if location["geometry_type"] == "Point":
            all_point_locations_df.append(location_df)
        elif location["geometry_type"] == "Polygon":
            all_polygon_locations_df.append(location_df)

    connection_type = {"Point":pd.DataFrame(),"Polygon":pd.DataFrame()}
    if len(all_point_locations_df) > 0:
        all_point_locations_df = gpd.GeoDataFrame(
                                        pd.concat(all_point_locations_df,axis=0,ignore_index=True),
                                        geometry="geometry", 
                                        crs=f"EPSG:{epsg_meters}"
                                        ) 
        connection_type["Point"] = all_point_locations_df
    if len(all_polygon_locations_df) > 0:
        all_polygon_locations_df = gpd.GeoDataFrame(
                                        pd.concat(all_polygon_locations_df,axis=0,ignore_index=True),
                                        geometry="geometry", 
                                        crs=f"EPSG:{epsg_meters}"
                                        )
        connection_type["Polygon"] = all_polygon_locations_df

    countries = list(set(countries))
    nearest_roads = []
    for m_c in countries:
        country_roads = road_edges[(
                    road_edges["from_iso_a3"] == m_c
                    ) | (road_edges["to_iso_a3"] == m_c)]
        connected_nodes = list(set(country_roads.from_id.values.tolist() + country_roads.to_id.values.tolist()))
        country_nodes = road_nodes[road_nodes[node_id_column].isin(connected_nodes)] 
        if len(country_roads.index) > 0:
            targets = []
            for key,location_df in connection_type.items():
                if len(location_df.index) > 0:
                    location_df = location_df[location_df["location_iso"] == m_c]
                    if len(location_df.index) > 0:
                        if key == "Polygon":
                            # intersect pop and other infrastructures with roads first to find which other infrastructures have roads on them
                            loc_intersects = gpd.sjoin_nearest(location_df,
                                                country_roads[[road_id_column,road_type_column,"geometry"]],
                                                how="left").reset_index()
                            # get the intersected roads which are not the main roads
                            selected_edges = list(set(loc_intersects[road_id_column].values.tolist()))
                            polygon_roads = country_roads[country_roads[road_id_column].isin(selected_edges)]
                            targets += list(set(polygon_roads.from_id.values.tolist() + polygon_roads.to_id.values.tolist()))

                            del selected_edges, polygon_roads
                        else:
                            loc_intersects = ckdnearest(location_df,
                                                    country_nodes[[node_id_column,"geometry"]])
                            targets += list(set(loc_intersects[node_id_column].tolist()))
                        del loc_intersects

            if len(targets) > 0:
                targets = list(set(targets))
                graph = create_igraph_from_dataframe(
                                    country_roads[["from_id","to_id",road_id_column,"length_m"]]
                                    )
                A = sorted(graph.connected_components().subgraphs(),key=lambda l:len(l.es[road_id_column]),reverse=True)
                for j in range(len(A)):
                    connected_edges = A[j].es[road_id_column]
                    connected_roads_df = country_roads[country_roads[road_id_column].isin(connected_edges)]
                    connected_nodes = list(set(connected_roads_df.from_id.values.tolist() + connected_roads_df.to_id.values.tolist()))
                    sinks = [t for t in targets if t in connected_nodes]
                    if len(sinks) > 0:
                        source_df = connected_roads_df[connected_roads_df[road_type_column].isin(main_road_types)]
                        if len(source_df.index) > 0:
                            source = source_df.from_id.values[0]
                            n_r, _ = network_od_path_estimations(A[j],source,sinks,"length_m",road_id_column)
                            connected_roads = list(set([item for sublist in n_r for item in sublist]))
                            nearest_roads += connected_roads
                        else:
                            nearest_roads += connected_edges

        
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

    nearest_nodes.to_file(os.path.join(
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