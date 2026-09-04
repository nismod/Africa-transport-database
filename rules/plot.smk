"""Map and chart the database.

The scripts under ``scripts/plot`` and ``scripts/maps and stats`` that draw the
finished network layers; the ones that chart a comparison against another
dataset are in ``validate.smk`` instead.

Every rule that draws a basemap reads the Natural Earth country and lake layers
through ``aftdb.plot.maps.plot_africa_basemap()`` and friends, so those are
declared as inputs even where the script itself does not name them.
"""


# ---------------------------------------------------------------------------
# maps
# ---------------------------------------------------------------------------


rule plot_africa_basemap:
    """Plot the Africa basemap on its own."""
    input:
        script=f"{PLOT}/africa_maps.py",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/africa_basemap.png",
    shell:
        """
        python {input.script}
        """


rule plot_airports:
    """Map airports sized by total annual seats."""
    input:
        script=f"{PLOT}/africa_maps_airports.py",
        airports=f"{DATA}/infrastructure/africa_airport_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/airports.png",
    shell:
        """
        python {input.script}
        """


rule plot_ports_and_iww:
    """Map maritime ports, inland ports and their routes."""
    input:
        script=f"{PLOT}/africa_maps_ports.py",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/IWW_and_ports.png",
    shell:
        """
        python {input.script}
        """


rule plot_ports_bubble:
    """Map maritime and inland ports as proportional bubbles."""
    input:
        script=f"{PLOT}/africa_maps_ports_bubble.py",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/ports_with_edges_last.png",
    shell:
        """
        python {input.script}
        """


rule plot_rails_gauge:
    """Map the railway network coloured by gauge."""
    input:
        script=f"{PLOT}/africa_maps_rails.py",
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/rail_test_gauge.png",
    shell:
        """
        python {input.script}
        """


rule plot_rails_facilities:
    """Map railway stations by facility type."""
    input:
        script=f"{PLOT}/africa_maps_rails_facilities.py",
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/rail_test_facility.png",
    shell:
        """
        python {input.script}
        """


rule plot_roads_typology:
    """Map the road network coloured by highway typology."""
    input:
        script=f"{PLOT}/africa_maps_roads.py",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/roads_typology2_LAST.png",
    shell:
        """
        python {input.script}
        """


rule plot_roads_corridors:
    """Map the road network coloured by development corridor."""
    input:
        script=f"{PLOT}/africa_maps_roads_corridors.py",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        legend=f"{FIGURES}/roads_corridors_legend_LAST.png",
        figure=f"{FIGURES}/roads_corridors_LAST.png",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------


rule plot_rail_histogram:
    """Stacked bar chart of railway length by country and status."""
    input:
        script=f"{PLOT}/africa_hist_rails.py",
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
    output:
        figure=f"{FIGURES}/rail_hist_cap_withgrid.png",
    shell:
        """
        python {input.script}
        """


rule plot_roads_histogram:
    """Stacked bar chart of road length by corridor and typology."""
    input:
        script=f"{PLOT}/africa_hist_roads.py",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
    output:
        figure=f"{FIGURES}/roads_hist_cap2_grid.png",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# minerals maps, carried over from the transport-critical-minerals workflow
# ---------------------------------------------------------------------------


rule plot_location_maps:
    """Maps of optimised mine and processing locations.

    The mineral usage factor and BACI trade inputs are read by
    ``modify_mineral_usage_factors()`` rather than by ``main()``, so they do not
    appear alongside the other reads in the script.
    """
    input:
        script=f"{PLOT}/location_maps.py",
        ccg_countries=CCG_COUNTRY_CODES,
        stage_mapping=f"{DATA}/mineral_usage_factors/stage_mapping.xlsx",
        aggregated_stages=f"{DATA}/mineral_usage_factors/aggregated_stages.xlsx",
        usage_factors=f"{DATA}/mineral_usage_factors/mineral_usage_factors.xlsx",
        metal_content=f"{DATA}/mineral_usage_factors/metal_content.csv",
        baci_countries=f"{DATA}/baci/ccg_country_codes.csv",
        mine_city_stages=f"{DATA}/baci/mine_city_stages.csv",
        baci_trade=f"{DATA}/baci/baci_ccg_minerals_trade_2022_bgs_corrected.csv",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
        locations=expand(
            f"{RESULTS}/optimised_processing_locations/"
            "combined_node_locations_for_energy_conversion_{scenario}.gpkg",
            scenario=[
                "country_unconstrained",
                "country_constrained",
                "region_unconstrained",
                "region_constrained",
            ],
        ),
    output:
        figures=expand(
            f"{FIGURES}/regional_figures/mine_and_processing_locations/"
            "combined_processing_locations_maps_{name}.png",
            name=[
                "2030_mid_country",
                "2040_mid_country",
                "2030_mid_region",
                "2040_mid_region",
            ],
        ),
    shell:
        """
        python {input.script}
        """


