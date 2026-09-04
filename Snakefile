"""Snakemake workflow for the African Transport Systems Database (AfTS-Db).

This Snakefile wraps every runnable script under ``scripts/`` in a rule. It does
not change any of the Python code: each rule simply runs a script as it is, and
declares the files that script reads (``input``) and writes (``output``).

Paths come from ``config.json`` (copy ``config.template.json`` and edit it), so
the workflow and the scripts resolve exactly the same locations. The scripts
call ``load_config()`` themselves, which reads ``config.json`` relative to the
script file, so the values below and the values a script sees are the same.

Several scripts also use ``config['paths']['results']``, so ``config.json``
needs a ``results`` entry as well (see ``config.template.json``).

Scripts are executed from the repository root with ``PYTHONPATH`` pointing at
the script's own directory, because they import sibling modules
(``utils.py``, ``utils_new.py``, ``map_plotting_utils.py``, ...) as top-level
modules. Relative paths in ``config.json`` are therefore relative to the
repository root.

Library modules with no ``main()`` have no rule of their own; they are declared
as inputs of the rules that import them:

    scripts/preprocess/utils.py
    scripts/preprocess/utils_new.py
    scripts/preprocess/updated_utils.py
    scripts/preprocess/network.py
    scripts/plot/map_plotting_utils.py
    scripts/plot/scalebar.py
    scripts/plot/htb.py
    scripts/maps and stats/utils_new.py
    scripts/maps and stats/map_plotting_utils.py
"""

if not config:

    configfile: "config.json"


PATHS = config["paths"]
INCOMING = PATHS["incoming_data"]
DATA = PATHS["data"]
FIGURES = PATHS["figures"]
# Several scripts read config['paths']['results']; fall back to the data path so
# that the workflow still parses if the key is missing from config.json.
RESULTS = PATHS.get("results", DATA)

PREPROCESS = "scripts/preprocess"
PLOT = "scripts/plot"
MAPS_AND_STATS = "scripts/maps and stats"

# Every rule runs its script the same way.
RUN_SCRIPT = 'PYTHONPATH="$(dirname "{input.script}")" python "{input.script}"'

# Shared library modules, declared as inputs so that editing them re-triggers
# the rules that depend on them.
UTILS = f"{PREPROCESS}/utils.py"
UTILS_NEW = f"{PREPROCESS}/utils_new.py"
PLOT_UTILS = f"{PLOT}/map_plotting_utils.py"
MAPS_UTILS = f"{MAPS_AND_STATS}/map_plotting_utils.py"

# Basemap layers read inside map_plotting_utils.plot_africa_basemap(),
# plot_africa_basemap2(), plot_global_basemap() and plot_ccg_basemap().
BASEMAP_COUNTRIES = f"{DATA}/admin_boundaries/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp"
BASEMAP_LAKES = f"{DATA}/admin_boundaries/ne_10m_lakes/ne_10m_lakes.shp"
CCG_COUNTRY_CODES = f"{DATA}/admin_boundaries/ccg_country_codes.csv"

# Frequently reused source datasets.
AFRICA_ADM0 = (
    f"{INCOMING}/Africa_GIS Supporting Data/a. Africa_GIS Shapefiles/"
    "AFR_Political_ADM0_Boundaries.shp/AFR_Political_ADM0_Boundaries.shp"
)
USGS_PORTS = (
    f"{INCOMING}/Africa_GIS Supporting Data/a. Africa_GIS Shapefiles/"
    "AFR_Infra_Transport_Ports.shp/AFR_Infra_Transport_Ports.shp"
)
CORRIDOR_DB = (
    f"{INCOMING}/africa_corridor_developments/"
    "AfricanDevelopmentCorridorDatabase2022.gpkg"
)
NE_110M_COUNTRIES = f"{INCOMING}/ports/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"


