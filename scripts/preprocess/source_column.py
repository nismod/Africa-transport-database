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

def main():

    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    epsg_meters = 3395 # To convert geometries to measure distances in meters   

    ports_nodes = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_maritime_network.gpkg"),layer = 'nodes') 
    ports_edges = gpd.read_file(os.path.join(processed_data_path,
                                    "infrastructure",
                                    "africa_maritime_network.gpkg"),layer = 'edges')
    
    source_port = [
    "Padilla, A. D., Otarod, D., Deloach-Overton, S. W., Kemna, R. F., Freeman, P. A., Wolfe, E. R., ... & Brioche, A. S. Compilation of geospatial data (GIS) for the mineral industries and related infrastructure of Africa. US Geological Survey. https://doi.org/10.5066/P97EQWXP (2021).",
    "Thorn, J. P.R., Mwangi, B.; Juffe Bignoli, D., The African Development Corridors Database. Dryad, Dataset. https://doi.org/10.5061/dryad.9kd51c5hw (2022)."
    ]

    source_other = [
        "UN Global Platform; IMF PortWatch https://portwatch.imf.org/",
        "Verschuur, J. Global multi-hazard risk to port infrastructure and trade. Mendeley Data. V1, doi: 10.17632/kdyt24tsh5.1 (2022).",
        "Modelled"
    ]

    mask_port = (ports_nodes["vessel_count_total"] == 0) & (ports_nodes["infra"] == "port")
    mask_maritime = ports_nodes["infra"] == "maritime"

    ports_nodes.loc[mask_port, "source"] = ports_nodes.loc[mask_port].apply(
        lambda _: source_port, axis=1
    )

    ports_nodes.loc[mask_maritime, "source"] = ports_nodes.loc[mask_maritime].apply(
        lambda _: ["Modelled"], axis=1
    )

    ports_nodes.loc[~mask_port & ~mask_maritime, "source"] = ports_nodes.loc[~mask_port & ~mask_maritime].apply(
        lambda _: source_other, axis=1
    )
    ports_edges["source"] = [
    [
        "Verschuur, J. Global multi-hazard risk to port infrastructure and trade. Mendeley Data. V1, doi: 10.17632/kdyt24tsh5.1 (2022).",
        "Modelled"
    ]]* len(ports_edges)
   
    ports_edges.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_maritime_network_withsources.gpkg"),
                        layer="edges",driver="GPKG")
    ports_nodes.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_maritime_network_withsources.gpkg"),
                        layer="nodes",driver="GPKG")
    
    
    
    air_nodes_df = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network_rev.gpkg"
                                ), 
                            layer="nodes"
                            )
    air_edges_df = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network_rev.gpkg"
                                ), 
                            layer="edges"
                            )
    
    air_nodes_df["source"] = [
    [
        "World Bank Group. Global Airports: Locations of airports with international travel. https://datacatalog.worldbank.org/search/dataset/0038117/Global-Airports (2020).",
        "OurAirports. Airport data. https://ourairports.com/ (accessed June 2025).",
        "Modelled"
    ]]* len(air_nodes_df)
    air_edges_df["source"] = [
    [
        "World Bank Group. Global Airports: Locations of airports with international travel. https://datacatalog.worldbank.org/search/dataset/0038117/Global-Airports (2020)."
    ]]* len(air_edges_df)

    print(air_nodes_df)
    print(air_edges_df)

    air_edges_df.to_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_airport_network_withsources.gpkg"),
                        layer="edges",driver="GPKG")
    air_nodes_df.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_airport_network_withsources.gpkg"),
                        layer="nodes",driver="GPKG")
    

    multi_df = gpd.read_file(os.path.join(
                            processed_data_path,
                            "infrastructure",
                            "africa_multimodal_rev.gpkg"
                                ), 
                            layer="edges"
                            )
    
    multi_df["source"] = [
    [
        "Modelled"
    ]]* len(multi_df)

    print(multi_df)

    multi_df.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_multimodal_withsources.gpkg"),
                            layer="edges",driver="GPKG")

    roads_nodes_df = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_roads_network.gpkg"
                                    ), 
                                layer="nodes"
                                )
    roads_edges_df = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_roads_network.gpkg"
                                    ), 
                                layer="edges"
                                )


    source_corridors_edges = [
    "AfDB. Cross-border Road Corridors: The Quest to Integrate Africa.(2019)",
    "Expanding Market Access in Africa and Nurturing Continental Integration. (2023).",
    "Tripartite Transport and Transit Facilitation Programme (TTTFP). https://tttfp.org/corridors/all-corridors/ (2019).",
    "Open Street Maps. Open Street Maps. https://download.geofabrik.de/ (2021).",
    "Modelled"
    ]

    source_other_edges = [
        "Open Street Maps. Open Street Maps. https://download.geofabrik.de/ (2021).",
        "Modelled"
    ]

    mask_corridors = roads_edges_df["corridor_name"].notna()
    mask_other = roads_edges_df["corridor_name"].isna()

    roads_edges_df.loc[mask_corridors, "source"] = (
        roads_edges_df.loc[mask_corridors]
        .apply(lambda _: source_corridors_edges, axis=1)
    )

    roads_edges_df.loc[mask_other, "source"] = (
        roads_edges_df.loc[mask_other]
        .apply(lambda _: source_other_edges, axis=1)
    )

    roads_nodes_df["source"] = [
        [
            "Open Street Maps. Open Street Maps. https://download.geofabrik.de/ (2021).",
            "Modelled"
        ]]* len(roads_nodes_df)
    
    roads_nodes_df.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_roads_network_withsources.gpkg"),
                            layer="nodes",driver="GPKG")
    roads_edges_df.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_roads_network_withsources.gpkg"),
                            layer="edges",driver="GPKG")
    

    rail_nodes_df = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_railways_network.gpkg"
                                    ), 
                                layer="nodes"
                                )
    rail_edges_df = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_railways_network.gpkg"
                                    ), 
                                layer="edges"
                                )


    source_infranull = [
    "Modelled"
    ]

    source_other_nodes = [
        "Open Street Maps. Open Street Maps. https://download.geofabrik.de/ (2021).",
        "Young, M. An Open Source Routable Rail Dataset For Africa. https://github.com/trg-rail/africa_rail_network"
    ]

    mask_infranulls = rail_nodes_df["infra"].isna()
    mask_other_nodes = rail_nodes_df["infra"].notna()

    rail_nodes_df.loc[mask_infranulls, "source"] = (
        rail_nodes_df.loc[mask_infranulls]
        .apply(lambda _: source_infranull, axis=1)
    )

    rail_nodes_df.loc[mask_other_nodes, "source"] = (
        rail_nodes_df.loc[mask_other_nodes]
        .apply(lambda _: source_other_nodes, axis=1)
    )



    source_rail_edges1 = ["Open Street Maps. Open Street Maps. https://download.geofabrik.de/ (2021).",
                        "AU-PIDA. African Union. PIDA projects. AU-PIDA https://www.au-pida.org/pida-projects/ (accessed February 2025).",
                        "Thorn, J. P.R., Mwangi, B.; Juffe Bignoli, D., The African Development Corridors Database. Dryad, Dataset. https://doi.org/10.5061/dryad.9kd51c5hw (2022).",              
                        "CPCS Transcom International Limited. East African Railways Master Plan Study: Final Report. Prepared for the East African Community (2009).",
                        "Modelled"
        ]

    source_rail_edges2 = ["Young, M. An Open Source Routable Rail Dataset For Africa. https://github.com/trg-rail/africa_rail_network"]

    mask_rail_edges1 = rail_edges_df["comment"].isna()
    mask_rail_edges2 = rail_edges_df["comment"].notna()

    rail_edges_df.loc[mask_rail_edges1, "source"] = (
        rail_edges_df.loc[mask_rail_edges1]
        .apply(lambda _: source_rail_edges1, axis=1)
    )

    rail_edges_df.loc[mask_rail_edges2, "source"] = (
        rail_edges_df.loc[mask_rail_edges2]
        .apply(lambda _: source_rail_edges2, axis=1)
    )
    
    
    rail_nodes_df.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_railways_network_withsources.gpkg"),
                            layer="nodes",driver="GPKG")
    rail_edges_df.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_railways_network_withsources.gpkg"),
                            layer="edges",driver="GPKG")
    
    iww_df_nodes = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_iww_network.gpkg"
                                    ), 
                                layer="nodes"
                                )
    iww_df_edges = gpd.read_file(os.path.join(
                                processed_data_path,
                                "infrastructure",
                                "africa_iww_network.gpkg"
                                    ), 
                                layer="edges"
                                )
    
    mask_nile = iww_df_nodes["waterbody"].isin(["Victoria Nile", "Nile river"])
    mask_iww = iww_df_nodes["infra"] == "IWW route"
    mask_osm = ~mask_nile & ~mask_iww  # everything else

    iww_df_nodes.loc[mask_nile, "source"] = (
        iww_df_nodes.loc[mask_nile]
        .apply(lambda _: ["NBI Technical Reports - WRM-2022-02. Nile River Navigation - Integration of scenarios for sector development into the Strategic Water Resources Analysis. https://nilebasin.org/sites/default/files/2023-09/WRM-2022-02_Nile%2520River%2520Navigation.pdf (2022)."],
                axis=1)
    )

    iww_df_nodes.loc[mask_iww, "source"] = (
        iww_df_nodes.loc[mask_iww]
        .apply(lambda _: ["Modelled"], axis=1)
    )

    iww_df_nodes.loc[mask_osm, "source"] = (
        iww_df_nodes.loc[mask_osm]
        .apply(lambda _: ["Africa Geoportal. OpenStreetMap Waterways for Africa. https://africageoportal.maps.arcgis.com/home/item.html?id=82232d0415c04e7086414dff7eb1310f"], 
               axis=1)
    )

    node_waterbody = iww_df_nodes.set_index("id")["waterbody"]
    iww_df_edges["from_waterbody"] = iww_df_edges["from_id"].map(node_waterbody)
    iww_df_edges["to_waterbody"] = iww_df_edges["to_id"].map(node_waterbody)

    victoria_lakes = ["Lake Victoria"]
    modelled_lakes = ["Lake Albert", "Lake Kivu", "Lake Mweru", "Lake Tanganyika"]

    mask_victoria = (
        iww_df_edges["from_waterbody"].isin(victoria_lakes) |
        iww_df_edges["to_waterbody"].isin(victoria_lakes)
    )

    mask_modelled = (
        iww_df_edges["from_waterbody"].isin(modelled_lakes) |
        iww_df_edges["to_waterbody"].isin(modelled_lakes)
    )

    mask_osm = ~mask_victoria & ~mask_modelled

    iww_df_edges.loc[mask_victoria, "source"] = (
    iww_df_edges.loc[mask_victoria]
    .apply(lambda _: ["Lake Victoria Routes. https://victoriatugandbarge.com/routes (accessed August 2025)."], axis=1)
    )

    iww_df_edges.loc[mask_modelled, "source"] = (
        iww_df_edges.loc[mask_modelled]
        .apply(lambda _: ["Modelled", "Pant, R., Koks, E. E., Russell, T., & Hall, J. W. Transport Risks Analysis for The United Republic of Tanzania - Systemic vulnerability assessment of multi-modal transport networks. Final Report Draft. Oxford, UK (2018).", "Munyangeyo, A., & Gudmestad, O. T. Safety aspects for inland personnel transport; case study Congo River. In ISOPE International Ocean and Polar Engineering Conference (pp. ISOPE-I). ISOPE (2022)."], axis=1)
    )

    iww_df_edges.loc[mask_osm, "source"] = (
        iww_df_edges.loc[mask_osm]
        .apply(lambda _: ["Africa Geoportal. OpenStreetMap Waterways for Africa. https://africageoportal.maps.arcgis.com/home/item.html?id=82232d0415c04e7086414dff7eb1310f"], axis=1)
    )

    iww_df_nodes.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_iww_network_withsources.gpkg"),
                            layer="nodes",driver="GPKG")
    iww_df_edges.to_file(os.path.join(processed_data_path,
                            "infrastructure",
                            "africa_iww_network_withsources.gpkg"),
                            layer="edges",driver="GPKG")



if __name__ == '__main__':
    main()