rule plot_mine_ownership_maps:
    """Global maps of mine ownership shares by country.
    """
    input:
        script=f"{PLOT}/mine_ownership_maps.py",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
        centroids=f"{DATA}/admin_boundaries/centroids/countries_iso3_code.csv",
        ownership=f"{RESULTS}/mine_ownership/df_maps_2022.csv",
    output:
        basemap=f"{FIGURES}/mine_ownership/global_basemap.png",
        totals=f"{FIGURES}/mine_ownership/mine_totals.svg",
        by_ownership=f"{FIGURES}/mine_ownership/country_totals_by_ownership.svg",
    shell:
        """
        python {input.script}
        """


rule maps_graphs:
    """Plot the main road network over the Africa basemap.
    """
    input:
        script=f"{MAPS_AND_STATS}/graphs.py",
        ccg_countries=CCG_COUNTRY_CODES,
        main_roads=f"{INCOMING}/africa_roads/africa_main_roads.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/roads_test.png",
    shell:
        """
        python {input.script}
        """


rule maps_graphs_transport:
    """Plot the final road edges by corridor over the Africa basemap.
    """
    input:
        script=f"{MAPS_AND_STATS}/graphs_transport.py",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/roads_test.png",
    shell:
        """
        python {input.script}
        """


rule maps_global_maps:
    """Map copper node and edge flows over the Africa basemap.

    Only the last ``plot_flows`` block is enabled in the script; the disabled
    blocks additionally read ``Minerals/copper_mines_tons_refined_unrefined.gpkg``,
    ``minerals/ccg_mines_est_production.gpkg``, ``Minerals/s_and_p_mines.gpkg``
    and ``flow_mapping/{mineral}_flows_{year}.gpkg``.
    """
    input:
        script=f"{MAPS_AND_STATS}/global_maps.py",
        ccg_countries=CCG_COUNTRY_CODES,
        edge_flows=f"{RESULTS}/flow_mapping/edges_flows_2022.gpkg",
        node_flows=f"{RESULTS}/flow_mapping/nodes_flows_2022.gpkg",
        od_ports=f"{RESULTS}/flow_mapping/mining_city_node_level_ods_2022.csv",
        port_commodities=f"{DATA}/port_statistics/port_known_commodities_traded.csv",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/ccg_copper_total_africa_node_edge_flows_2022.png",
    shell:
        """
        python {input.script}
        """


rule maps_global_maps_transport:
    """Map railway status, then copper node and edge flows.

    NOTE: as in ``global_maps.py``, the disabled blocks read further mineral
    datasets.

    It also writes {FIGURES}/ccg_copper_total_africa_node_edge_flows_2022.png,
    which is declared as the output of ``maps_global_maps`` instead - need to
    decide which script should produce this.
    """
    input:
        script=f"{MAPS_AND_STATS}/global_maps_transport.py",
        ccg_countries=CCG_COUNTRY_CODES,
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        edge_flows=f"{RESULTS}/flow_mapping/edges_flows_2022.gpkg",
        node_flows=f"{RESULTS}/flow_mapping/nodes_flows_2022.gpkg",
        od_ports=f"{RESULTS}/flow_mapping/mining_city_node_level_ods_2022.csv",
        port_commodities=f"{DATA}/port_statistics/port_known_commodities_traded.csv",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        railway_status=f"{FIGURES}/railway_status.png",
    shell:
        """
        python {input.script}
        """