# Some files are written by more than one script, because the scripts were
# written to be run in sequence and each one refines the previous result. These
# ruleorder directives record the intended order - the preferred (left-most)
# rule is the one that writes the file last in the pipeline.
#
# ``costs_columns`` additionally rewrites the FINAL road geoparquets in place, so
# it cannot be wired in as an automatic dependency. Run it explicitly
# (``snakemake costs_columns``) between ``road_adjustments`` and
# ``road_processing``.
ruleorder: road_processing > costs_columns
ruleorder: africa_inland_waterways > inland_waterways_cleaning
ruleorder: maps_graphs_transport > maps_graphs


rule all:
    """Build the published multi-modal network layers."""
    input:
        f"{DATA}/infrastructure/africa_roads_network.gpkg",
        f"{DATA}/infrastructure/africa_railways_network.gpkg",
        f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        f"{DATA}/infrastructure/africa_iww_network.gpkg",
        f"{DATA}/infrastructure/africa_airport_network_last.gpkg",
        f"{DATA}/infrastructure/africa_multimodal_rev.gpkg",


# ---------------------------------------------------------------------------
# scripts/preprocess - OpenStreetMap extracts
# ---------------------------------------------------------------------------

rule osm_extract_v2:
    """Extract airport terminal footprints from the Africa OSM PBF extract.

    NOTE: this script defines its own load_config() that looks for
    ``scripts/config.json`` rather than the repository-root ``config.json``.
    """
    input:
        script=f"{PREPROCESS}/osm_extract_v2.py",
        pbf=f"{INCOMING}/osm/africa-260219.osm.pbf",
    output:
        parquet=f"{INCOMING}/infrastructure/africa_osm_airports_terminals.parquet",
    shell:
        RUN_SCRIPT


rule extract_suez:
    """Turn the Suez Canal OSM waterways into a topological network."""
    input:
        script=f"{PREPROCESS}/extract_suez.py",
        utils=UTILS,
        waterways=f"{INCOMING}/egypt-latest-free.shp/gis_osm_waterways_free_1.shp",
        suez_ids=f"{INCOMING}/egypt-latest-free.shp/suez_canal_ids.csv",
        global_ports=f"{INCOMING}/Global port supply-chains/Network/nodes_maritime.gpkg",
    output:
        # Layers "nodes" and "edges" are written into the same GeoPackage.
        network=f"{INCOMING}/egypt-latest-free.shp/suez_canal_network.gpkg",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/preprocess - maritime ports
# ---------------------------------------------------------------------------

rule ports_data_cleaning:
    """Match USGS, corridor and global port datasets into the maritime network.

    NOTE: the script contains a ``breakpoint()`` call and will drop into pdb
    unless PYTHONBREAKPOINT=0 is set in the environment.
    """
    input:
        script=f"{PREPROCESS}/ports_data_cleaning.py",
        utils=UTILS_NEW,
        global_ports=f"{INCOMING}/Global port supply-chains/Network/nodes_maritime.gpkg",
        usgs_ports=USGS_PORTS,
        corridor_db=CORRIDOR_DB,
        africa_adm0=AFRICA_ADM0,
        maritime_edges=f"{INCOMING}/ports/edges_maritime_corrected.gpkg",
        suez_network=f"{INCOMING}/suez_canal_network.gpkg",
    output:
        global_network=f"{DATA}/infrastructure/global_maritime_network.gpkg",
        africa_network=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        # Written to the working directory by port_edges.to_csv("test2.csv").
        test_csv="test2.csv",
    shell:
        RUN_SCRIPT


rule ports_new_merge:
    """Merge the 2025 IMF PortWatch port statistics into the maritime network."""
    input:
        script=f"{PREPROCESS}/ports_new_merge.py",
        utils=UTILS_NEW,
        global_network=f"{DATA}/infrastructure/global_maritime_network.gpkg",
        ports_2025=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/Ports.shp",
        port_calls=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/port_calls_average_2019-2024.csv",
        port_capacity=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/port_capacity_called_average_2019-2024.csv",
        port_turnaround=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/port_turn_around_time_average_2019-2024.csv",
    output:
        global_network=f"{DATA}/infrastructure/global_maritime_network_PROVA_NEW1.gpkg",
        africa_network=f"{DATA}/infrastructure/africa_maritime_network_PROVA_NEW1.gpkg",
    shell:
        RUN_SCRIPT


