#!/usr/bin/env python
# coding: utf-8
import sys
import os
import re
import json
import pandas as pd
import geopandas as gpd
import snkit
from shapely.geometry import LineString
from updated_utils import *
from tqdm import tqdm
tqdm.pandas()

def get_line_status(x):
    if "abandon" in x:
        return "abandoned"
    else:
        return "open"

def add_attributes(dataframe,columns_attributes):
    for column_name,attribute_value in columns_attributes.items():
        dataframe[column_name] = attribute_value

    return dataframe

def add_iso_code(df,df_id_column,incoming_data_path):
    # Insert countries' ISO CODE
    africa_boundaries = gpd.read_file(os.path.join(
                            incoming_data_path,
                            "Africa_GIS Supporting Data",
                            "a. Africa_GIS Shapefiles",
                            "AFR_Political_ADM0_Boundaries.shp",
                            "AFR_Political_ADM0_Boundaries.shp"))
    africa_boundaries.rename(columns={"DsgAttr03":"iso3"},inplace=True)
    # Spatial join
    m = gpd.sjoin(df, 
                    africa_boundaries[['geometry', 'iso3']], 
                    how="left", predicate='within').reset_index()
    m = m[~m["iso3"].isna()]        
    un = df[~df[df_id_column].isin(m[df_id_column].values.tolist())]
    un = gpd.sjoin_nearest(un,
                            africa_boundaries[['geometry', 'iso3']], 
                            how="left").reset_index()
    m = pd.concat([m,un],axis=0,ignore_index=True)
    return m

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    epsg_meters = 3395 # To convert geometries to measure distances in meters
    # Read a number of rail network files and convert them to networks first
    rail_paths = os.path.join(incoming_data_path,"africa_corridor_developments")
    input_descriptions = [
                            {
                                "project_name":"Conakry-Kankan Railway",
                                "points_file": None,
                                "lines_file": "guinea_rail.shp",
                                "points_layer":None,
                                "lines_layer":None,
                                "project_attributes":{"country":"Guinea",
                                                    "status":"abandoned",
                                                    "mode":"mixed",
                                                    "gauge":1000,
                                                    "line":"Conakry-Kankan Railway"},
                                "distance_threshold":300

                            },
                            {
                                "project_name":"Simandou railway project",
                                "points_file": "17D.1.gpkg",
                                "lines_file": "17D.1.gpkg",
                                "points_layer":"17d1_points",
                                "lines_layer":"17d1_lines",
                                "project_attributes":{"country":"Guinea",
                                                    "status":"construction",
                                                    "mode":"freight",
                                                    "gauge":1435,
                                                    "line":"Simandou-Conakry Railway (or Transguinean Railway)"},
                                "distance_threshold":300

                            },
                            {
                                "project_name":"Togo Rail",
                                "points_file": "togo_lines.gpkg",
                                "lines_file": "togo_lines.gpkg",
                                "points_layer":"nodes",
                                "lines_layer":"lines",
                                "project_attributes":{"country":"Togo",
                                                    "status":"proposed",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"Lomé – Cinkassé Railway"},
                                "distance_threshold":300

                            },
                            {
                                "project_name":"Ghana Burkina Faso",
                                "points_file": "Team.gpkg",
                                "lines_file": "Team.gpkg",
                                "points_layer":"team_points",
                                "lines_layer":"team_lines",
                                "project_attributes":{"country":"Ghana-Burkina Faso",
                                                    "status":"construction",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"Tema-Ouagadougou Railway"},

                            },
                            {
                                "project_name":"Isaka Kigali Gitega Railway",
                                "points_file": "Dar_es.gpkg",
                                "lines_file": "Dar_es.gpkg",
                                "points_layer":"dar_es_points",
                                "lines_layer":"dar_es_lines",
                                "project_attributes":{"country":"Tanzania-Rwanda-Burundi",
                                                    "status":"proposed",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"Isaka - Kigali - Gitega Standard Gauge Railway"},
                                "distance_threshold":300

                            },
                            {
                                "project_name":"East Africa Railway",
                                "points_file": "eastafrica_rail.gpkg",
                                "lines_file": "eastafrica_rail.gpkg",
                                "points_layer":"eastafrica_points",
                                "lines_layer":"eastafrica_edges",
                                "project_attributes":{"country":"Kenya-Uganda-DRC-Rwanda-Burundi-South Sudan-Ethopia",
                                                    "status":"proposed",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"East Africa Standard Gauge Railway"},
                                "distance_threshold":1000

                            },
                            {
                                "project_name":"Kinshasa Ilebo Railway",
                                "points_file": None,
                                "lines_file": "kinsasha_rail.gpkg",
                                "points_layer":None,
                                "lines_layer":None,
                                "project_attributes":{"country":"DRC",
                                                    "status":"proposed",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"Kinshasa - Ilebo Railway"},
                                "distance_threshold":300

                            },
                            {
                                "project_name":"Tanzania Standard Gauge Railway",
                                "points_file": "tanzania_sgr_lines.gpkg",
                                "lines_file": "tanzania_sgr_lines.gpkg",
                                "points_layer":"nodes",
                                "lines_layer":"lines",
                                "project_attributes":{"country":"Tanzania",
                                                    "status":"contruction",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"Tanzania SGR Project"},
                                "distance_threshold":200

                            },
                            {
                                "project_name":"Standard Gauge Railway",
                                "points_file": None,
                                "lines_file": None,
                                "points_layer":"nodes",
                                "lines_layer":"edges",
                                "project_attributes":{"country":"Tanzania",
                                                    "status":"proposed",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"Isaka - Kigali - Gitega Standard Gauge Railway"},
                                "distance_threshold":100

                            },

                        ]
    processinng_step_one = False
    if processinng_step_one is True:
        for inputs in input_descriptions:
            distance_threshold = inputs["distance_threshold"]
            if inputs["points_file"] is not None:
                df_points = gpd.read_file(os.path.join(rail_paths,
                                    inputs["points_file"]),layer=inputs["points_layer"])
                df_points.columns = map(str.lower, df_points.columns)
            elif inputs["project_name"] == "Standard Gauge Railway":
                tza_sgr_nodes = gpd.read_file(os.path.join(rail_paths,
                            "tanzania_standard_gauge_railway.gpkg"),
                            layer="nodes")
                isaka_sgr_nodes = gpd.read_file(os.path.join(rail_paths,
                                    "isaka_kigali_gitega_railway.gpkg"),
                                    layer="nodes")
                df_points = pd.concat([tza_sgr_nodes,isaka_sgr_nodes],axis=0,ignore_index=True)
                df_points.drop(["node_id","component"],axis=1,inplace=True)
                df_points.columns = map(str.lower, df_points.columns)
                df_points = gpd.GeoDataFrame(df_points,geometry="geometry",crs="EPSG:4326")
            else:
                df_points = inputs["points_file"]
            
            if inputs["project_name"] == "Standard Gauge Railway":
                tza_sgr_lines = gpd.read_file(os.path.join(rail_paths,
                            "tanzania_standard_gauge_railway.gpkg"),
                            layer="edges")
                isaka_sgr_lines = gpd.read_file(os.path.join(rail_paths,
                                    "isaka_kigali_gitega_railway.gpkg"),
                                    layer="edges")
                df_lines = pd.concat([tza_sgr_lines,isaka_sgr_lines],axis=0,ignore_index=True)
                df_lines.drop(["edge_id","from_node","to_node","component"],axis=1,inplace=True)
                df_lines = gpd.GeoDataFrame(df_lines,geometry="geometry",crs="EPSG:4326")
            else:
                df_lines = gpd.read_file(os.path.join(rail_paths,
                            inputs["lines_file"]),layer=inputs["lines_layer"])

            df_lines.columns = map(str.lower, df_lines.columns)
            
            if inputs["project_name"] == "Conakry-Kankan Railway":
                df_lines = df_lines[df_lines["name"] == "Conakry-Kankan Railway"]
                df_lines.rename(columns={"name":"line"},inplace=True)
                df_lines["status"] = df_lines.progress_apply(lambda x:get_line_status(str(x["comments"]).lower()),axis=1)
                df_lines["country"] = "Guinea"
                df_lines["mode"] = np.where(df_lines["type2"] == "Freight & Passenger","mixed","freight")
                df_lines["gauge"] = 1000
                df_lines = df_lines[["country","line","status","mode","gauge","geometry"]]
            elif inputs["project_name"] in ["Tanzania Standard Gauge Railway","Togo Rail","Standard Gauge Railway"]:
                df_lines = df_lines[["country","line","status","mode","gauge","comment","geometry"]]
            else:
                df_lines = add_attributes(df_lines,inputs["project_attributes"])
                df_lines = df_lines[["country","line","status","mode","gauge","geometry"]]

            # df_lines = df_lines[["country","line","status","mode","gauge","geometry"]]
            df_crs = int(str(df_lines.crs).split(":")[1])
            network = create_network_from_nodes_and_edges(
                                        df_points,
                                        df_lines,"",
                                        geometry_precision=True)
            edges, nodes = components(network.edges,network.nodes,"node_id")
            edges = edges.set_crs(epsg=df_crs)
            nodes = nodes.set_crs(epsg=df_crs)
            max_edge_id = max([int(re.findall(r'\d+',v)[0]) for v in edges["edge_id"].values.tolist()])
            # Join network components which are very close
            all_components = list(set(nodes["component"].values.tolist()))
            component_dfs = []
            nodes = nodes.to_crs(epsg=epsg_meters)
            for c in range(len(all_components)-1):
                for p in range(c+1, len(all_components)):
                    c1 = nodes[nodes["component"] == all_components[c]][["node_id","geometry"]]
                    c2 = nodes[nodes["component"] == all_components[p]][["node_id","geometry"]]
                    distances = ckdnearest(c1,c2)
                    distances = distances[distances["dist"] <= distance_threshold]
                    print (distances)
                    if len(distances.index) > 0:
                        distances.columns = ["from_node","from_geometry","node_id","dist"]
                        distances = pd.merge(distances,c2,how="left",on=["node_id"])
                        distances.rename(columns={"node_id":"to_node","geometry":"to_geometry"},inplace=True)
                        distances["geometry"] = distances.progress_apply(lambda x:LineString([x.from_geometry,x.to_geometry]),axis=1)
                        distances["edge_id"] = list(max_edge_id + 1 + distances.index.values)
                        distances["edge_id"] = distances.progress_apply(lambda x: f"e_{x.edge_id}",axis=1)
                        distances.drop(["from_geometry","to_geometry","dist"],axis=1,inplace=True)
                        distances = add_attributes(distances,inputs["project_attributes"])
                        distances = gpd.GeoDataFrame(distances,geometry="geometry",crs=epsg_meters)
                        distances = distances.to_crs(epsg=df_crs)
                        component_dfs.append(distances)
                        max_edge_id = max(max_edge_id + 1 + distances.index.values)
        
            nodes = nodes.to_crs(epsg=df_crs)
            if len(component_dfs) > 0:
                edges = pd.concat([edges]+component_dfs,
                                axis=0,ignore_index=True)
                edges = gpd.GeoDataFrame(edges,geometry="geometry",crs=df_lines.crs)
                edges = edges.to_crs(epsg=epsg_meters)
                edges["length_m"] = edges.geometry.length
                edges = edges[edges["length_m"] > 0]
                edges = edges.to_crs(epsg=df_crs)

            edges, nodes = components(edges,nodes,"node_id","edge_id","from_node","to_node")
            output_file_name = inputs["project_name"].lower().replace(" ","_")
            gpd.GeoDataFrame(nodes,
                    geometry="geometry",
                    crs=df_lines.crs).to_file(os.path.join(
                                    rail_paths,
                                    f"{output_file_name}.gpkg"),
                                layer="nodes",driver="GPKG")
            gpd.GeoDataFrame(edges,
                    geometry="geometry",
                    crs=df_lines.crs).to_file(os.path.join(
                                    rail_paths,
                                    f"{output_file_name}.gpkg"),
                                layer="edges",driver="GPKG")

    input_descriptions = [
                            {
                                "project_name":"Guinea Lines",
                                "find_nearest":False

                            },
                            {
                                "project_name":"Simandou railway project",
                                "find_nearest":False
                            },
                            {
                                "project_name":"Togo Rail",
                                "find_nearest":False
                            },
                            {
                                "project_name":"Ghana Burkina Faso",
                                "find_nearest":False
                            },
                            {
                                "project_name":"Standard Gauge Railway",
                                "find_nearest":False
                            },
                            {
                                "project_name":"East Africa Railway",
                                "find_nearest":True,
                                "project_attributes":{"country":"Kenya-Uganda-DRC-Rwanda-Burundi-South Sudan-Ethopia",
                                                    "status":"proposed",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"East Africa Standard Gauge Railway"},
                                "distance_threshold":15.0
                            },
                            {
                                "project_name":"Kinshasa Ilebo Railway",
                                "find_nearest":True,
                                "project_attributes":{"country":"DRC",
                                                    "status":"proposed",
                                                    "mode":"mixed",
                                                    "gauge":1435,
                                                    "line":"Kinshasa - Ilebo Railway"},
                                "distance_threshold":2.0
                            },
                        ]
    processinng_step_two = True
    if processinng_step_two is True:
        rail_edges = gpd.read_file(os.path.join(incoming_data_path,
                            "africa_rail_network",
                            "network_data",
                            "africa_railways.gpkg"),layer="edges")
        max_edge_id = max(rail_edges.oid.values.tolist())
        df_crs = int(str(rail_edges.crs).split(":")[1])
        rail_nodes = json.load(open(os.path.join(incoming_data_path,
                            "africa_rail_network",
                            "network_data",
                            "africa_rail_nodes.geojson")))
        rail_nodes = convert_json_geopandas(rail_nodes)
        rail_nodes = rail_nodes.to_crs(epsg=4326)
        max_node_id = max(rail_nodes.oid.values.tolist())

        select_ids = list(set(rail_edges["source"].values.tolist() + rail_edges["target"].values.tolist()))
        rail_nodes = rail_nodes[rail_nodes["oid"].isin(select_ids)]

        print ("* Selected main rail edges and nodes")
        all_edges = [rail_edges]
        all_nodes = [rail_nodes]
        for inputs in input_descriptions:
            output_file_name = inputs["project_name"].lower().replace(" ","_")
            df_nodes = gpd.read_file(os.path.join(
                                    rail_paths,
                                    f"{output_file_name}.gpkg"),
                                layer="nodes")

            df_nodes["oid"] = list(max_node_id + 1 + df_nodes.index.values)
            for del_col in ["component"]:
                if del_col in df_nodes.columns.values.tolist():
                    df_nodes.drop(del_col,axis=1,inplace=True)

            df_edges = gpd.read_file(os.path.join(
                                    rail_paths,
                                    f"{output_file_name}.gpkg"),
                                layer="edges")

            for del_col in ["oid","edge_id","source","target","component"]:
                if del_col in df_edges.columns.values.tolist():
                    df_edges.drop(del_col,axis=1,inplace=True)
            
            df_edges = pd.merge(df_edges,
                            df_nodes[["node_id","oid"]],
                            how="left",
                            left_on=["from_node"],right_on=["node_id"])
            df_edges.rename(columns={"oid":"source"},inplace=True)
            df_edges.drop(["from_node","node_id"],axis=1,inplace=True)
            df_edges = pd.merge(df_edges,
                            df_nodes[["node_id","oid"]],
                            how="left",
                            left_on=["to_node"],right_on=["node_id"])
            df_edges.rename(columns={"oid":"target"},inplace=True)
            df_edges.drop(["to_node","node_id"],axis=1,inplace=True)
            df_edges["oid"] = list(max_edge_id + 1 + df_edges.index.values)
            
            all_edges.append(df_edges)
            max_edge_id = max(max_edge_id + 1 + df_edges.index.values)
            if inputs["find_nearest"] is True:
                distance_threshold = inputs["distance_threshold"]
                df_nodes_mod = []
                c2 = rail_nodes.copy()[["oid","geometry"]].to_crs(epsg=epsg_meters)
                c1 = df_nodes.copy()[["oid","geometry"]].to_crs(epsg=epsg_meters)
                c1.rename(columns={"oid":"source"},inplace=True)
                dist = ckdnearest(c1,c2)
                same_points = dist[dist["dist"] <= 1.0e-2]
                if len(same_points.index) > 0:
                    for r in same_points.itertuples():
                        df_nodes.loc[df_nodes.oid == r.source,"oid"] = r.oid
                        df_edges.loc[df_edges.source == r.source,"source"] = r.oid
                        df_edges.loc[df_edges.target == r.source,"target"] = r.oid
                    df_nodes = df_nodes[~df_nodes.oid.isin(same_points.oid.values.tolist())]
                distances = dist[(dist["dist"] > 1.0e-2) & (dist["dist"] <= distance_threshold)]
                if len(distances.index) > 0:
                    distances.columns = ["source","from_geometry","oid","dist"]
                    distances = pd.merge(distances,c2,how="left",on=["oid"])
                    distances.rename(columns={"oid":"target","geometry":"to_geometry"},inplace=True)
                    distances["geometry"] = distances.progress_apply(lambda x:LineString([x.from_geometry,x.to_geometry]),axis=1)
                    distances["oid"] = list(max_edge_id + 1 + distances.index.values)
                    distances.drop(["from_geometry","to_geometry","dist"],axis=1,inplace=True)
                    distances = add_attributes(distances,inputs["project_attributes"])
                    distances = gpd.GeoDataFrame(distances,geometry="geometry",crs=epsg_meters)
                    distances = distances.to_crs(epsg=df_crs)
                    all_edges.append(distances)
                    max_edge_id = max(max_edge_id + 1 + distances.index.values)

            all_nodes.append(df_nodes)
            max_node_id = max(max_node_id + 1 + df_nodes.index.values)
            print (f"* Added rail edges and nodes for {inputs['project_name']}")

        all_edges = pd.concat(all_edges,axis=0,ignore_index=True)
        all_nodes = pd.concat(all_nodes,axis=0,ignore_index=True)

        edges, nodes = components(all_edges,all_nodes,"oid","oid","source","target")
        print ("* Added components")

        nodes = gpd.GeoDataFrame(nodes,geometry="geometry",crs=rail_edges.crs)
        nodes = add_iso_code(nodes,"oid",incoming_data_path)
        for del_col in ["node_id","index","index_right"]:
            if del_col in nodes.columns.values.tolist():
                nodes.drop(del_col,axis=1,inplace=True)
        
        nodes.rename(columns={"oid":"id","type":"infra"},inplace=True)

        edges = gpd.GeoDataFrame(edges,geometry="geometry",crs=rail_edges.crs)
        if "length" in edges.columns.values.tolist():
            edges.drop("length",axis=1,inplace=True)
        edges = edges.to_crs(epsg=epsg_meters)
        edges["length_m"] = edges.geometry.length
        edges = edges.to_crs(epsg=df_crs)

        edges = pd.merge(edges,nodes[["id","iso3"]],how="left",left_on=["source"],right_on=["id"])
        edges.rename(columns={"iso3":"from_iso_a3"},inplace=True)
        edges.drop("id",axis=1,inplace=True)

        edges = pd.merge(edges,nodes[["id","iso3"]],how="left",left_on=["target"],right_on=["id"])
        edges.rename(columns={"iso3":"to_iso_a3"},inplace=True)
        edges.drop("id",axis=1,inplace=True)

        nodes["id"] = nodes.progress_apply(lambda x:f"railn_{x.id}",axis=1)
        edges["oid"] = edges.progress_apply(lambda x:f"raile_{x.oid}",axis=1)
        edges["source"] = edges.progress_apply(lambda x:f"railn_{x.source}",axis=1)
        edges["target"] = edges.progress_apply(lambda x:f"railn_{x.target}",axis=1)
        edges.rename(columns={"oid":"id","source":"from_id","target":"to_id","type":"infra"},inplace=True)

        gpd.GeoDataFrame(nodes,
                geometry="geometry",
                crs=rail_edges.crs).to_file(os.path.join(
                        processed_data_path,
                        "infrastructure",
                        "africa_railways_network.gpkg"),
                        layer="nodes",driver="GPKG")
        gpd.GeoDataFrame(edges,
                geometry="geometry",
                crs=rail_edges.crs).to_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_railways_network.gpkg"),
                            layer="edges",driver="GPKG")
 




if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)