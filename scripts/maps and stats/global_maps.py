"""Road network risks and adaptation maps
"""
import os
import sys
from collections import OrderedDict
import pandas as pd
import geopandas as gpd
import numpy as np
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from map_plotting_utils import *
from tqdm import tqdm
tqdm.pandas()

def select_nodes(x,flow_column,threshold_ton_flows):
    if x["infra"] == "port":
        return 1
    # elif (x["infra"] in ["station","stop","road"]) and (x["degree"] > 2) and (x[flow_column] > threshold_ton_flows):
    #     return 1
    else:
        return 0

def remove_nodes_and_edges(flow_df,nodes_df,data_path,output_path,year,mineral_class):
    flow_df = flow_df[~flow_df.geometry.isna()]
    flow_crs = flow_df.crs 
    # port_routes = gpd.read_file(
    #                 os.path.join(data_path,
    #                     "infrastructure",
    #                     "global_maritime_network.gpkg"),
    #                 layer="edges")
    # flow_df = pd.merge(flow_df,port_routes[["id","distance","length"]]).fillna(0)
    # flow_df = flow_df[(flow_df["distance"]<10000) & (flow_df["length"] < 350)]
    flow_df = flow_df[flow_df["id"] != "maritimeroute_6700"]
    # flow_df = gpd.GeoDataFrame(flow_df,geometry="geometry",crs=flow_crs)
    od_ports_df = pd.read_csv(os.path.join(
                            output_path,
                            "flow_mapping",
                            f"mining_city_node_level_ods_{year}.csv"))
    od_ports_df = od_ports_df[od_ports_df["reference_mineral"] == mineral_class]
    od_ports = [p.split("_")[0] for p in list(set(od_ports_df["destination_id"].values.tolist())) if "port" in p]
    del od_ports_df

    port_commodities_df = pd.read_csv(os.path.join(data_path,
                            "port_statistics",
                            "port_known_commodities_traded.csv"))
    export_ports_africa = list(set(port_commodities_df[
                            port_commodities_df[f"{mineral_class}_export_binary"] == 1
                            ]["id"].values.tolist()))
    od_ports += export_ports_africa
    del port_commodities_df, export_ports_africa

    flow_df_all_ids = list(set(flow_df["from_id"].values.tolist() + flow_df["to_id"].values.tolist()))
    flow_df_port_ids = [p for p in flow_df_all_ids if "port" in p]
    flow_df_exclude_port_ids = [p for p in flow_df_port_ids if p not in od_ports]
    del flow_df_all_ids, flow_df_port_ids, od_ports

    flow_df = flow_df[~(
                        (
                            flow_df.from_id.isin(flow_df_exclude_port_ids)
                        ) | (
                            flow_df.to_id.isin(flow_df_exclude_port_ids)
                            )
                    )]
    if len(nodes_df.index) > 0:
        nodes_df = nodes_df[~nodes_df["id"].isin(flow_df_exclude_port_ids)]

    return flow_df,nodes_df