rule merged_points_v2:
    """Merge USGS, global and corridor port points, add ISO3 codes."""
    input:
        script=f"{PREPROCESS}/Merged points-v2.py",
        utils=UTILS,
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
        RUN_SCRIPT


rule sample_code_from_ports_africa:
    """Attach the non-intersected port points to the Africa port network."""
    input:
        script=f"{PREPROCESS}/sample_code_from_ports_africa.py",
        utils=UTILS,
        africa_ports=f"{INCOMING}/ports/africa_ports.gpkg",
        non_intersected=f"{DATA}/non_intersected_from_merged.gpkg",
    output:
        modified=f"{DATA}/africa_ports_modified.gpkg",
    shell:
        RUN_SCRIPT


rule add_id:
    """Fill in node_id, name and ISO3 for the merged port nodes."""
    input:
        script=f"{PREPROCESS}/Add ID.py",
        utils=UTILS,
        non_intersected=f"{DATA}/non_intersected_from_merged.gpkg",
        modified_ports=f"{DATA}/africa_ports_modified.gpkg",
        world_boundaries=NE_110M_COUNTRIES,
        merged_csv=f"{DATA}/merged_with_iso2.csv",
    output:
        output_gpkg=f"{DATA}/output.gpkg",
    shell:
        RUN_SCRIPT


rule economic:
    """Join port weight, value and utilisation statistics to the merged ports.

    NOTE: the script also reads a hard-coded absolute Windows path to
    ``AFR_Infra_Transport_Ports.shp``; that path is not declared here because it
    is not derived from config.json.
    """
    input:
        script=f"{PREPROCESS}/economic.py",
        utils=UTILS,
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
        RUN_SCRIPT


rule port_cargo_attributes:
    """Derive traded commodities and annual capacities per port."""
    input:
        script=f"{PREPROCESS}/port_cargo_attributes.py",
        utils=UTILS,
        port_matches=f"{INCOMING}/ports/all_ports_matches.xlsx",
        corridor_db=CORRIDOR_DB,
        usgs_ports=USGS_PORTS,
        global_network=f"{DATA}/infrastructure/global_maritime_network.gpkg",
        port_utilisation=f"{DATA}/port_statistics/port_utilization.csv",
    output:
        vessel_capacities=f"{DATA}/port_statistics/port_vessel_types_and_capacities.csv",
        commodities=f"{DATA}/port_statistics/port_known_commodities_traded.csv",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/preprocess - railways
# ---------------------------------------------------------------------------

rule rail_data_cleaning:
    """Build the Africa railway network from OSM and corridor project data.

    Step one converts each rail project into a per-project GeoPackage inside the
    ``africa_corridor_developments`` folder; step two merges those with the
    Africa rail network. Note that step two reads ``guinea_lines.gpkg`` while
    step one writes the same project out as ``conakry-kankan_railway.gpkg``, so
    that input has to be supplied (or renamed) by hand.
    """
    input:
        script=f"{PREPROCESS}/rail_data_cleaning.py",
        utils=UTILS_NEW,
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
        RUN_SCRIPT


rule rails_costs:
    """Estimate capital, O&M and investment costs per railway line."""
    input:
        script=f"{PREPROCESS}/rails_costs.py",
        utils=UTILS_NEW,
        rail_network=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        costs=f"{INCOMING}/Rail_Costs.xlsx",
    output:
        costs=f"{DATA}/infrastructure/africa_rails_costs.csv",
    shell:
        RUN_SCRIPT


