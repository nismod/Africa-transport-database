import os

import click

"""Road network risks and adaptation maps"""

from functools import partial

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cartopy.mpl.geoaxes import GeoAxes
from matplotlib.axes import Axes
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    line_map_plotting_colors_width,
    plot_africa_basemap,
    point_map_plotting_colors_width,
    save_fig,
)

GeoAxes._pcolormesh_patched = Axes.pcolormesh

tqdm.pandas()


def select_nodes(x, flow_column, threshold_ton_flows):
    if x["infra"] == "port":
        return 1
    else:
        return 0


def remove_nodes_and_edges(
    flow_df, nodes_df, od_ports_file, port_commodities_file, mineral_class
):
    flow_df = flow_df[~flow_df.geometry.isna()]
    flow_df = flow_df[flow_df["id"] != "maritimeroute_6700"]
    od_ports_df = pd.read_csv(od_ports_file)
    od_ports_df = od_ports_df[od_ports_df["reference_mineral"] == mineral_class]
    od_ports = [
        p.split("_")[0]
        for p in list(set(od_ports_df["destination_id"].values.tolist()))
        if "port" in p
    ]
    del od_ports_df

    port_commodities_df = pd.read_csv(port_commodities_file)
    export_ports_africa = list(
        set(
            port_commodities_df[
                port_commodities_df[f"{mineral_class}_export_binary"] == 1
            ]["id"].values.tolist()
        )
    )
    od_ports += export_ports_africa
    del port_commodities_df, export_ports_africa

    flow_df_all_ids = list(
        set(flow_df["from_id"].values.tolist() + flow_df["to_id"].values.tolist())
    )
    flow_df_port_ids = [p for p in flow_df_all_ids if "port" in p]
    flow_df_exclude_port_ids = [p for p in flow_df_port_ids if p not in od_ports]
    del flow_df_all_ids, flow_df_port_ids, od_ports

    flow_df = flow_df[
        ~(
            (flow_df.from_id.isin(flow_df_exclude_port_ids))
            | (flow_df.to_id.isin(flow_df_exclude_port_ids))
        )
    ]
    if len(nodes_df.index) > 0:
        nodes_df = nodes_df[~nodes_df["id"].isin(flow_df_exclude_port_ids)]

    return flow_df, nodes_df


@click.command()
@click.option("--ccg-countries", required=True, type=click.Path(exists=True))
@click.option("--railways", required=True, type=click.Path(exists=True))
@click.option("--edge-flows", required=True, type=click.Path(exists=True))
@click.option("--node-flows", required=True, type=click.Path(exists=True))
@click.option("--od-ports", required=True, type=click.Path(exists=True))
@click.option("--port-commodities", required=True, type=click.Path(exists=True))
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--output-railway-status", required=True, type=click.Path())
@click.option("--output-dir", required=True, type=click.Path())
def main(
    ccg_countries,
    railways,
    edge_flows,
    node_flows,
    od_ports,
    port_commodities,
    countries,
    lakes,
    output_railway_status,
    output_dir,
):
    """Map railway status, then copper node and edge flows"""
    ccg_countries = pd.read_csv(ccg_countries)
    ccg_isos = ccg_countries[ccg_countries["ccg_country"] == 1][
        "iso_3digit_alpha"
    ].values.tolist()

    # plot railways
    plot_mine_sites = True
    if plot_mine_sites is True:
        mine_sites_df = gpd.read_file(railways)
        mine_sites_df["geometry"] = mine_sites_df.geometry.centroid
        mine_sites_df["status"] = np.where(
            mine_sites_df["status"] == 0, "proposed", "abandoned"
        )
        output_column = "status"
        values_range = mine_sites_df[output_column].values.tolist()
        ax_proj = get_projection(epsg=4326)
        _fig, ax_plots = plt.subplots(
            1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
        )

        ax = plot_africa_basemap(ax_plots, countries, lakes, ccg_countries)
        ax = point_map_plotting_colors_width(
            ax,
            mine_sites_df,
            output_column,
            values_range,
            point_classify_column="status",
            point_categories=["Unrefined", "Refined"],
            point_colors=["#e31a1c", "#41ae76"],
            point_labels=[s.upper() for s in ["Proposed", "Abandoned"]],
            point_zorder=[6, 7, 8, 9],
            point_steps=8,
            width_step=40.0,
            interpolation="fisher-jenks",
            legend_size=16,
            legend_weight=2.0,
            no_value_label="No output",
        )
        plt.tight_layout()
        save_fig(output_railway_status)
        plt.close()

    plot_flows = True
    if plot_flows is True:
        years = [2021, 2030]
        years = [2022]
        mineral_class = "copper"
        for year in years:
            flow_df = gpd.read_file(
                edge_flows,
                layer=mineral_class,
            )
            nodes_df = gpd.read_file(
                node_flows,
                layer=mineral_class,
            )
            nodes_df = nodes_df[nodes_df["iso3"].isin(ccg_isos)]
            flow_df, nodes_df = remove_nodes_and_edges(
                flow_df, nodes_df, od_ports, port_commodities, mineral_class
            )

            output_columns = [f"{mineral_class}_final_stage_production_tons"]
            output_types = ["total"]
            output_colors = ["#cc4c02"]
            for idx, (oc, ot, ocl) in enumerate(
                zip(output_columns, output_types, output_colors)
            ):
                if oc in flow_df.columns.values.tolist():
                    values_range = flow_df[oc].values.tolist()
                    if max(values_range) > 0:
                        threshold_ton_flows = nodes_df[oc].quantile(0.95)

                        nodes_df["select_nodes_binary"] = nodes_df.progress_apply(
                            partial(select_nodes, oc, threshold_ton_flows), axis=1
                        )
                        ax_proj = get_projection(epsg=4326)
                        _fig, ax_plots = plt.subplots(
                            1,
                            1,
                            subplot_kw={"projection": ax_proj},
                            figsize=(12, 12),
                            dpi=500,
                        )
                        ax = plot_africa_basemap(
                            ax_plots, countries, lakes, ccg_countries
                        )
                        ax = line_map_plotting_colors_width(
                            ax,
                            flow_df,
                            oc,
                            1.0e3,
                            f"{ot.title()} Annual output ('000 tons)",
                            "flows",
                            line_colors=8 * [ocl],
                            no_value_color="#969696",
                            line_steps=8,
                            width_step=0.08,
                            interpolation="fisher-jenks",
                        )
                        n_df = nodes_df[nodes_df["select_nodes_binary"] == 1]
                        n_df[oc] = 1e-3 * n_df[oc]
                        n_cls = ["sea", "rail", "road"]
                        n_cls = ["sea"]
                        print(n_df)
                        ax = point_map_plotting_colors_width(
                            ax,
                            n_df,
                            oc,
                            n_df[oc].values.tolist(),
                            point_classify_column="mode",
                            point_categories=n_cls,
                            point_colors=["#1f78b4", "#00441b", "#993404"],
                            point_labels=[s.upper() for s in n_cls],
                            point_zorder=[20, 21, 22, 23],
                            point_steps=8,
                            width_step=40.0,
                            interpolation="fisher-jenks",
                            legend_label="Annual output ('000 tons)",
                            legend_size=16,
                            legend_weight=2.0,
                            no_value_label="No output",
                        )
                        plt.tight_layout()
                        save_fig(
                            os.path.join(
                                output_dir,
                                f"ccg_{mineral_class}_{ot}_africa_node_edge_flows_{year}.png",
                            )
                        )
                        plt.close()


if __name__ == "__main__":
    main()
