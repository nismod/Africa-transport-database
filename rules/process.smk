"""Build the transport database from the incoming data.

One rule per script under ``scripts/preprocess``, in roughly the order they are
meant to run: OpenStreetMap extracts, then each mode (maritime, rail, road, air,
inland waterways), then the multi-modal links that join them, then the
finishing passes that add derived columns and data-source citations.

The preprocessing scripts that match against reference datasets rather than
build a layer live in ``validate.smk`` instead.
"""


# ---------------------------------------------------------------------------
# OpenStreetMap extracts
# ---------------------------------------------------------------------------


rule osm_extract_v2:
    """Extract airport terminal footprints from the Africa OSM PBF extract.
    """
    input:
        script=f"{PREPROCESS}/osm_extract_v2.py",
        pbf=f"{INCOMING}/osm/africa-260219.osm.pbf",
    output:
        parquet=f"{INCOMING}/infrastructure/africa_osm_airports_terminals.parquet",
    shell:
        """
        python {input.script}
        """


rule extract_suez:
    """Turn the Suez Canal OSM waterways into a topological network."""
    input:
        script=f"{PREPROCESS}/extract_suez.py",
        waterways=f"{INCOMING}/egypt-latest-free.shp/gis_osm_waterways_free_1.shp",
        suez_ids=f"{INCOMING}/egypt-latest-free.shp/suez_canal_ids.csv",
        global_ports=f"{INCOMING}/Global port supply-chains/Network/nodes_maritime.gpkg",
    output:
        # Layers "nodes" and "edges" are written into the same GeoPackage.
        network=f"{INCOMING}/egypt-latest-free.shp/suez_canal_network.gpkg",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# maritime ports
# ---------------------------------------------------------------------------


rule ports_data_cleaning:
    """Match USGS, corridor and global port datasets into the maritime network.
    """
    input:
        script=f"{PREPROCESS}/ports_data_cleaning.py",
        global_ports=f"{INCOMING}/Global port supply-chains/Network/nodes_maritime.gpkg",
        usgs_ports=USGS_PORTS,
        corridor_db=CORRIDOR_DB,
        africa_adm0=AFRICA_ADM0,
        maritime_edges=f"{INCOMING}/ports/edges_maritime_corrected.gpkg",
        suez_network=f"{INCOMING}/suez_canal_network.gpkg",
    output:
        global_network=f"{DATA}/infrastructure/global_maritime_network.gpkg",
        africa_network=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
    shell:
        """
        python {input.script}
        """


rule ports_new_merge:
    """Merge the 2025 IMF PortWatch port statistics into the maritime network."""
    input:
        script=f"{PREPROCESS}/ports_new_merge.py",
        global_network=f"{DATA}/infrastructure/global_maritime_network.gpkg",
        ports_2025=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/Ports.shp",
        port_calls=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/port_calls_average_2019-2024.csv",
        port_capacity=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/port_capacity_called_average_2019-2024.csv",
        port_turnaround=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/port_turn_around_time_average_2019-2024.csv",
    output:
        global_network=f"{DATA}/infrastructure/global_maritime_network_PROVA_NEW1.gpkg",
        africa_network=f"{DATA}/infrastructure/africa_maritime_network_PROVA_NEW1.gpkg",
    shell:
        """
        python {input.script}
        """


rule merged_points_v2:
    """Merge USGS, global and corridor port points, add ISO3 codes."""
    input:
        script=f"{PREPROCESS}/Merged points-v2.py",
        usgs_ports=USGS_PORTS,
        global_ports=f"{INCOMING}/ports/nodes_maritime.gpkg",
        corridor_db=CORRIDOR_DB,
        world_boundaries=NE_110M_COUNTRIES,
    output:
        merged_gpkg=f"{DATA}/merged_with_iso2.gpkg",
        merged_csv=f"{DATA}/merged_with_iso2.csv",
        non_intersected_gpkg=f"{DATA}/non_intersected_from_merged.gpkg",
        non_intersected_csv=f"{DATA}/non_intersected_from_merged.csv",
    shell:
        """
        python {input.script}
        """