rule google_api_matches:
    """Match rail facilities against mines, ports, airports and Google places."""
    input:
        script=f"{PREPROCESS}/google_api_matches.py",
        utils=UTILS_NEW,
        rail_network=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        google_points=f"{INCOMING}/africa-station-google-points/stations_with_google_api_points.csv",
        global_mines=f"{INCOMING}/Supplementary 1：mine area polygons/74548 mine polygons/74548_projected.shp",
        usgs_facilities=(
            f"{INCOMING}/Africa_GIS Supporting Data/a. Africa_GIS Shapefiles/"
            "AFR_Mineral_Facilities.shp/AFR_Mineral_Facilities.shp"
        ),
        airports=f"{DATA}/infrastructure/africa_airport_network.gpkg",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        previous_matches=f"{RESULTS}/africa-station-google-points/location_proximity_final.gpkg",
    output:
        matches=f"{INCOMING}/africa-station-google-points/location_proximity_final.gpkg",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/preprocess - roads
# ---------------------------------------------------------------------------

rule road_connectivity:
    """Connect points of interest to the OSM road network (README step 1-5)."""
    input:
        script=f"{PREPROCESS}/road_connectivity.py",
        utils=UTILS_NEW,
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
        RUN_SCRIPT


rule road_corridors_primary_roads:
    """Route the named road corridors over the primary road network."""
    input:
        script=f"{PREPROCESS}/road_corridors_primary_roads.py",
        utils=UTILS_NEW,
        road_edges=f"{DATA}/infrastructure/africa_roads_edges.geoparquet",
        road_nodes=f"{DATA}/infrastructure/africa_roads_nodes.geoparquet",
        corridors=f"{INCOMING}/road_corridors.xlsx",
    output:
        nodes=f"{DATA}/infrastructure/africa_roads_nodes_withcorridors.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges_withcorridors.geoparquet",
    shell:
        RUN_SCRIPT


rule road_corridors_ns_corridor:
    """Route the Lobito corridor over the AGO/COD/ZMB road network.

    Despite the file name, this script reads ``Lobito_corridor.xlsx`` and writes
    the ``PROVA_Lobito_corridor`` layers.
    """
    input:
        script=f"{PREPROCESS}/road_corridors_NS_corridor.py",
        utils=UTILS_NEW,
        road_edges=f"{INCOMING}/africa_roads/edges_with_topology.geoparquet",
        road_nodes=f"{INCOMING}/africa_roads/nodes_with_topology.geoparquet",
        corridor=f"{INCOMING}/Lobito_corridor.xlsx",
    output:
        nodes=f"{DATA}/infrastructure/africa_roads_nodes_PROVA_Lobito_corridor.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges_PROVA_Lobito_corridor.geoparquet",
    shell:
        RUN_SCRIPT


rule road_adjustments:
    """Merge the per-corridor road extracts into the final road network.

    This script also writes the ``nodes`` and ``edges`` layers of

        {DATA}/infrastructure/africa_roads_network.gpkg

    but that file is re-written by ``costs_columns`` and then ``road_processing``,
    so it is declared as the output of ``road_processing`` only - two jobs in one
    DAG may not write the same file.
    """
    input:
        script=f"{PREPROCESS}/RoadAdjustments.py",
        utils=UTILS_NEW,
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
        RUN_SCRIPT


rule costs_columns:
    """Tidy the road node/edge columns and cap the lane count.

    As well as the GeoPackage declared below, this script rewrites its two
    inputs in place:

        {DATA}/infrastructure/africa_roads_nodes_FINAL.geoparquet
        {DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet

    Those two files are deliberately left out of ``output`` because declaring
    a file as both the input and the output of a rule that another rule also
    produces makes the dependency graph cyclic.
    """
    input:
        script=f"{PREPROCESS}/costs_columns.py",
        utils=UTILS_NEW,
        nodes=f"{DATA}/infrastructure/africa_roads_nodes_FINAL.geoparquet",
        edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
    output:
        network=f"{DATA}/infrastructure/africa_roads_network.gpkg",
    shell:
        RUN_SCRIPT


rule road_processing:
    """Infer paved status, surface material and asset type for road edges."""
    input:
        script=f"{PREPROCESS}/road_processing.py",
        utils=UTILS,
        edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
    output:
        edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL_last.geoparquet",
        network=f"{DATA}/infrastructure/africa_roads_network.gpkg",
    shell:
        RUN_SCRIPT