def main(config):
    data_path = config['paths']['data']
    output_path = config['paths']['results']
    figure_path = config['paths']['figures']

    figures = os.path.join(figure_path)
    ccg_countries = pd.read_csv(os.path.join(data_path,"admin_boundaries","ccg_country_codes.csv"))
    ccg_isos = ccg_countries[ccg_countries["ccg_country"] == 1]["iso_3digit_alpha"].values.tolist()
    reference_minerals = ["copper","cobalt","manganese","lithium","graphite","nickel"]
    reference_mineral_colors = ["#cc4c02","#3690c0","#88419d","#d7301f","#252525","#737373"]
    plot_mine_sites = False
    if plot_mine_sites is True:
        mine_sites_df = gpd.read_file(os.path.join(data_path,
                                        "Minerals",
                                        "copper_mines_tons_refined_unrefined.gpkg"))
        mine_sites_df["geometry"] = mine_sites_df.geometry.centroid
        mine_sites_df["refining_type"] = np.where(mine_sites_df["process_binary"] == 0,"Unrefined","Refined")
        output_column = "mine_output_approx_copper"
        values_range = mine_sites_df[output_column].values.tolist()
        ax_proj = get_projection(epsg=4326)
        fig, ax_plots = plt.subplots(1,1,
                        subplot_kw={'projection': ax_proj},
                        figsize=(12,12),
                        dpi=500)
        # ax_plots = ax_plots.flatten()
        ax = plot_africa_basemap(ax_plots)
        ax = point_map_plotting_colors_width(ax,mine_sites_df,
                                    output_column,
                                    values_range,
                                    point_classify_column="refining_type",
                                    point_categories=["Unrefined","Refined"],
                                    point_colors=["#e31a1c","#41ae76"],
                                    point_labels=[s.upper() for s in ["Unrefined","Refined"]],
                                    point_zorder=[6,7,8,9],
                                    point_steps=8,
                                    width_step = 40.0,
                                    interpolation = 'fisher-jenks',
                                    legend_label="Annual output (tons)",
                                    legend_size=16,
                                    legend_weight=2.0,
                                    no_value_label="No output",
                                    )
        plt.tight_layout()
        save_fig(os.path.join(figures,"ccg_copper_outputs.png"))
        plt.close()

    plot_mine_sites = False
    if plot_mine_sites is True:
        mine_id_col = "id"
        mines_df = gpd.read_file(
                        os.path.join(
                            data_path,
                            "minerals",
                            "ccg_mines_est_production.gpkg"))
        mines_crs = mines_df.crs
        mines_df["geometry"] = mines_df.geometry.centroid
        mines_df = gpd.GeoDataFrame(mines_df,geometry="geometry",crs=mines_crs)
        all_mines = []
        if mine_id_col not in mines_df.columns.values.tolist():
            mines_df[mine_id_col] = mines_df.index.values.tolist()
            mines_df[mine_id_col] = mines_df.progress_apply(lambda x:f"mine_{x[mine_id_col]}",axis=1)
        for reference_mineral in reference_minerals:
            if f"{reference_mineral}_processed_ton" not in mines_df.columns.values.tolist():
                mines_df[f"{reference_mineral}_processed_ton"] = 0
            if f"{reference_mineral}_unprocessed_ton" not in mines_df.columns.values.tolist():
                mines_df[f"{reference_mineral}_unprocessed_ton"] = 0

            mines_df[f"{reference_mineral}_tons"] = mines_df[f"{reference_mineral}_processed_ton"] + mines_df[f"{reference_mineral}_unprocessed_ton"]
            mines_df["reference_mineral"] = reference_mineral
        
            all_mines.append(mines_df[mines_df[f"{reference_mineral}_tons"]>0])

        all_mines = gpd.GeoDataFrame(
                            pd.concat(all_mines,axis=0,ignore_index=True).fillna(0),
                            geometry="geometry",crs=mines_crs)
        all_mines["total_tons"
        ] = 1.0e-3*all_mines[[f"{rf}_tons" for rf in reference_minerals]].sum(axis=1) 
        
        values_range = all_mines["total_tons"].values.tolist()
        ax_proj = get_projection(epsg=4326)
        fig, ax_plots = plt.subplots(1,1,
                        subplot_kw={'projection': ax_proj},
                        figsize=(12,12),
                        dpi=500)
        # ax_plots = ax_plots.flatten()
        ax = plot_africa_basemap(ax_plots)
        ax = point_map_plotting_colors_width(ax,all_mines,
                                    "total_tons",
                                    values_range,
                                    point_classify_column="reference_mineral",
                                    point_categories=reference_minerals,
                                    point_colors=reference_mineral_colors,
                                    point_labels=[s.upper() for s in reference_minerals],
                                    point_zorder=[6,6,8,9,10,11],
                                    point_steps=8,
                                    width_step = 60.0,
                                    interpolation = 'fisher-jenks',
                                    legend_label="Annual output ('000 tons)",
                                    legend_size=16,
                                    legend_weight=2.0,
                                    no_value_label="No output",
                                    no_value_color="#ffffff"
                                    )
        plt.tight_layout()
        save_fig(os.path.join(figures,"ccg_mineral_outputs.png"))
        plt.close()

    plot_mine_sites = False
    if plot_mine_sites is True:
        s_and_p_mines = gpd.read_file(os.path.join(
                        data_path,
                        "Minerals",
                        "s_and_p_mines.gpkg"))
        mineral = "Copper"
        s_and_p_mines["refining_type"] = np.where(s_and_p_mines["PROCESSING_METHODS"].isna(),"Unrefined","Refined")
        s_and_p_mines["copper_mine_binary"] = s_and_p_mines.progress_apply(
                                        lambda x: 1 if mineral.lower() in x["COMMODITIES_LIST"].lower() else 0,axis=1)
        # s_and_p_mines[["COMMODITIES_LIST","copper_mine_binary"]].to_csv("test.csv")
        commodity_column = "COMMODITY_PRODUCTION_TONNE_BY_PERIOD"
        years = [2022,2030,2040]

        for year in years:
            output_column = f"{commodity_column}_{year}_{mineral}"
            # mine_sites_df = s_and_p_mines[s_and_p_mines[output_column] > 0] 
            mine_sites_df = s_and_p_mines[s_and_p_mines["copper_mine_binary"] == 1] 
            mine_sites_df[output_column] = mine_sites_df[output_column].fillna(0)
            values_range = mine_sites_df[output_column].values.tolist()
            ax_proj = get_projection(epsg=4326)
            fig, ax_plots = plt.subplots(1,1,
                            subplot_kw={'projection': ax_proj},
                            figsize=(12,12),
                            dpi=500)
            ax = plot_africa_basemap(ax_plots)
            ax = point_map_plotting_colors_width(ax,mine_sites_df,
                                        output_column,
                                        values_range,
                                        point_classify_column="refining_type",
                                        point_categories=["Unrefined","Refined"],
                                        point_colors=["#e31a1c","#41ae76"],
                                        point_labels=[s.upper() for s in ["Unrefined","Refined"]],
                                        point_zorder=[6,7,8,9],
                                        point_steps=8,
                                        width_step = 40.0,
                                        interpolation = 'fisher-jenks',
                                        legend_label="Annual output (tons)",
                                        legend_size=16,
                                        legend_weight=2.0,
                                        no_value_label="No output",
                                        )
            plt.tight_layout()
            save_fig(os.path.join(figures,f"s_and_p_{mineral}_{year}_outputs.png"))
            plt.close()

    plot_flows = False
    if plot_flows is True:
        years = [2021,2030]
        years = [2022]
        mineral_class = "copper"
        for year in years:
            flow_df = gpd.read_file(os.path.join(output_path,
                                            "flow_mapping",
                                            f"edges_flows_{year}.gpkg"),
                                            layer=mineral_class)
            flow_df,_ = remove_nodes_and_edges(flow_df,
                                            pd.DataFrame(),
                                            data_path,
                                            output_path,
                                            year,
                                            mineral_class)

            # print (flow_df.columns.values.tolist())
            # output_columns = [f"{mineral_class}_mine_output_tons",
            #                     f"{mineral_class}_refined_mine_output_tons",
            #                     f"{mineral_class}_unrefined_mine_output_tons"]
            # output_types = ["total","refined","unrefined"]
            # output_colors = ['#7f0000',"#41ae76","#e31a1c"]
            output_columns = [f"{mineral_class}_final_stage_production_tons"]
            output_types = ["total"]
            output_colors = ["#cc4c02"]
            for idx,(oc,ot,ocl) in enumerate(zip(output_columns,output_types,output_colors)):
                if oc in flow_df.columns.values.tolist(): 
                    values_range = flow_df[oc].values.tolist()
                    if max(values_range) > 0:
                        ax_proj = get_projection(epsg=4326)
                        fig, ax_plots = plt.subplots(1,1,
                                        subplot_kw={'projection': ax_proj},
                                        figsize=(12,6),
                                        dpi=500)
                        # ax_plots = ax_plots.flatten()
                        ax = plot_global_basemap(ax_plots)
                        ax = line_map_plotting_colors_width(ax,flow_df,oc,
                                            1.0e3,f"{ot.title()} Annual output ('000 tons)","flows",
                                            line_colors = 8*[ocl],
                                            no_value_color = '#969696',
                                            line_steps = 8,
                                            width_step = 0.08,
                                            interpolation='fisher-jenks')
                        plt.tight_layout()
                        save_fig(os.path.join(figures,f"ccg_{mineral_class}_{ot}_flows_{year}.png"))
                        plt.close()

    plot_flows = False
    if plot_flows is True:
        years = [2021,2030]
        years = [2022]
        mineral_class = "copper"
        for year in years:
            flow_df = gpd.read_file(os.path.join(output_path,
                                            "flow_mapping",
                                            f"{mineral_class}_flows_{year}.gpkg"),
                                            layer="edges")
            nodes_df = gpd.read_file(os.path.join(output_path,
                                        "flow_mapping",
                                        f"{mineral_class}_flows_{year}.gpkg"),
                                        layer="nodes")
            nodes_df = nodes_df[nodes_df["iso3"].isin(ccg_isos)]
            flow_df,nodes_df = remove_nodes_and_edges(flow_df,nodes_df,
                                        data_path,output_path,year,mineral_class)

            # print (flow_df.columns.values.tolist())
            output_columns = [f"{mineral_class}_mine_output_tons",
                                f"{mineral_class}_refined_mine_output_tons",
                                f"{mineral_class}_unrefined_mine_output_tons"]
            output_types = ["total","refined","unrefined"]
            output_colors = ['#7f0000',"#41ae76","#e31a1c"]
            for idx,(oc,ot,ocl) in enumerate(zip(output_columns,output_types,output_colors)):
                if oc in flow_df.columns.values.tolist(): 
                    values_range = flow_df[oc].values.tolist()
                    if max(values_range) > 0:
                        threshold_ton_flows = nodes_df[oc].quantile(0.95)

                        nodes_df["select_nodes_binary"] = nodes_df.progress_apply(
                                                lambda x:select_nodes(x,oc,threshold_ton_flows),
                                                axis=1)
                        ax_proj = get_projection(epsg=4326)
                        fig, ax_plots = plt.subplots(1,1,
                                        subplot_kw={'projection': ax_proj},
                                        figsize=(12,12),
                                        dpi=500)
                        ax = plot_africa_basemap(ax_plots)
                        ax = line_map_plotting_colors_width(ax,flow_df,oc,
                                            1.0,f"{ot.title()} Annual output (tons)","flows",
                                            line_colors = 8*[ocl],
                                            no_value_color = '#969696',
                                            line_steps = 8,
                                            width_step = 0.08,
                                            interpolation='fisher-jenks')
                        n_df = nodes_df[nodes_df["select_nodes_binary"] == 1]
                        n_cls = ["sea","rail","road"]
                        print (n_df)
                        ax = point_map_plotting_colors_width(ax,n_df,
                                                oc,
                                                n_df[oc].values.tolist(),
                                                point_classify_column="mode",
                                                point_categories=n_cls,
                                                point_colors=["#1f78b4","#00441b","#993404"],
                                                point_labels=[s.upper() for s in n_cls],
                                                point_zorder=[20,21,22,23],
                                                point_steps=8,
                                                width_step = 40.0,
                                                interpolation = 'fisher-jenks',
                                                legend_label="Annual output (tons)",
                                                legend_size=16,
                                                legend_weight=2.0,
                                                no_value_label="No output",
                                                )
                        plt.tight_layout()
                        save_fig(os.path.join(figures,
                                    f"ccg_{mineral_class}_{ot}_africa_node_edge_flows_{year}.png"))
                        plt.close()
    plot_flows = True
    if plot_flows is True:
        years = [2021,2030]
        years = [2022]
        mineral_class = "copper"
        for year in years:
            flow_df = gpd.read_file(os.path.join(output_path,
                                            "flow_mapping",
                                            f"edges_flows_{year}.gpkg"),
                                            layer=mineral_class)
            nodes_df = gpd.read_file(os.path.join(output_path,
                                        "flow_mapping",
                                        f"nodes_flows_{year}.gpkg"),
                                        layer=mineral_class)
            nodes_df = nodes_df[nodes_df["iso3"].isin(ccg_isos)]
            flow_df,nodes_df = remove_nodes_and_edges(flow_df,nodes_df,
                                        data_path,output_path,year,mineral_class)

            # print (flow_df.columns.values.tolist())
            # output_columns = [f"{mineral_class}_mine_output_tons",
            #                     f"{mineral_class}_refined_mine_output_tons",
            #                     f"{mineral_class}_unrefined_mine_output_tons"]
            # output_types = ["total","refined","unrefined"]
            # output_colors = ['#7f0000',"#41ae76","#e31a1c"]
            output_columns = [f"{mineral_class}_final_stage_production_tons"]
            output_types = ["total"]
            output_colors = ["#cc4c02"]
            for idx,(oc,ot,ocl) in enumerate(zip(output_columns,output_types,output_colors)):
                if oc in flow_df.columns.values.tolist():

                    values_range = flow_df[oc].values.tolist()
                    if max(values_range) > 0:
                        threshold_ton_flows = nodes_df[oc].quantile(0.95)

                        nodes_df["select_nodes_binary"] = nodes_df.progress_apply(
                                                lambda x:select_nodes(x,oc,threshold_ton_flows),
                                                axis=1)
                        ax_proj = get_projection(epsg=4326)
                        fig, ax_plots = plt.subplots(1,1,
                                        subplot_kw={'projection': ax_proj},
                                        figsize=(12,12),
                                        dpi=500)
                        ax = plot_africa_basemap(ax_plots)
                        ax = line_map_plotting_colors_width(ax,flow_df,oc,
                                            1.0e3,f"{ot.title()} Annual output ('000 tons)","flows",
                                            line_colors = 8*[ocl],
                                            no_value_color = '#969696',
                                            line_steps = 8,
                                            width_step = 0.08,
                                            interpolation='fisher-jenks')
                        n_df = nodes_df[nodes_df["select_nodes_binary"] == 1]
                        n_df[oc] = 1e-3*n_df[oc]
                        n_cls = ["sea","rail","road"]
                        n_cls = ["sea"]
                        print (n_df)
                        ax = point_map_plotting_colors_width(ax,n_df,
                                                oc,
                                                n_df[oc].values.tolist(),
                                                point_classify_column="mode",
                                                point_categories=n_cls,
                                                point_colors=["#1f78b4","#00441b","#993404"],
                                                point_labels=[s.upper() for s in n_cls],
                                                point_zorder=[20,21,22,23],
                                                point_steps=8,
                                                width_step = 40.0,
                                                interpolation = 'fisher-jenks',
                                                legend_label="Annual output ('000 tons)",
                                                legend_size=16,
                                                legend_weight=2.0,
                                                no_value_label="No output",
                                                )
                        plt.tight_layout()
                        save_fig(os.path.join(figures,
                                    f"ccg_{mineral_class}_{ot}_africa_node_edge_flows_{year}.png"))
                        plt.close()
    # if plot_flows is True:
    #     flow_df = gpd.read_file(os.path.join(output_path,
    #                                     "flow_mapping",
    #                                     "copper_flows.gpkg"),
    #                                     layer="edges")
    #     flow_df = flow_df[~flow_df.geometry.isna()]
    #     nodes_df = gpd.read_file(os.path.join(output_path,
    #                                     "flow_mapping",
    #                                     "copper_flows.gpkg"),
    #                                     layer="nodes")
    #     nodes_df = nodes_df[nodes_df["iso3"].isin(ccg_isos)]
    #     # print (flow_df.columns.values.tolist())
    #     output_columns = ["copper_mine_output_tons",
    #                         "copper_refined_mine_output_tons",
    #                         "copper_unrefined_mine_output_tons"]
    #     output_types = ["total","refined","unrefined"]
    #     output_colors = ['#7f0000',"#41ae76","#e31a1c"]
    #     for idx,(oc,ot,ocl) in enumerate(zip(output_columns,output_types,output_colors)): 
    #         values_range = flow_df[oc].values.tolist()
    #         threshold_ton_flows = nodes_df[oc].quantile(0.95)

    #         nodes_df["select_nodes_binary"] = nodes_df.progress_apply(
    #                                 lambda x:select_nodes(x,oc,threshold_ton_flows),
    #                                 axis=1)
    #         ax_proj = get_projection(epsg=4326)
    #         fig, ax_plots = plt.subplots(1,1,
    #                         subplot_kw={'projection': ax_proj},
    #                         figsize=(12,12),
    #                         dpi=500)
    #         # ax_plots = ax_plots.flatten()
    #         # ax = plot_global_basemap(ax_plots)
    #         ax = plot_africa_basemap(ax_plots)
    #         ax = line_map_plotting_colors_width(ax,flow_df,oc,
    #                             1.0,f"{ot.title()} Annual output (tons)","flows",
    #                             line_colors = 8*[ocl],
    #                             no_value_color = '#969696',
    #                             line_steps = 8,
    #                             width_step = 0.08,
    #                             interpolation='fisher-jenks')
    #         n_df = nodes_df[nodes_df["select_nodes_binary"] == 1]
    #         n_cls = ["sea","rail","road"]
    #         print (n_df)
    #         ax = point_map_plotting_colors_width(ax,n_df,
    #                                 oc,
    #                                 n_df[oc].values.tolist(),
    #                                 point_classify_column="mode",
    #                                 point_categories=n_cls,
    #                                 point_colors=["#1f78b4","#00441b","#993404"],
    #                                 point_labels=[s.upper() for s in n_cls],
    #                                 point_zorder=[20,21,22,23],
    #                                 point_steps=8,
    #                                 width_step = 40.0,
    #                                 interpolation = 'fisher-jenks',
    #                                 legend_label="Annual output (tons)",
    #                                 legend_size=16,
    #                                 legend_weight=2.0,
    #                                 no_value_label="No output",
    #                                 )
    #         plt.tight_layout()
    #         save_fig(os.path.join(figures,f"ccg_copper_{ot}_node_edge_flows.png"))
    #         plt.close()

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
