#!/usr/bin/env python
# coding: utf-8
# (1) Merge three datasets; (2)Add ISO3 (4) extract non_intersected
import sys
import os
import re
import pandas as pd
import geopandas as gpd
import igraph as ig
from utils import *
from tqdm import tqdm
tqdm.pandas()

def convert_units(y):
    if y in ['Metric tons','Metric tons (storage)','Metrict tons']:
        return 1.0
    elif y == 'Metric tons per day':
        return 365.0
    elif y == 'Million metric tons':
        return 1.0e6
    elif y == 'MTEU':
        return 12.0*1e6
    elif y == 'Kilograms':
        return 1.0/1000.0
    elif y == 'Thousand metric tons':
        return 1000.0
    elif y == '42-gallon barrels per day':
        return 42*264.17*365.0
    elif y == '42-gallon barrels (presumed)':
        return 42*264.17
    elif y in ['Thousand 42-gallon barrels','Thousand barrels']:
        return 42*264.17*1000.0
    elif y == 'Thousand barrels per day':
        return 42*264.17*1000.0*365
    elif y in ['Cubic meters (presumed)','Cubic metres']:
        return 2.41
    elif y == 'Million cubic meters':
        # 1 m3 = 2.41 metric tons
        return 1.0e6*2.41
    elif y == 'Thousand bricks':
        # Assume each brick weighs 3.5kg
        return 3.5
    elif y == 'Thousand carats':
        return 2.0e-7*1.0e3
    else:
        return 0.0

def find_ref_mineral(x,m):
    if m in str(x["commodity_group_export"]).lower():
        return 1
    elif m in str(x["commodity_subgroup_export"]).lower():
        return 1
    else:
        return 0