rule corridors_costs:
    """Estimate capital, O&M and investment costs per road corridor."""
    input:
        script=f"{PREPROCESS}/corridors_costs.py",
        utils=UTILS_NEW,
        road_network=f"{DATA}/infrastructure/africa_roads_network.gpkg",
        costs=f"{INCOMING}/Roads_Costs.xlsx",
    output:
        merged_costs=f"{DATA}/infrastructure/merged_costs_data.csv",
        corridor_costs=f"{DATA}/infrastructure/africa_corridors_costs.csv",
    shell:
        RUN_SCRIPT


rule stats_rail_roads:
    """Summarise rail length by status and road length by corridor/surface."""
    input:
        script=f"{PREPROCESS}/stats_rail_roads.py",
        utils=UTILS_NEW,
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        rail_network=f"{DATA}/infrastructure/africa_railways_network.gpkg",
    output:
        rail_stats=f"{DATA}/infrastructure/rail_stats.csv",
        paved_stats=f"{DATA}/infrastructure/paved_stats2.csv",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/preprocess - HeiGIT road surface validation
# ---------------------------------------------------------------------------

rule merge_heigit_data:
    """Merge the per-country HeiGIT road surface GeoPackages into one file."""
    input:
        script=f"{PREPROCESS}/merge_heigit_data.py",
        utils=UTILS_NEW,
        # The script globs heigit_*_roadsurface_lines.gpkg in this folder.
        heigit_folder=f"{INCOMING}/Randhawaetal_2025_Locations",
    output:
        merged=f"{DATA}/infrastructure/validation_file_merge.geoparquet",
    shell:
        RUN_SCRIPT


rule heigit_check:
    """Compare database road surfaces against the merged HeiGIT dataset."""
    input:
        script=f"{PREPROCESS}/heigit_check.py",
        utils=UTILS_NEW,
        database_lines=f"{DATA}/infrastructure/africa_roads_edges.geoparquet",
        heigit_lines=f"{DATA}/infrastructure/validation_file_merge.geoparquet",
        boundaries=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg",
    output:
        merged=f"{RESULTS}/merged_validation_datasets.parquet",
        pivot=f"{RESULTS}/merged_validation_datasets.csv",
        pivot_corrected=f"{RESULTS}/merged_validation_datasets_corrected.csv",
    shell:
        RUN_SCRIPT


rule roads_validation_comparison:
    """Clip database and HeiGIT roads by country and compare paved lengths."""
    input:
        script=f"{PREPROCESS}/roads_validation_comparison.py",
        utils=UTILS_NEW,
        database_lines=f"{DATA}/infrastructure/africa_roads_edges_FINAL_last.geoparquet",
        boundaries=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg",
        # One HeiGIT file per country is read, if present, from this folder.
        heigit_folder=f"{INCOMING}/Randhawaetal_2025_Locations",
    output:
        merged=f"{DATA}/infrastructure/merged_validation_datasets.parquet",
        pivot=f"{DATA}/infrastructure/merged_validation_datasets.csv",
        counts=f"{DATA}/infrastructure/merged_validation_datasets_counts.csv",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/preprocess - airports
# ---------------------------------------------------------------------------

rule airports_data_cleaning:
    """Rebuild airport route geometries and attach origin/destination ISO3."""
    input:
        script=f"{PREPROCESS}/airports_data_cleaning.py",
        utils=UTILS_NEW,
        airport_network=f"{DATA}/infrastructure/africa_airport_network.gpkg",
    output:
        network=f"{DATA}/infrastructure/africa_airport_network_last.gpkg",
    shell:
        RUN_SCRIPT


rule ourairports_data_layer:
    """Filter the OurAirports layer to the airports in the network."""
    input:
        script=f"{PREPROCESS}/ourairports_data_layer.py",
        utils=UTILS_NEW,
        ourairports=f"{INCOMING}/airports/africa_airports_ourairport.gpkg",
        airport_network=f"{DATA}/infrastructure/africa_airport_network.gpkg",
    output:
        ourairports=f"{DATA}/infrastructure/africa_airport_ourairport_rev.gpkg",
        network=f"{DATA}/infrastructure/africa_airport_network_rev.gpkg",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/preprocess - inland waterways
