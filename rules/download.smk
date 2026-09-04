"""Fetch the incoming data.

Most of the incoming data cannot be fetched automatically: it comes from
click-through portals, from the outputs of a separate workflow, or from files
the authors compiled by hand. The rules below cover the layers that do have a
stable direct URL; everything else is inventoried in DATA SOURCES so that the
remaining download rules can be written as the sources allow.

The URLs here could not be reached from the environment this file was written
in, so treat them as a starting point rather than a tested download.

DATA SOURCES
------------
Grouped by provider. "auto" means a rule below fetches it; "manual" means it
has to be put in place by hand before the workflow will run.

Natural Earth - auto (rules below)
    {DATA}/admin_boundaries/ne_10m_admin_0_countries/*
    {DATA}/admin_boundaries/ne_10m_lakes/*
    {INCOMING}/ports/ne_110m_admin_0_countries/*

OpenStreetMap, via Geofabrik https://download.geofabrik.de/ - manual
    {INCOMING}/osm/africa-260219.osm.pbf
    {INCOMING}/egypt-latest-free.shp/gis_osm_waterways_free_1.shp
    The Africa extract is pinned to a 2026-02-19 snapshot. Geofabrik keeps
    dated extracts for 90 days and full history behind a subscription, so a
    download rule needs a snapshot date it can still reach - see EXTENSION
    POINTS.

Open-gira road network https://github.com/nismod/open-gira - manual
    {INCOMING}/africa_roads/edges_with_topology.gpq
    {INCOMING}/africa_roads/nodes_with_topology.gpq
    {INCOMING}/africa_roads/edges_with_topology.geoparquet
    {INCOMING}/africa_roads/nodes_with_topology.geoparquet
    Produced by a separate workflow; the two file extensions are the same
    layers under two names - see EXTENSION POINTS.

USGS Africa GIS supporting data https://doi.org/10.5066/P97EQWXP - manual
    {INCOMING}/Africa_GIS Supporting Data/a. Africa_GIS Shapefiles/
        AFR_Political_ADM0_Boundaries.shp/
        AFR_Infra_Transport_Ports.shp/
        AFR_Mineral_Facilities.shp/

African Development Corridors Database https://doi.org/10.5061/dryad.9kd51c5hw - manual
    {INCOMING}/africa_corridor_developments/AfricanDevelopmentCorridorDatabase2022.gpkg

Global port supply-chains https://doi.org/10.17632/kdyt24tsh5.1 - manual
    {INCOMING}/Global port supply-chains/Network/nodes_maritime.gpkg
    {INCOMING}/Global port supply-chains/Port_statistics/port_locations_value.csv
    {INCOMING}/Global port supply-chains/Port_statistics/port_locations_weight.csv
    {INCOMING}/Global port supply-chains/Port_statistics/port_utilization.csv

IMF PortWatch https://portwatch.imf.org/ - manual
    {INCOMING}/Global port supply-chains/Ports Updated 2025/Ports.shp
    {INCOMING}/Global port supply-chains/Ports Updated 2025/port_calls_average_2019-2024.csv
    {INCOMING}/Global port supply-chains/Ports Updated 2025/port_capacity_called_average_2019-2024.csv
    {INCOMING}/Global port supply-chains/Ports Updated 2025/port_turn_around_time_average_2019-2024.csv

Africa rail network https://github.com/trg-rail/africa_rail_network - manual
    {INCOMING}/africa_rail_network/network_data/africa_railways.gpkg
    {INCOMING}/africa_rail_network/network_data/africa_rail_nodes.geojson

Rail corridor projects, digitised by the authors from AU-PIDA
https://www.au-pida.org/pida-projects/ and the corridors database - manual
    {INCOMING}/africa_corridor_developments/17D.1.gpkg
    {INCOMING}/africa_corridor_developments/Dar_es.gpkg
    {INCOMING}/africa_corridor_developments/Team.gpkg
    {INCOMING}/africa_corridor_developments/eastafrica_rail.gpkg
    {INCOMING}/africa_corridor_developments/guinea_lines.gpkg
    {INCOMING}/africa_corridor_developments/guinea_rail.shp
    {INCOMING}/africa_corridor_developments/kinsasha_rail.gpkg
    {INCOMING}/africa_corridor_developments/tanzania_sgr_lines.gpkg
    {INCOMING}/africa_corridor_developments/togo_lines.gpkg

OurAirports https://ourairports.com/ - manual
    {INCOMING}/airports/africa_airports_ourairport.gpkg

World Bank Global Airports
https://datacatalog.worldbank.org/search/dataset/0038117/Global-Airports - manual
    {DATA}/infrastructure/africa_airport_network.gpkg
    Read by six rules and written by none - see EXTENSION POINTS.

HeiGIT road surface, Randhawa et al. 2025 - manual
    {INCOMING}/Randhawaetal_2025_Locations/heigit_<iso3>_roadsurface_lines.gpkg

Global mine polygons - manual
    {INCOMING}/Supplementary 1：mine area polygons/74548 mine polygons/74548_projected.shp

Google Places API results, collected by the authors - manual
    {INCOMING}/africa-station-google-points/stations_with_google_api_points.csv

GADM https://gadm.org/ - manual
    {DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg
    Derived from the GADM 3.6 levels GeoPackage with a continent column added,
    so it needs a processing rule as well as a download - see EXTENSION POINTS.

Other admin boundary lookups, compiled by the authors - manual
    {DATA}/admin_boundaries/ccg_country_codes.csv
    {DATA}/admin_boundaries/centroids/countries_iso3_code.csv
    {DATA}/admin_boundaries/country_codes.xlsx
    {DATA}/admin_boundaries/un_urban_population/un_pop_df.gpkg

Inland waterways and cost assumptions, compiled by the authors - manual
    {INCOMING}/IWW_ports/africa_IWW_ports.xlsx
    {INCOMING}/IWW_ports/edges_port_IWW_af.gpkg
    {INCOMING}/IWW_ports/hotosm_ssd_waterways.gpkg
    {INCOMING}/Africa_osm_rivers/africa_network_edges.geoparquet
    {INCOMING}/Africa_osm_rivers/africa_network_nodes.geoparquet
    {INCOMING}/Lobito_corridor.xlsx
    {INCOMING}/Rail_Costs.xlsx
    {INCOMING}/Roads_Costs.xlsx
    {INCOMING}/road_corridors.xlsx
    {INCOMING}/ports/africa_ports.gpkg
    {INCOMING}/ports/all_ports_matches.xlsx
    {INCOMING}/ports/edges_maritime_corrected.gpkg
    {INCOMING}/ports/nodes_maritime.gpkg
    {INCOMING}/egypt-latest-free.shp/suez_canal_ids.csv
    {DATA}/Validation sets/ports.csv
    {DATA}/port_statistics/port_utilization.csv
    {RESULTS}/rails.xlsx

transport-critical-minerals workflow outputs - manual
    {RESULTS}/flow_mapping/edges_flows_2022.gpkg
    {RESULTS}/flow_mapping/nodes_flows_2022.gpkg
    {RESULTS}/flow_mapping/mining_city_node_level_ods_2022.csv
    {RESULTS}/mine_ownership/df_maps_2022.csv
    {RESULTS}/optimised_processing_locations/
    {DATA}/mineral_usage_factors/aggregated_stages.xlsx
    {DATA}/mineral_usage_factors/metal_content.csv
    {DATA}/mineral_usage_factors/mineral_usage_factors.xlsx
    {DATA}/mineral_usage_factors/stage_mapping.xlsx
    {DATA}/baci/baci_ccg_minerals_trade_2022_bgs_corrected.csv
    {DATA}/baci/ccg_country_codes.csv
    {DATA}/baci/mine_city_stages.csv
    Read by the maps and stats rules, which were carried over from that
    project - see EXTENSION POINTS.

EXTENSION POINTS
----------------
Things to settle before the workflow can run end to end, roughly in the order
they bite:

1. Road corridor extracts. ``road_adjustments`` reads five pairs of corridor
   geoparquets (Lobito, NS, TA, TSH, MDG) but only the Lobito pair has a rule.
   ``scripts/preprocess/road_corridors_NS_corridor.py`` is hard-coded to the
   Lobito spreadsheet and the AGO/COD/ZMB country filter. Generalising it to
   take a corridor name, spreadsheet and country list would turn
   ``road_corridors_ns_corridor`` into one wildcard rule covering all five, and
   is the single biggest gap in the DAG.

2. Suez canal path mismatch. ``extract_suez`` writes
   ``{INCOMING}/egypt-latest-free.shp/suez_canal_network.gpkg`` but
   ``ports_data_cleaning`` reads ``{INCOMING}/suez_canal_network.gpkg``, so the
   two rules are not connected. One of the two paths needs to change.

3. Rail project file naming. ``rail_data_cleaning`` writes the Conakry-Kankan
   project as ``conakry-kankan_railway.gpkg`` and then reads it back as
   ``guinea_lines.gpkg``. The two names need to agree before the second half of
   the script can use the first half's output.

4. Google API matches path mismatch. ``google_api_matches`` reads
   ``{RESULTS}/africa-station-google-points/location_proximity_final.gpkg`` and
   writes ``{INCOMING}/africa-station-google-points/location_proximity_final.gpkg``,
   so it cannot be re-run from its own output and does not connect to
   ``plot_rail_facility_proximity``, which reads the ``{RESULTS}`` copy.

5. Road network file extensions. ``road_connectivity`` reads
   ``{INCOMING}/africa_roads/*_with_topology.gpq`` while
   ``road_corridors_ns_corridor`` reads ``*_with_topology.geoparquet``. These
   are the same open-gira layers under two extensions.

6. Port utilisation duplicated. ``port_cargo_attributes`` reads
   ``{DATA}/port_statistics/port_utilization.csv`` and ``economic`` reads
   ``{INCOMING}/Global port supply-chains/Port_statistics/port_utilization.csv``.

7. Airport network. Nothing builds
   ``{DATA}/infrastructure/africa_airport_network.gpkg``; it is the World Bank
   Global Airports layer after some preparation that is not in this repository.
   A rule for that preparation would close the last mode-level gap.

8. GADM continents layer. ``gadm36_levels_continents.gpkg`` is GADM 3.6 with a
   continent attribute joined on. A download rule plus a small processing rule
   would replace the manual step.

9. OSM snapshot. The Africa extract is pinned to a date Geofabrik no longer
   serves publicly. Either pin to a snapshot that stays reachable, or take the
   date from config so a refresh is a config change rather than a code change.

10. Minerals rules. ``maps_global_maps``, ``maps_global_maps_transport``,
    ``plot_location_maps`` and ``plot_mine_ownership_maps`` read the outputs of
    the transport-critical-minerals workflow, including the BACI trade and
    mineral usage factor tables that ``location_maps.py`` reads through
    ``modify_mineral_usage_factors()``. They belong either behind an opt-in
    target or in that repository.
"""