rule sample_code_from_ports_africa:
    """Attach the non-intersected port points to the Africa port network."""
    input:
        script=f"{PREPROCESS}/sample_code_from_ports_africa.py",
        africa_ports=f"{INCOMING}/ports/africa_ports.gpkg",
        non_intersected=f"{DATA}/non_intersected_from_merged.gpkg",
    output:
        modified=f"{DATA}/africa_ports_modified.gpkg",
    shell:
        """
        python {input.script}
        """


rule add_id:
    """Fill in node_id, name and ISO3 for the merged port nodes."""
    input:
        script=f"{PREPROCESS}/Add ID.py",
        non_intersected=f"{DATA}/non_intersected_from_merged.gpkg",
        modified_ports=f"{DATA}/africa_ports_modified.gpkg",
        world_boundaries=NE_110M_COUNTRIES,
        merged_csv=f"{DATA}/merged_with_iso2.csv",
    output:
        output_gpkg=f"{DATA}/output.gpkg",
    shell:
        """
        python {input.script}
        """


rule economic:
    """Join port weight, value and utilisation statistics to the merged ports.
    """
    input:
        script=f"{PREPROCESS}/economic.py",
        usgs_ports=USGS_PORTS,
        ports_weight=f"{INCOMING}/Global port supply-chains/Port_statistics/port_locations_weight.csv",
        ports_value=f"{INCOMING}/Global port supply-chains/Port_statistics/port_locations_value.csv",
        ports_utilization=f"{INCOMING}/Global port supply-chains/Port_statistics/port_utilization.csv",
        merged_csv=f"{DATA}/merged_with_iso2.csv",
    output:
        weightvalues=f"{DATA}/ports_weightvalues.csv",
        merged2=f"{DATA}/merged2.csv",
        results=f"{DATA}/economic results2.csv",
        missing_coords=f"{DATA}/missing_coords.csv",
    shell:
        """
        python {input.script}
        """


rule port_cargo_attributes:
    """Derive traded commodities and annual capacities per port."""
    input:
        script=f"{PREPROCESS}/port_cargo_attributes.py",
        port_matches=f"{INCOMING}/ports/all_ports_matches.xlsx",
        corridor_db=CORRIDOR_DB,
        usgs_ports=USGS_PORTS,
        global_network=f"{DATA}/infrastructure/global_maritime_network.gpkg",
        port_utilisation=f"{DATA}/port_statistics/port_utilization.csv",
    output:
        vessel_capacities=f"{DATA}/port_statistics/port_vessel_types_and_capacities.csv",
        commodities=f"{DATA}/port_statistics/port_known_commodities_traded.csv",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# railways
# ---------------------------------------------------------------------------


rule rail_data_cleaning:
    """Build the Africa railway network from OSM and corridor project data.

    Step one converts each rail project into a per-project GeoPackage inside the
    ``africa_corridor_developments`` folder; step two merges those with the
    Africa rail network.

    Note that step two reads ``guinea_lines.gpkg`` while step one writes the
    same project out as ``conakry-kankan_railway.gpkg``, so that input has to be
    supplied, or perhaps renamed.
    """
    input:
        script=f"{PREPROCESS}/rail_data_cleaning.py",
        africa_adm0=AFRICA_ADM0,
        guinea_rail=f"{INCOMING}/africa_corridor_developments/guinea_rail.shp",
        simandou=f"{INCOMING}/africa_corridor_developments/17D.1.gpkg",
        togo=f"{INCOMING}/africa_corridor_developments/togo_lines.gpkg",
        team=f"{INCOMING}/africa_corridor_developments/Team.gpkg",
        dar_es=f"{INCOMING}/africa_corridor_developments/Dar_es.gpkg",
        eastafrica=f"{INCOMING}/africa_corridor_developments/eastafrica_rail.gpkg",
        kinshasa=f"{INCOMING}/africa_corridor_developments/kinsasha_rail.gpkg",
        tanzania_sgr=f"{INCOMING}/africa_corridor_developments/tanzania_sgr_lines.gpkg",
        guinea_lines=f"{INCOMING}/africa_corridor_developments/guinea_lines.gpkg",
        africa_railways=f"{INCOMING}/africa_rail_network/network_data/africa_railways.gpkg",
        africa_rail_nodes=f"{INCOMING}/africa_rail_network/network_data/africa_rail_nodes.geojson",
    output:
        conakry=f"{INCOMING}/africa_corridor_developments/conakry-kankan_railway.gpkg",
        simandou=f"{INCOMING}/africa_corridor_developments/simandou_railway_project.gpkg",
        togo=f"{INCOMING}/africa_corridor_developments/togo_rail.gpkg",
        ghana_burkina=f"{INCOMING}/africa_corridor_developments/ghana_burkina_faso.gpkg",
        isaka=f"{INCOMING}/africa_corridor_developments/isaka_kigali_gitega_railway.gpkg",
        eastafrica=f"{INCOMING}/africa_corridor_developments/east_africa_railway.gpkg",
        kinshasa=f"{INCOMING}/africa_corridor_developments/kinshasa_ilebo_railway.gpkg",
        tanzania_sgr=f"{INCOMING}/africa_corridor_developments/tanzania_standard_gauge_railway.gpkg",
        standard_gauge=f"{INCOMING}/africa_corridor_developments/standard_gauge_railway.gpkg",
        network=f"{DATA}/infrastructure/africa_railways_network.gpkg",
    shell:
        """
        python {input.script}
        """