# ---------------------------------------------------------------------------

rule inland_waterways_cleaning:
    """Build the inland waterway network from IWW ports, lakes and rivers."""
    input:
        script=f"{PREPROCESS}/inland_waterways_cleaning.py",
        utils=UTILS_NEW,
        iww_ports=f"{INCOMING}/IWW_ports/africa_IWW_ports.xlsx",
        congo_rivers=f"{INCOMING}/IWW_ports/edges_port_IWW_af.gpkg",
        south_sudan=f"{INCOMING}/IWW_ports/hotosm_ssd_waterways.gpkg",
        africa_adm0=AFRICA_ADM0,
    output:
        network=f"{DATA}/infrastructure/africa_iww_network.gpkg",
    shell:
        RUN_SCRIPT


rule africa_inland_waterways:
    """Route IWW ports over the OSM river network (step 3 of the script).

    Steps 1 and 2 are switched off in the script (``step = False``); when
    enabled they read ``OpenStreetMap_Waterways_for_Africa.geoparquet``,
    ``africa_river_edges.geoparquet`` and ``IWW_ports/africa_IWW_ports.xlsx``,
    and write ``africa_river_{nodes,edges}.geoparquet`` and
    ``africa_network_{nodes,edges}.geoparquet`` into ``Africa_osm_rivers``.
    """
    input:
        script=f"{PREPROCESS}/africa_inland_waterways.py",
        utils=UTILS,
        network_edges=f"{INCOMING}/Africa_osm_rivers/africa_network_edges.geoparquet",
        network_nodes=f"{INCOMING}/Africa_osm_rivers/africa_network_nodes.geoparquet",
        africa_adm0=AFRICA_ADM0,
    output:
        network=f"{DATA}/infrastructure/africa_iww_network.gpkg",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/preprocess - multi-modal links and finishing steps
# ---------------------------------------------------------------------------

rule multi_modal_edges_creation:
    """Create the inter-modal links between sea, IWW, rail, air and road."""
    input:
        script=f"{PREPROCESS}/multi_modal_edges_creation.py",
        utils=UTILS_NEW,
        airports=f"{DATA}/infrastructure/africa_airport_network.gpkg",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        road_nodes=f"{DATA}/infrastructure/africa_roads_nodes_FINAL.geoparquet",
    output:
        multimodal=f"{DATA}/infrastructure/africa_multimodal_rev.gpkg",
    shell:
        RUN_SCRIPT


rule data_checks:
    """Reduce the multi-modal edge layer to the published set of columns.

    The script reads and rewrites

        {DATA}/infrastructure/africa_multimodal.gpkg

    in place. Only the write is declared below: naming the same file as both
    the input and the output of a rule makes the dependency graph cyclic.
    """
    input:
        script=f"{PREPROCESS}/data_checks.py",
        utils=UTILS_NEW,
    output:
        multimodal=f"{DATA}/infrastructure/africa_multimodal.gpkg",
    shell:
        RUN_SCRIPT


rule source_column:
    """Add the data-source citation column to every published network layer."""
    input:
        script=f"{PREPROCESS}/source_column.py",
        utils=UTILS_NEW,
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
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/plot - maps
# ---------------------------------------------------------------------------

rule plot_africa_basemap:
    """Plot the Africa basemap on its own."""
    input:
        script=f"{PLOT}/africa_maps.py",
        utils=PLOT_UTILS,
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/africa_basemap.png",
    shell:
        RUN_SCRIPT


rule plot_airports:
    """Map airports sized by total annual seats."""
    input:
        script=f"{PLOT}/africa_maps_airports.py",
        utils=PLOT_UTILS,
        airports=f"{DATA}/infrastructure/africa_airport_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/airports.png",
    shell:
        RUN_SCRIPT


rule plot_ports_and_iww:
    """Map maritime ports, inland ports and their routes."""
    input:
        script=f"{PLOT}/africa_maps_ports.py",
        utils=PLOT_UTILS,
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/IWW_and_ports.png",
    shell:
        RUN_SCRIPT