def main(config):
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    
    port_matches = pd.read_excel(
                    os.path.join(incoming_data_path,
                        "ports",
                        "all_ports_matches.xlsx"),
                    sheet_name="matches")
    port_corridor = gpd.read_file(os.path.join(
                                incoming_data_path,
                                "africa_corridor_developments",
                                "AfricanDevelopmentCorridorDatabase2022.gpkg" 
                                ),layer='point')[["Project_code","Commodities_traded_or_transported"]]
    port_corridor.rename(columns={"Commodities_traded_or_transported":"commodity_subgroup"},inplace=True)
    port_corridor['corridor_annual_capacity_tons'] = port_corridor.progress_apply(
                                                        lambda x:";".join(["0"]*len(x["commodity_subgroup"].split(";"))),
                                                        axis=1)

    port_matches = pd.merge(port_matches,port_corridor,how="left",on=["Project_code"])
    usgs_ports = gpd.read_file(os.path.join(
                                incoming_data_path,
                                "Africa_GIS Supporting Data",
                                "a. Africa_GIS Shapefiles",
                                "AFR_Infra_Transport_Ports.shp",
                                "AFR_Infra_Transport_Ports.shp"))
    usgs_ports["capacity_convert_tons"] = usgs_ports.progress_apply(
                                            lambda x:convert_units(x['DsgAttr06']),
                                            axis=1)
    usgs_ports['usgs_annual_capacity_tons'] = usgs_ports["DsgAttr05"]*usgs_ports["capacity_convert_tons"]
    usgs_ports.rename(columns={'DsgAttr03':"commodity_group_export",
                            'DsgAttr04':"commodity_subgroup_export"},
                        inplace=True)
    columns_merge = ['commodity_group_export','commodity_subgroup_export','usgs_annual_capacity_tons']
    df = []
    for col in columns_merge:
        df.append(usgs_ports.groupby(['FeatureUID'])[col].agg(
                [(col,  lambda x: ';'.join(map(str, x)))])) 

    df = pd.concat(df,axis=1).reset_index()

    port_matches = pd.merge(port_matches,df,how="left",on=['FeatureUID'])
    columns = ['commodity_group_export',
            'commodity_subgroup_export',
            'usgs_annual_capacity_tons',
            'commodity_subgroup',
            'corridor_annual_capacity_tons']
    for col in columns:
        port_matches[col] = port_matches[col].fillna('none')

    
    port_matches["commodity_group_export"] = port_matches[
                                                    ["commodity_group_export",
                                                    "commodity_subgroup"]].apply(
                                            lambda x : ';'.join(x), axis = 1).str.replace('none', '').str.strip(';')
    port_matches["commodity_subgroup_export"] = port_matches[
                                                    ["commodity_subgroup_export",
                                                    "commodity_subgroup"]].apply(
                                            lambda x : ';'.join(x), axis = 1).str.replace('none', '').str.strip(';')
    port_matches["annual_capacity_tons"] = port_matches[
                                                    ["usgs_annual_capacity_tons",
                                                    "corridor_annual_capacity_tons"]].apply(
                                            lambda x : ';'.join(x), axis = 1).str.replace('none', '').str.strip(';')
    
    port_matches = port_matches[["id","commodity_group_export",
                                "commodity_subgroup_export",
                                "annual_capacity_tons"]]
    df = []
    for col in ["commodity_group_export",
                "commodity_subgroup_export",
                "annual_capacity_tons"]:
        df.append(port_matches.groupby(['id'])[col].agg(
                [(col,  lambda x: ';'.join(map(str, x)))]))
    
    port_matches = pd.concat(df,axis=1).reset_index()
    # find ports with reference minerals
    reference_minerals = ["copper","cobalt","nickel","lithium","manganese","graphite"]
    for ref_m in reference_minerals:
        port_matches[f"{ref_m}_export_binary"] = port_matches.progress_apply(
                                            lambda x:find_ref_mineral(x,ref_m),axis=1)
    
    port_df = gpd.read_file(os.path.join(processed_data_path,
                    "infrastructure",
                    "global_maritime_network.gpkg"),
                    layer="nodes")
    port_df.drop("geometry",axis=1,inplace=True)
    port_utilisation = pd.read_csv(os.path.join(
                                processed_data_path,
                                "port_statistics",
                                "port_utilization.csv"))
    
    port_utilisation["annual_vessel_capacity_tons"] = 52.0*port_utilisation['dwt_per_week']
    port_matches = pd.merge(port_matches,port_df,how="left",on=["id"])

    vessel_types = list(set(port_utilisation["vessel_type_main"].values.tolist()))
    all_ports_utilisations = []
    for vt in vessel_types:
        df = port_utilisation[port_utilisation["vessel_type_main"] == vt]
        port_matches = pd.merge(port_matches,
                            df[["id","annual_vessel_capacity_tons"]],
                            how="left",on=["id"]).fillna(0)
        port_matches.rename(
                columns={"annual_vessel_capacity_tons":f"{vt.lower().replace(' ','_')}_annual_vessel_capacity_tons"},
                inplace=True)
        p_df = port_df[port_df["infra"] == "port"][["id","name","iso3"]]
        p_df["vessel_type_main"] = vt
        all_ports_utilisations.append(
                pd.merge(p_df,
                df[["id","annual_vessel_capacity_tons"]],
                how="left",on=["id"]).fillna(0))

    all_ports_utilisations = pd.concat(all_ports_utilisations,axis=0,ignore_index=True)
    print (all_ports_utilisations)
    all_ports_utilisations[
                ["id","name","iso3","vessel_type_main","annual_vessel_capacity_tons"]
                ].to_csv(os.path.join(processed_data_path,
                        "port_statistics",
                        "port_vessel_types_and_capacities.csv"),index=False)

    port_matches.to_csv(os.path.join(processed_data_path,
                        "port_statistics",
                        "port_known_commodities_traded.csv"),index=False)
    # df = []
    # for col in columns_merge:
    #     df.append(port_utilisation.groupby(['id'])[col].agg(
    #             [(col,  lambda x: ';'.join(map(str, x)))])) 

    # df = pd.concat(df,axis=1).reset_index()
    # df.to_csv(os.path.join(processed_data_path,
    #                     "port_statistics",
    #                     "port_vessel_types_and_capacities.csv"),index=False)



if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)