# Natural Earth vector data, from the version-tagged GitHub mirror so that the
# sidecar files come down individually and the version is pinned.
NATURAL_EARTH_VERSION = "5.1.2"
NATURAL_EARTH_URL = "https://github.com/nvkelso/natural-earth-vector/raw/refs/tags/v{version}/{folder}/{layer}"
NATURAL_EARTH_EXTENSIONS = [".shp", ".shx", ".dbf", ".prj", ".cpg"]

# Each output path ends in the extension to fetch, so one loop covers them all.
NATURAL_EARTH_SHELL = """
for path in {output}; do
    mkdir -p "$(dirname "$path")"
    curl -fsSL "{params.url}.${{path##*.}}" -o "$path"
done
"""


rule download_natural_earth_countries:
    """Country outlines used as the basemap for every map"""
    output:
        multiext(
            f"{DATA}/admin_boundaries/ne_10m_admin_0_countries/ne_10m_admin_0_countries",
            *NATURAL_EARTH_EXTENSIONS,
        ),
    params:
        url=NATURAL_EARTH_URL.format(
            version=NATURAL_EARTH_VERSION,
            folder="10m_cultural",
            layer="ne_10m_admin_0_countries",
        ),
    shell:
        NATURAL_EARTH_SHELL


rule download_natural_earth_lakes:
    """Lakes, drawn over the basemap so that they read as water not land"""
    output:
        multiext(
            f"{DATA}/admin_boundaries/ne_10m_lakes/ne_10m_lakes",
            *NATURAL_EARTH_EXTENSIONS,
        ),
    params:
        url=NATURAL_EARTH_URL.format(
            version=NATURAL_EARTH_VERSION,
            folder="10m_physical",
            layer="ne_10m_lakes",
        ),
    shell:
        NATURAL_EARTH_SHELL


rule download_natural_earth_countries_110m:
    """Coarser country outlines, used to look up ISO3 codes for port points"""
    output:
        multiext(
            f"{INCOMING}/ports/ne_110m_admin_0_countries/ne_110m_admin_0_countries",
            *NATURAL_EARTH_EXTENSIONS,
        ),
    params:
        url=NATURAL_EARTH_URL.format(
            version=NATURAL_EARTH_VERSION,
            folder="110m_cultural",
            layer="ne_110m_admin_0_countries",
        ),
    shell:
        NATURAL_EARTH_SHELL