rule plot_ports_bubble:
    """Map maritime and inland ports as proportional bubbles."""
    input:
        script=f"{PLOT}/africa_maps_ports_bubble.py",
        utils=PLOT_UTILS,
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/ports_with_edges_last.png",
    shell:
        RUN_SCRIPT


rule plot_rails_gauge:
    """Map the railway network coloured by gauge."""
    input:
        script=f"{PLOT}/africa_maps_rails.py",
        utils=PLOT_UTILS,
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/rail_test_gauge.png",
    shell:
        RUN_SCRIPT


rule plot_rails_facilities:
    """Map railway stations by facility type."""
    input:
        script=f"{PLOT}/africa_maps_rails_facilities.py",
        utils=PLOT_UTILS,
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/rail_test_facility.png",
    shell:
        RUN_SCRIPT


rule plot_roads_typology:
    """Map the road network coloured by highway typology."""
    input:
        script=f"{PLOT}/africa_maps_roads.py",
        utils=PLOT_UTILS,
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/roads_typology2_LAST.png",
    shell:
        RUN_SCRIPT


rule plot_roads_corridors:
    """Map the road network coloured by development corridor."""
    input:
        script=f"{PLOT}/africa_maps_roads_corridors.py",
        utils=PLOT_UTILS,
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        legend=f"{FIGURES}/roads_corridors_legend_LAST.png",
        figure=f"{FIGURES}/roads_corridors_LAST.png",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/plot - charts
# ---------------------------------------------------------------------------

rule plot_rail_histogram:
    """Stacked bar chart of railway length by country and status."""
    input:
        script=f"{PLOT}/africa_hist_rails.py",
        utils=PLOT_UTILS,
        railways=f"{DATA}/infrastructure/africa_railways_network.gpkg",
    output:
        figure=f"{FIGURES}/rail_hist_cap_withgrid.png",
    shell:
        RUN_SCRIPT


rule plot_roads_histogram:
    """Stacked bar chart of road length by corridor and typology."""
    input:
        script=f"{PLOT}/africa_hist_roads.py",
        utils=PLOT_UTILS,
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
    output:
        figure=f"{FIGURES}/roads_hist_cap2_grid.png",
    shell:
        RUN_SCRIPT


rule plot_multi_modal_proximity:
    """Histogram of multi-modal link lengths by connection type."""
    input:
        script=f"{PLOT}/multi_proximity_plot.py",
        utils=PLOT_UTILS,
        multimodal=f"{DATA}/infrastructure/africa_multimodal.gpkg",
    output:
        figure=f"{FIGURES}/multi_modal_proximity.png",
    shell:
        RUN_SCRIPT


rule plot_rail_facility_proximity:
    """Histogram of rail facility distances to matched reference locations."""
    input:
        script=f"{PLOT}/rail_location_proximity_plot.py",
        utils=PLOT_UTILS,
        matches=f"{RESULTS}/africa-station-google-points/location_proximity_final.gpkg",
    output:
        figure=f"{FIGURES}/rail_facility_proximity.png",
    shell:
        RUN_SCRIPT


rule plot_heigit_bar_charts:
    """Bar charts comparing this database against HeiGIT and rail references."""
    input:
        script=f"{PLOT}/heigit_bar_charts.py",
        utils=PLOT_UTILS,
        validation=f"{RESULTS}/merged_validation_datasets_corrected.csv",
        country_codes=f"{DATA}/admin_boundaries/country_codes.xlsx",
        rails=f"{RESULTS}/rails.xlsx",
    output:
        comparison=f"{FIGURES}/heigit_comparison.png",
        differences_csv=f"{RESULTS}/merged_validation_datasets_differences.csv",
        differences=f"{FIGURES}/heigit_difference.png",
        rail_comparisons=f"{FIGURES}/rail_comparisons.png",
    shell:
        RUN_SCRIPT