rule rails_costs:
    """Estimate capital, O&M and investment costs per railway line."""
    input:
        script=f"{PREPROCESS}/rails_costs.py",
        rail_network=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        costs=f"{INCOMING}/Rail_Costs.xlsx",
    output:
        costs=f"{DATA}/infrastructure/africa_rails_costs.csv",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# roads
# ---------------------------------------------------------------------------


rule road_connectivity:
    """Connect points of interest to the OSM road network (README step 1-5)."""
    input:
        script=f"{PREPROCESS}/road_connectivity.py",
        population=f"{DATA}/admin_boundaries/un_urban_population/un_pop_df.gpkg",
        airports=f"{DATA}/infrastructure/africa_airport_network.gpkg",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        road_edges=f"{INCOMING}/africa_roads/edges_with_topology.gpq",
        road_nodes=f"{INCOMING}/africa_roads/nodes_with_topology.gpq",
    output:
        nodes=f"{DATA}/infrastructure/africa_roads_nodes.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges.geoparquet",
        main_roads=f"{INCOMING}/africa_roads/africa_main_roads.gpkg",
    shell:
        """
        python {input.script}
        """


rule road_corridors_primary_roads:
    """Route the named road corridors over the primary road network."""
    input:
        script=f"{PREPROCESS}/road_corridors_primary_roads.py",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges.geoparquet",
        road_nodes=f"{DATA}/infrastructure/africa_roads_nodes.geoparquet",
        corridors=f"{INCOMING}/road_corridors.xlsx",
    output:
        nodes=f"{DATA}/infrastructure/africa_roads_nodes_withcorridors.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges_withcorridors.geoparquet",
    shell:
        """
        python {input.script}
        """


rule road_corridors_ns_corridor:
    """Route the Lobito corridor over the AGO/COD/ZMB road network.

    Despite the file name, this script reads ``Lobito_corridor.xlsx`` and writes
    the ``PROVA_Lobito_corridor`` layers.
    """
    input:
        script=f"{PREPROCESS}/road_corridors_NS_corridor.py",
        road_edges=f"{INCOMING}/africa_roads/edges_with_topology.geoparquet",
        road_nodes=f"{INCOMING}/africa_roads/nodes_with_topology.geoparquet",
        corridor=f"{INCOMING}/Lobito_corridor.xlsx",
    output:
        nodes=f"{DATA}/infrastructure/africa_roads_nodes_PROVA_Lobito_corridor.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges_PROVA_Lobito_corridor.geoparquet",
    shell:
        """
        python {input.script}
        """