rule plot_location_maps:
    """Maps of optimised mine and processing locations.

    NOTE: this script imports ``trade_functions`` and calls
    ``map_background_and_bounds()``, neither of which is part of this
    repository - it is carried over from the transport-critical-minerals
    project and needs those modules on the PYTHONPATH.
    """
    input:
        script=f"{PLOT}/location_maps.py",
        utils=PLOT_UTILS,
        ccg_countries=CCG_COUNTRY_CODES,
        stage_mapping=f"{DATA}/mineral_usage_factors/stage_mapping.xlsx",
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
        RUN_SCRIPT


rule plot_mine_ownership_maps:
    """Global maps of mine ownership shares by country.

    NOTE: this script calls ``map_background_and_bounds()``, which is not part
    of this repository - it is carried over from the
    transport-critical-minerals project.
    """
    input:
        script=f"{PLOT}/mine_ownership_maps.py",
        utils=PLOT_UTILS,
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
        centroids=f"{DATA}/admin_boundaries/centroids/countries_iso3_code.csv",
        ownership=f"{RESULTS}/mine_ownership/df_maps_2022.csv",
    output:
        basemap=f"{FIGURES}/mine_ownership/global_basemap.png",
        totals=f"{FIGURES}/mine_ownership/mine_totals.svg",
        by_ownership=f"{FIGURES}/mine_ownership/country_totals_by_ownership.svg",
    shell:
        RUN_SCRIPT


# ---------------------------------------------------------------------------
# scripts/maps and stats
# ---------------------------------------------------------------------------

rule maps_validation:
    """Cluster-compare the maritime port database against CIA port counts."""
    input:
        script=f"{MAPS_AND_STATS}/validation.py",
        ports=f"{DATA}/Validation sets/ports.csv",
    output:
        clusters=f"{DATA}/Validation sets/port_cluster_comparison_k3.csv",
    shell:
        RUN_SCRIPT


rule maps_graphs:
    """Plot the main road network over the Africa basemap.

    NOTE: the script contains a ``breakpoint()`` call and will drop into pdb
    unless PYTHONBREAKPOINT=0 is set in the environment.
    """
    input:
        script=f"{MAPS_AND_STATS}/graphs.py",
        utils=MAPS_UTILS,
        ccg_countries=CCG_COUNTRY_CODES,
        main_roads=f"{INCOMING}/africa_roads/africa_main_roads.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/roads_test.png",
    shell:
        RUN_SCRIPT


rule maps_graphs_transport:
    """Plot the final road edges by corridor over the Africa basemap.

    NOTE: the script contains ``breakpoint()`` calls and will drop into pdb
    unless PYTHONBREAKPOINT=0 is set in the environment.
    """
    input:
        script=f"{MAPS_AND_STATS}/graphs_transport.py",
        utils=MAPS_UTILS,
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
    output:
        figure=f"{FIGURES}/roads_test.png",
    shell:
        RUN_SCRIPT


rule maps_global_maps:
    """Map copper node and edge flows over the Africa basemap.

    Only the last ``plot_flows`` block is enabled in the script; the disabled
    blocks additionally read ``Minerals/copper_mines_tons_refined_unrefined.gpkg``,
    ``minerals/ccg_mines_est_production.gpkg``, ``Minerals/s_and_p_mines.gpkg``
    and ``flow_mapping/{mineral}_flows_{year}.gpkg``.
    """
    input:
        script=f"{MAPS_AND_STATS}/global_maps.py",
        utils=MAPS_UTILS,
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
        RUN_SCRIPT


rule maps_global_maps_transport:
    """Map railway status, then copper node and edge flows.

    NOTE: the script contains a ``breakpoint()`` call after the railway status
    map and will drop into pdb unless PYTHONBREAKPOINT=0 is set. As for
    ``global_maps.py``, the disabled blocks read further mineral datasets.

    It also writes {FIGURES}/ccg_copper_total_africa_node_edge_flows_2022.png,
    which is declared as the output of ``maps_global_maps`` instead - two jobs in
    one DAG may not write the same file.
    """
    input:
        script=f"{MAPS_AND_STATS}/global_maps_transport.py",
        utils=MAPS_UTILS,
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
        RUN_SCRIPT