rule road_adjustments:
    """Merge the per-corridor road extracts into the final road network.

    This script also writes the ``nodes`` and ``edges`` layers of

        {DATA}/infrastructure/africa_roads_network.gpkg

    but that file is re-written by ``costs_columns`` and then ``road_processing``,
    so it is declared as the output of ``road_processing`` only - two jobs in one
    workflow may not write the same file.
    """
    input:
        script=f"{PREPROCESS}/RoadAdjustments.py",
        lobito_edges=f"{DATA}/infrastructure/africa_roads_edges_PROVA_Lobito_corridor.geoparquet",
        lobito_nodes=f"{DATA}/infrastructure/africa_roads_nodes_PROVA_Lobito_corridor.geoparquet",
        ta_edges=f"{DATA}/infrastructure/africa_roads_edges_PROVA_TA_corridor.geoparquet",
        ta_nodes=f"{DATA}/infrastructure/africa_roads_nodes_PROVA_TA_corridor.geoparquet",
        tsh_edges=f"{DATA}/infrastructure/africa_roads_edges_PROVA_TSH_corridor.geoparquet",
        tsh_nodes=f"{DATA}/infrastructure/africa_roads_nodes_PROVA_TSH_corridor.geoparquet",
        ns_edges=f"{DATA}/infrastructure/africa_roads_edges_PROVA_NS_corridor.geoparquet",
        ns_nodes=f"{DATA}/infrastructure/africa_roads_nodes_PROVA_NS_corridor.geoparquet",
        mdg_edges=f"{DATA}/infrastructure/africa_roads_edges_PROVA_MDG.geoparquet",
        mdg_nodes=f"{DATA}/infrastructure/africa_roads_nodes_PROVA_MDG.geoparquet",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_withcorridors.geoparquet",
        road_nodes=f"{DATA}/infrastructure/africa_roads_nodes_withcorridors.geoparquet",
    output:
        nodes=f"{DATA}/infrastructure/africa_roads_nodes_FINAL.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
    shell:
        """
        python {input.script}
        """


rule costs_columns:
    """Tidy the road node/edge columns and cap the lane count.

    As well as the GeoPackage declared below, this script rewrites its two
    inputs in place:

        {DATA}/infrastructure/africa_roads_nodes_FINAL.geoparquet
        {DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet

    Those two files are deliberately left out of ``output``. Need to be named
    something different at each stage, order needs confirming.
    """
    input:
        script=f"{PREPROCESS}/costs_columns.py",
        nodes=f"{DATA}/infrastructure/africa_roads_nodes_FINAL.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
    output:
        network=f"{DATA}/infrastructure/africa_roads_network.gpkg",
    shell:
        """
        python {input.script}
        """


rule road_processing:
    """Infer paved status, surface material and asset type for road edges."""
    input:
        script=f"{PREPROCESS}/road_processing.py",
        edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
    output:
        edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL_last.geoparquet",
        network=f"{DATA}/infrastructure/africa_roads_network.gpkg",
    shell:
        """
        python {input.script}
        """


rule corridors_costs:
    """Estimate capital, O&M and investment costs per road corridor."""
    input:
        script=f"{PREPROCESS}/corridors_costs.py",
        road_network=f"{DATA}/infrastructure/africa_roads_network.gpkg",
        costs=f"{INCOMING}/Roads_Costs.xlsx",
    output:
        merged_costs=f"{DATA}/infrastructure/merged_costs_data.csv",
        corridor_costs=f"{DATA}/infrastructure/africa_corridors_costs.csv",
    shell:
        """
        python {input.script}
        """


rule stats_rail_roads:
    """Summarise rail length by status and road length by corridor/surface."""
    input:
        script=f"{PREPROCESS}/stats_rail_roads.py",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        rail_network=f"{DATA}/infrastructure/africa_railways_network.gpkg",
    output:
        rail_stats=f"{DATA}/infrastructure/rail_stats.csv",
        paved_stats=f"{DATA}/infrastructure/paved_stats2.csv",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# airports
# ---------------------------------------------------------------------------


rule airports_data_cleaning:
    """Rebuild airport route geometries and attach origin/destination ISO3."""
    input:
        script=f"{PREPROCESS}/airports_data_cleaning.py",
        airport_network=f"{DATA}/infrastructure/africa_airport_network.gpkg",
    output:
        network=f"{DATA}/infrastructure/africa_airport_network_last.gpkg",
    shell:
        """
        python {input.script}
        """


rule ourairports_data_layer:
    """Filter the OurAirports layer to the airports in the network."""
    input:
        script=f"{PREPROCESS}/ourairports_data_layer.py",
        ourairports=f"{INCOMING}/airports/africa_airports_ourairport.gpkg",
        airport_network=f"{DATA}/infrastructure/africa_airport_network.gpkg",
    output:
        ourairports=f"{DATA}/infrastructure/africa_airport_ourairport_rev.gpkg",
        network=f"{DATA}/infrastructure/africa_airport_network_rev.gpkg",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# inland waterways
# ---------------------------------------------------------------------------


rule inland_waterways_cleaning:
    """Build the inland waterway network from IWW ports, lakes and rivers."""
    input:
        script=f"{PREPROCESS}/inland_waterways_cleaning.py",
        iww_ports=f"{INCOMING}/IWW_ports/africa_IWW_ports.xlsx",
        congo_rivers=f"{INCOMING}/IWW_ports/edges_port_IWW_af.gpkg",
        south_sudan=f"{INCOMING}/IWW_ports/hotosm_ssd_waterways.gpkg",
        africa_adm0=AFRICA_ADM0,
    output:
        network=f"{DATA}/infrastructure/africa_iww_network.gpkg",
    shell:
        """
        python {input.script}
        """


rule africa_inland_waterways:
    """Build the inland waterway network from the OSM rivers extract.

    Three steps in one script: turn the waterways extract into a network, keep
    the large connected rivers and snap the IWW ports onto them, then route
    between the ports and drop the reaches that connect nothing. The two
    intermediate river networks are written back into ``Africa_osm_rivers``
    alongside the extract they come from.

    Steps one and two were switched off in the script with a ``step = False``
    flag - "this step takes a lot of time, so we have set it to false after
    running it once". Snakemake skips the whole rule when its outputs are up to
    date, so the flags are gone and all three steps run.
    """
    input:
        script=f"{PREPROCESS}/africa_inland_waterways.py",
        waterways=f"{INCOMING}/Africa_osm_rivers/OpenStreetMap_Waterways_for_Africa.geoparquet",
        iww_ports=f"{INCOMING}/IWW_ports/africa_IWW_ports.xlsx",
        africa_adm0=AFRICA_ADM0,
    output:
        river_edges=f"{INCOMING}/Africa_osm_rivers/africa_river_edges.geoparquet",
        river_nodes=f"{INCOMING}/Africa_osm_rivers/africa_river_nodes.geoparquet",
        network_edges=f"{INCOMING}/Africa_osm_rivers/africa_network_edges.geoparquet",
        network_nodes=f"{INCOMING}/Africa_osm_rivers/africa_network_nodes.geoparquet",
        network=f"{DATA}/infrastructure/africa_iww_network.gpkg",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# multi-modal links and finishing passes
# ---------------------------------------------------------------------------


rule multi_modal_edges_creation:
    """Create the inter-modal links between sea, IWW, rail, air and road."""
    input:
        script=f"{PREPROCESS}/multi_modal_edges_creation.py",
        airports=f"{DATA}/infrastructure/africa_airport_network.gpkg",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        road_nodes=f"{DATA}/infrastructure/africa_roads_nodes_FINAL.geoparquet",
    output:
        multimodal=f"{DATA}/infrastructure/africa_multimodal_rev.gpkg",
    shell:
        """
        python {input.script}
        """


rule data_checks:
    """Reduce the multi-modal edge layer to the published set of columns.

    The script reads and rewrites

        {DATA}/infrastructure/africa_multimodal.gpkg

    Needs to be named something different as input and output, order needs confirming.
    """
    input:
        script=f"{PREPROCESS}/data_checks.py",
        # multimodal=f"{DATA}/infrastructure/africa_multimodal.gpkg",
    output:
        multimodal=f"{DATA}/infrastructure/africa_multimodal.gpkg",
    shell:
        """
        python {input.script}
        """


rule source_column:
    """Add the data-source citation column to every published network layer."""
    input:
        script=f"{PREPROCESS}/source_column.py",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        airports=f"{DATA}/infrastructure/africa_airport_network_rev.gpkg",
        multimodal=f"{DATA}/infrastructure/africa_multimodal_rev.gpkg",
        roads=f"{DATA}/infrastructure/africa_roads_network.gpkg",
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
    output:
        maritime=f"{DATA}/infrastructure/africa_maritime_network_withsources.gpkg",
        airports=f"{DATA}/infrastructure/africa_airport_network_withsources.gpkg",
        multimodal=f"{DATA}/infrastructure/africa_multimodal_withsources.gpkg",
        roads=f"{DATA}/infrastructure/africa_roads_network_withsources.gpkg",
        railways=f"{DATA}/infrastructure/africa_railways_network_withsources.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network_withsources.gpkg",
    shell:
        """
        python {input.script}
        """
