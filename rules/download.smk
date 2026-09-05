"""Fetch the incoming data.

Some of the incoming data can be fetched from a stable URL; the rest comes
from click-through portals, from the outputs of a separate workflow, or from
files the authors compiled or digitised by hand. Every external input is
inventoried in DATA SOURCES below, so that the gaps are visible even where no
rule can close them.

HOW FAR EACH RULE HAS BEEN TESTED
---------------------------------
The environment these rules were written in can only reach GitHub and Amazon
S3, so:

    tested   the URL was fetched and the response checked
    drafted  the URL follows the source's documented download API, but the
             first person with network access to that host has to confirm it,
             and in particular has to check that what comes out of the archive
             lands at the paths the rule declares

Tested: ``download_africa_rail_network``, ``download_osm_planet``.
Everything else is drafted.

DATA SOURCES
------------
Grouped by provider. "auto" means a rule below fetches it; "manual" means it
has to be put in place by hand before the workflow will run.

Natural Earth - auto (tested)
    {DATA}/admin_boundaries/ne_10m_admin_0_countries/*
    {DATA}/admin_boundaries/ne_10m_lakes/*
    {INCOMING}/ports/ne_110m_admin_0_countries/*

OpenStreetMap planet, via the OSMF bucket on S3 - auto (tested)
    {INCOMING}/osm/planet-{snapshot}.osm.pbf
    {INCOMING}/osm/africa-{snapshot}.osm.pbf
    The Africa extract used to be a Geofabrik dated extract pinned to
    2026-02-19, which Geofabrik no longer serves - see EXTENSION POINTS.

OpenStreetMap Egypt, via Geofabrik https://download.geofabrik.de/ - auto (drafted)
    {INCOMING}/egypt-latest-free.shp/gis_osm_waterways_free_1.shp

Open-gira road network https://github.com/nismod/open-gira - manual
    {INCOMING}/africa_roads/edges_with_topology.gpq
    {INCOMING}/africa_roads/nodes_with_topology.gpq
    {INCOMING}/africa_roads/edges_with_topology.geoparquet
    {INCOMING}/africa_roads/nodes_with_topology.geoparquet
    Produced by a separate workflow; the two file extensions are the same
    layers under two names - see EXTENSION POINTS.

USGS Africa GIS supporting data https://doi.org/10.5066/P97EQWXP - auto (drafted)
    {INCOMING}/Africa_GIS Supporting Data/a. Africa_GIS Shapefiles/
        AFR_Political_ADM0_Boundaries.shp/
        AFR_Infra_Transport_Ports.shp/
        AFR_Mineral_Facilities.shp/

African Development Corridors Database https://doi.org/10.5061/dryad.9kd51c5hw - auto (drafted)
    {INCOMING}/africa_corridor_developments/AfricanDevelopmentCorridorDatabase2022.gpkg

Global port supply-chains https://doi.org/10.17632/vzzy3b9gg4.1 - auto (drafted)
    {INCOMING}/Global port supply-chains/Network/nodes_maritime.gpkg
    {INCOMING}/Global port supply-chains/Port_statistics/port_locations_value.csv
    {INCOMING}/Global port supply-chains/Port_statistics/port_locations_weight.csv
    {INCOMING}/Global port supply-chains/Port_statistics/port_utilization.csv
    Verschuur et al. (2022), "Ports' criticality in international trade and
    global supply-chains". This inventory previously cited
    10.17632/kdyt24tsh5.1, which is the same authors' port multi-hazard risk
    dataset and does not contain these files; the folder names in the paths
    above are the folder names in vzzy3b9gg4.

IMF PortWatch https://portwatch.imf.org/ - auto (drafted)
    {INCOMING}/Global port supply-chains/Ports Updated 2025/Ports.shp
    {INCOMING}/Global port supply-chains/Ports Updated 2025/port_calls_average_2019-2024.csv
    {INCOMING}/Global port supply-chains/Ports Updated 2025/port_capacity_called_average_2019-2024.csv
    {INCOMING}/Global port supply-chains/Ports Updated 2025/port_turn_around_time_average_2019-2024.csv
    PortWatch publishes the port point layer and a daily activity table; the
    three "average_2019-2024" tables are aggregates of the daily table, not
    downloads - see EXTENSION POINTS.

Africa rail network https://github.com/trg-rail/africa_rail_network - auto (tested)
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
    AU-PIDA publishes project attributes, not geometry: the Virtual PIDA
    Information Centre serves a projects dashboard whose export buttons give
    the filtered project list, a stakeholder database, and per-project PDF
    "fiches" from a fiche generator. None of those carry the alignment of a
    railway. The one geospatial PIDA-derived source is the African
    Development Corridors Database above, which maps corridors and the
    projects along them but not these individual project alignments. So these
    nine files stay hand-digitised, and the honest download rule for them is
    the corridors database rule plus this note.

OurAirports https://ourairports.com/ - auto (drafted)
    {INCOMING}/airports/africa_airports_ourairport.gpkg

World Bank Global Airports
https://datacatalog.worldbank.org/search/dataset/0038117/Global-Airports - auto (drafted)
    {DATA}/infrastructure/africa_airport_network.gpkg
    The download rule fetches the World Bank point layer. That layer is not
    yet the file the workflow reads, which is a node-and-edge network - see
    EXTENSION POINTS.

HeiGIT road surface, Randhawa et al. 2025 - auto (drafted)
    {INCOMING}/Randhawaetal_2025_Locations/heigit_<iso3>_roadsurface_lines.gpkg

Global mine polygons, Tang and Werner 2023 https://doi.org/10.5281/zenodo.7894216 - auto (drafted)
    {INCOMING}/Supplementary 1：mine area polygons/74548 mine polygons/74548_projected.shp
    The 74,548 polygons are Tang and Werner (2023), "Global mining footprint
    mapped from high-resolution satellite imagery", not the Maus et al.
    global-scale mining polygons - Maus version 2 has 44,929 features. The
    path is the layout inside their supplementary archive, full-width colon
    and all.

Google Places API results, collected by the authors - manual
    {INCOMING}/africa-station-google-points/stations_with_google_api_points.csv

GADM https://gadm.org/ - auto (drafted)
    {DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg
    Derived from the GADM 3.6 levels GeoPackage with ISO_A3 and continent
    columns added, so it takes a processing rule as well as a download.

Other admin boundary lookups, compiled by the authors - manual
    {DATA}/admin_boundaries/ccg_country_codes.csv
    {DATA}/admin_boundaries/centroids/countries_iso3_code.csv
    {DATA}/admin_boundaries/country_codes.xlsx
    {DATA}/admin_boundaries/un_urban_population/un_pop_df.gpkg

OpenStreetMap Waterways for Africa, via the Africa Geoportal
https://africageoportal.maps.arcgis.com/home/item.html?id=82232d0415c04e7086414dff7eb1310f - auto (drafted)
    {INCOMING}/Africa_osm_rivers/OpenStreetMap_Waterways_for_Africa.geoparquet
    The africa_river_* and africa_network_* geoparquets that sit beside it in
    that folder are not inputs - ``africa_inland_waterways`` derives them from
    this extract.

Inland waterways and cost assumptions, compiled by the authors - manual
    {INCOMING}/IWW_ports/africa_IWW_ports.xlsx
    {INCOMING}/IWW_ports/edges_port_IWW_af.gpkg
    {INCOMING}/IWW_ports/hotosm_ssd_waterways.gpkg
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

7. Airport network. ``download_world_bank_global_airports`` fetches the World
   Bank point layer, but ``{DATA}/infrastructure/africa_airport_network.gpkg``
   is read for a ``nodes`` layer keyed on an ``Orig`` IATA column and an
   ``edges`` layer of routes between them. Building those two layers from the
   airport points plus a route table is the last mode-level gap.

8. PortWatch averages. ``download_portwatch_ports`` fetches the port point
   layer and the daily port activity table. ``ports_new_merge`` reads three
   tables of 2019-2024 averages - port calls, capacity called and turnaround
   time - which are per-port means over that daily table. A rule that groups
   the daily table by port and year range would replace three manual files,
   and needs the daily table's column names to be written.

9. Inland waterway steps. ``africa_inland_waterways`` now runs all three of
   its steps rather than the last one only, so the river networks it used to
   need supplied by hand are built from the waterways extract. The first two
   steps are slow, which is why they were switched off; snakemake skips them
   once their outputs exist, but a first run of this rule is a long one.

10. OSM snapshot. ``osm_extract_africa`` cuts the Africa extract out of a
   planet file rather than downloading a Geofabrik extract, because the
   Geofabrik dated extract the workflow was pinned to (2026-02-19) is past
   the 90 days for which Geofabrik serves dated extracts publicly. The OSMF
   planet bucket keeps every weekly snapshot indefinitely, so the pin moved
   to the nearest planet snapshot at or before that date, 2026-02-16, and
   lives in ``config.json`` as ``osm_snapshot``. Planet files are cut on
   Mondays, so an arbitrary date cannot be matched exactly.

11. Rebuilding the rail network. ``download_africa_rail_network`` takes the
   published network out of the trg-rail repository at a pinned commit, which
   is the right thing to do today. Porting that repository's build so the
   workflow could rebuild the network itself is scoped in
   ``spikes/rail_network_port/README.md``, with a working prototype of its
   first stage. In short: SedonaDB and igraph can replace PostGIS and
   pgRouting, and the ported first stage reproduces every row count the
   original records, in 14 seconds against 9 minutes on DuckDB.
   But the 24 country scripts that hold the research are a working notebook
   rather than a runnable build - 17 of them open with a deliberate syntax
   error to stop anyone running the whole file - and they are keyed on 4,503
   feature ids that are row numbers from a 2021 snkit run. So replaying the
   build on its own inputs is feasible; rebuilding from a current OSM extract
   needs those edits re-keyed to OSM ids first, and is a separate project.
   Until either is done, refreshing the network means bumping
   ``AFRICA_RAIL_COMMIT``.

12. Minerals rules. ``maps_global_maps``, ``maps_global_maps_transport``,
    ``plot_location_maps`` and ``plot_mine_ownership_maps`` read the outputs of
    the transport-critical-minerals workflow, including the BACI trade and
    mineral usage factor tables that ``location_maps.py`` reads through
    ``modify_mineral_usage_factors()``. They belong either behind an opt-in
    target or in that repository.

13. Country coverage of the HeiGIT download. ``AFRICA_ISO3`` below lists the
    54 African states, and ``download_heigit_road_surface`` fetches one file
    per country. HeiGIT does not publish a file for every country, so a
    missing country fails the rule and has to come out of the list; once the
    list is known to be complete, ``merge_heigit_data`` and
    ``roads_validation_comparison`` can take ``expand()`` over it as an input
    instead of reading whatever the folder happens to hold.
"""

# ---------------------------------------------------------------------------
# Natural Earth
# ---------------------------------------------------------------------------

# Natural Earth vector data, from the version-tagged GitHub mirror so that the
# sidecar files come down individually and the version is pinned.
NATURAL_EARTH_VERSION = "5.1.2"
NATURAL_EARTH_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v{version}/{folder}/{layer}"
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


# ---------------------------------------------------------------------------
# OpenStreetMap
# ---------------------------------------------------------------------------

# The OpenStreetMap Foundation's planet bucket. Every weekly snapshot since
# 2013 is kept, which is what makes a dated pin reproducible; Geofabrik only
# serves its dated extracts for 90 days.
OSM_PLANET_URL = (
    "https://osm-planet-eu-central-1.s3.eu-central-1.amazonaws.com/planet/pbf"
)

GEOFABRIK_URL = "https://download.geofabrik.de"


rule download_osm_planet:
    """Fetch one weekly OSM planet snapshot, and check it against its md5.

    Roughly 90GB, and the md5 check reads all of it again. Snakemake will not
    re-fetch it once it is on disk, but the first run of this rule is a long
    one, and ``osm_extract_africa`` is the only thing that reads it.
    """
    output:
        planet=f"{INCOMING}/osm/planet-{{snapshot}}.osm.pbf",
    params:
        # Snapshot dates are yymmdd; the bucket is foldered by full year.
        url=lambda wildcards: f"{OSM_PLANET_URL}/20{wildcards.snapshot[:2]}/planet-{wildcards.snapshot}.osm.pbf",
    shell:
        """
        mkdir -p "$(dirname "{output.planet}")"
        curl -fsSL "{params.url}" -o "{output.planet}"
        curl -fsSL "{params.url}.md5" -o "{output.planet}.md5"
        (cd "$(dirname "{output.planet}")" \
            && md5sum -c "$(basename "{output.planet}").md5")
        """


rule africa_clip_polygon:
    """Dissolve the Natural Earth countries into one Africa clip polygon."""
    input:
        script=f"{PREPROCESS}/africa_extent.py",
        countries=BASEMAP_COUNTRIES,
    output:
        polygon=f"{INCOMING}/osm/africa.geojson",
    shell:
        """
        python "{input.script}" \
            --countries "{input.countries}" \
            --output-polygon "{output.polygon}"
        """


rule osm_extract_africa:
    """Cut the Africa extract out of the planet file.

    This replaces the Geofabrik africa extract the workflow used to be pinned
    to - see EXTENSION POINTS. osmium needs a good deal of scratch space and
    reads the whole planet file, so expect this to take a while.
    """
    input:
        planet=f"{INCOMING}/osm/planet-{{snapshot}}.osm.pbf",
        polygon=f"{INCOMING}/osm/africa.geojson",
    output:
        pbf=f"{INCOMING}/osm/africa-{{snapshot}}.osm.pbf",
    shell:
        """
        osmium extract \
            --polygon "{input.polygon}" \
            --strategy complete_ways \
            --overwrite \
            --output "{output.pbf}" \
            "{input.planet}"
        """


rule download_geofabrik_egypt_shapefiles:
    """Egypt shapefile extract, for the Suez canal waterways.

    Geofabrik's "latest" extract moves with OSM, so this is not a pinned
    input: re-running the rule after the file has been deleted will not
    give the same waterways back.
    """
    output:
        waterways=f"{INCOMING}/egypt-latest-free.shp/gis_osm_waterways_free_1.shp",
    params:
        url=f"{GEOFABRIK_URL}/africa/egypt-latest-free.shp.zip",
        folder=f"{INCOMING}/egypt-latest-free.shp",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.url}" -o "{params.folder}/egypt-latest-free.shp.zip"
        unzip -o -q "{params.folder}/egypt-latest-free.shp.zip" -d "{params.folder}"
        rm "{params.folder}/egypt-latest-free.shp.zip"
        """


# ---------------------------------------------------------------------------
# rail network
# ---------------------------------------------------------------------------

# The published network from the trg-rail repository, pinned to a commit so
# that a re-run gives the same network back - see EXTENSION POINTS.
AFRICA_RAIL_REPO = "https://raw.githubusercontent.com/trg-rail/africa_rail_network"
AFRICA_RAIL_COMMIT = "0a58a7d18ebae554af1fc1054fcaf5e175a895cb"


rule download_africa_rail_network:
    """Fetch the trg-rail network and node layers.

    ``rail_data_cleaning`` reads the nodes as raw GeoJSON and the edges as the
    ``edges`` layer of a GeoPackage, so the edges are converted below.
    """
    output:
        edges=f"{INCOMING}/africa_rail_network/network_data/africa_rail_network.geojson",
        nodes=f"{INCOMING}/africa_rail_network/network_data/africa_rail_nodes.geojson",
    params:
        base=f"{AFRICA_RAIL_REPO}/{AFRICA_RAIL_COMMIT}/network",
    shell:
        """
        mkdir -p "$(dirname "{output.edges}")"
        curl -fsSL "{params.base}/africa_rail_network.geojson" -o "{output.edges}"
        curl -fsSL "{params.base}/africa_rail_nodes.geojson" -o "{output.nodes}"
        """


rule convert_africa_railways:
    """Write the rail edges out as the GeoPackage layer the workflow reads."""
    input:
        script=f"{PREPROCESS}/convert_vector_format.py",
        edges=f"{INCOMING}/africa_rail_network/network_data/africa_rail_network.geojson",
    output:
        railways=f"{INCOMING}/africa_rail_network/network_data/africa_railways.gpkg",
    shell:
        """
        python "{input.script}" \
            --input-file "{input.edges}" \
            --output-file "{output.railways}" \
            --output-layer edges
        """


# ---------------------------------------------------------------------------
# published research datasets
# ---------------------------------------------------------------------------

# Compilation of Geospatial Data (GIS) for the Mineral Industries and Related
# Infrastructure of Africa, USGS, doi:10.5066/P97EQWXP.
SCIENCEBASE_ITEM = "607611a9d34e018b3201cbbf"


rule download_usgs_africa_gis:
    """USGS Africa mineral industries and infrastructure GIS compilation.

    DRAFT: ScienceBase serves every file attached to an item as one zip from
    ``catalog/file/get/<item>``, but the layout inside that zip has not been
    checked from here. The three shapefiles below are declared as outputs so
    that snakemake fails loudly if they do not land where the workflow reads
    them - each one sits in a folder that is itself named ``*.shp``.
    """
    output:
        boundaries=AFRICA_ADM0,
        ports=USGS_PORTS,
        facilities=(
            f"{INCOMING}/Africa_GIS Supporting Data/a. Africa_GIS Shapefiles/"
            "AFR_Mineral_Facilities.shp/AFR_Mineral_Facilities.shp"
        ),
    params:
        url=f"https://www.sciencebase.gov/catalog/file/get/{SCIENCEBASE_ITEM}",
        folder=f"{INCOMING}/Africa_GIS Supporting Data",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.url}" -o "{params.folder}/sciencebase.zip"
        unzip -o -q "{params.folder}/sciencebase.zip" -d "{params.folder}"
        rm "{params.folder}/sciencebase.zip"
        """


rule download_african_development_corridors:
    """African Development Corridors Database 2022, from Dryad.

    DRAFT: the Dryad v2 API serves a dataset as one zip. The database is
    published as a GeoPackage and an ESRI file geodatabase alongside the
    master spreadsheet, so the GeoPackage should be in there under this name.
    """
    output:
        corridors=CORRIDOR_DB,
    params:
        url="https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.9kd51c5hw/download",
        folder=f"{INCOMING}/africa_corridor_developments",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.url}" -o "{params.folder}/dryad.zip"
        unzip -o -q -j "{params.folder}/dryad.zip" \
            "*AfricanDevelopmentCorridorDatabase2022.gpkg" -d "{params.folder}"
        rm "{params.folder}/dryad.zip"
        """


rule download_global_port_supply_chains:
    """Verschuur et al. port network and statistics, from Mendeley Data.

    DRAFT: Mendeley's public API lists a dataset's files with a download URL
    for each, so the rule asks for the listing and pulls the four files by
    name rather than guessing at file ids. The folder layout under
    ``Network`` and ``Port_statistics`` is the dataset's own.
    """
    output:
        nodes=f"{INCOMING}/Global port supply-chains/Network/nodes_maritime.gpkg",
        value=f"{INCOMING}/Global port supply-chains/Port_statistics/port_locations_value.csv",
        weight=f"{INCOMING}/Global port supply-chains/Port_statistics/port_locations_weight.csv",
        utilization=f"{INCOMING}/Global port supply-chains/Port_statistics/port_utilization.csv",
    params:
        api="https://data.mendeley.com/public-api/datasets/vzzy3b9gg4/files?folder_id=root&version=1",
        folder=f"{INCOMING}/Global port supply-chains",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.api}" -o "{params.folder}/files.json"
        for path in {output}; do
            name="$(basename "$path")"
            url="$(jq -r --arg name "$name" \
                '.[] | select(.filename == $name) | .content_details.download_url' \
                "{params.folder}/files.json")"
            test -n "$url" || {{ echo "No Mendeley file named $name"; exit 1; }}
            mkdir -p "$(dirname "$path")"
            curl -fsSL "$url" -o "$path"
        done
        rm "{params.folder}/files.json"
        """


rule download_global_mine_polygons:
    """Tang and Werner global mining footprint polygons, from Zenodo.

    DRAFT: the Zenodo API lists a record's files, so the rule takes whichever
    archive it offers rather than pinning a file name - the supplementary
    archive's name carries a full-width colon, which is awkward to quote.
    """
    output:
        polygons=(
            f"{INCOMING}/Supplementary 1：mine area polygons/"
            "74548 mine polygons/74548_projected.shp"
        ),
    params:
        api="https://zenodo.org/api/records/7894216",
        folder=INCOMING,
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.api}" -o "{params.folder}/zenodo.json"
        jq -r '.files[] | select(.key | endswith(".zip")) | .links.self' \
            "{params.folder}/zenodo.json" \
        | while read -r url; do
            curl -fsSL "$url" -o "{params.folder}/mine_polygons.zip"
            unzip -o -q "{params.folder}/mine_polygons.zip" -d "{params.folder}"
            rm "{params.folder}/mine_polygons.zip"
        done
        rm "{params.folder}/zenodo.json"
        """


# ---------------------------------------------------------------------------
# ports
# ---------------------------------------------------------------------------

# PortWatch is an ArcGIS Hub site, so its datasets come through the Hub
# download API. The item ids are the ones in the dataset page URLs.
PORTWATCH_DOWNLOAD = "https://portwatch.imf.org/api/download/v1/items"
PORTWATCH_PORTS_ITEM = "acc668d199d1472abaaf2467133d4ca4"
PORTWATCH_DAILY_ITEM = "959214444157458aad969389b3ebe1a0"


rule download_portwatch_ports:
    """IMF PortWatch port locations and daily port activity.

    DRAFT: the Hub download API builds an export on request and answers with
    a redirect to it, which curl follows. The daily activity table is large.
    The three 2019-2024 average tables that ``ports_new_merge`` reads are
    aggregates of the daily table rather than downloads - see EXTENSION
    POINTS - so this rule stops at the two published datasets.
    """
    output:
        ports=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/Ports.shp",
        daily=f"{INCOMING}/Global port supply-chains/Ports Updated 2025/daily_port_activity.csv",
    params:
        ports_url=f"{PORTWATCH_DOWNLOAD}/{PORTWATCH_PORTS_ITEM}/shapefile?layers=0",
        daily_url=f"{PORTWATCH_DOWNLOAD}/{PORTWATCH_DAILY_ITEM}/csv?layers=0",
        folder=f"{INCOMING}/Global port supply-chains/Ports Updated 2025",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.ports_url}" -o "{params.folder}/ports.zip"
        unzip -o -q -j "{params.folder}/ports.zip" -d "{params.folder}"
        rm "{params.folder}/ports.zip"
        curl -fsSL "{params.daily_url}" -o "{output.daily}"
        """


# ---------------------------------------------------------------------------
# airports
# ---------------------------------------------------------------------------


rule download_ourairports:
    """The OurAirports airport table, rebuilt daily and served from GitHub."""
    output:
        airports=f"{INCOMING}/airports/airports.csv",
    params:
        url="https://davidmegginson.github.io/ourairports-data/airports.csv",
    shell:
        """
        mkdir -p "$(dirname "{output.airports}")"
        curl -fsSL "{params.url}" -o "{output.airports}"
        """


rule ourairports_africa_layer:
    """Turn the OurAirports table into the African airport point layer."""
    input:
        script=f"{PREPROCESS}/ourairports_africa.py",
        airports=f"{INCOMING}/airports/airports.csv",
    output:
        airports=f"{INCOMING}/airports/africa_airports_ourairport.gpkg",
    shell:
        """
        python "{input.script}" \
            --airports "{input.airports}" \
            --output-airports "{output.airports}"
        """


rule download_world_bank_global_airports:
    """World Bank Global Airports point layer, via its HDX mirror.

    DRAFT: HDX runs CKAN, whose API lists a dataset's resources with a URL
    for each, which is steadier than the World Bank catalogue's own download
    endpoint. This gives the airport points, not the node-and-edge network
    the workflow reads - see EXTENSION POINTS.
    """
    output:
        airports=f"{DATA}/infrastructure/world_bank_global_airports.zip",
    params:
        api="https://data.humdata.org/api/3/action/package_show?id=global-airports",
    shell:
        """
        mkdir -p "$(dirname "{output.airports}")"
        curl -fsSL "{params.api}" -o "{output.airports}.json"
        url="$(jq -r '.result.resources[0].url' "{output.airports}.json")"
        test -n "$url" || {{ echo "No HDX resource for global-airports"; exit 1; }}
        curl -fsSL "$url" -o "{output.airports}"
        rm "{output.airports}.json"
        """


# ---------------------------------------------------------------------------
# road surface validation
# ---------------------------------------------------------------------------

# HeiGIT publish one GeoPackage per country on HDX, served from ohsome.
HEIGIT_URL = "https://downloads.ohsome.org/hdx/mapillary_road_surface"

# The 54 African states. Not every one of them has a HeiGIT file - see
# EXTENSION POINTS.
AFRICA_ISO3 = [
    "AGO", "BDI", "BEN", "BFA", "BWA", "CAF", "CIV", "CMR", "COD", "COG",
    "COM", "CPV", "DJI", "DZA", "EGY", "ERI", "ETH", "GAB", "GHA", "GIN",
    "GMB", "GNB", "GNQ", "KEN", "LBR", "LBY", "LSO", "MAR", "MDG", "MLI",
    "MOZ", "MRT", "MUS", "MWI", "NAM", "NER", "NGA", "RWA", "SDN", "SEN",
    "SLE", "SOM", "SSD", "STP", "SWZ", "SYC", "TCD", "TGO", "TUN", "TZA",
    "UGA", "ZAF", "ZMB", "ZWE",
]


rule download_heigit_road_surface:
    """One country's HeiGIT road surface GeoPackage.

    DRAFT: the URL pattern is the one HDX links to for each country's
    GeoPackage resource, with the ISO3 code lowercased.
    """
    output:
        surfaces=f"{INCOMING}/Randhawaetal_2025_Locations/heigit_{{iso3}}_roadsurface_lines.gpkg",
    params:
        url=lambda wildcards: f"{HEIGIT_URL}/heigit_{wildcards.iso3.lower()}_roadsurface_lines.gpkg",
    shell:
        """
        mkdir -p "$(dirname "{output.surfaces}")"
        curl -fsSL "{params.url}" -o "{output.surfaces}"
        """


rule download_heigit_road_surface_all:
    """Fetch every African country's HeiGIT road surface GeoPackage."""
    input:
        expand(
            f"{INCOMING}/Randhawaetal_2025_Locations/heigit_{{iso3}}_roadsurface_lines.gpkg",
            iso3=[iso3.lower() for iso3 in AFRICA_ISO3],
        ),


# ---------------------------------------------------------------------------
# admin boundaries and waterways
# ---------------------------------------------------------------------------


rule download_gadm:
    """GADM 3.6 administrative areas, all levels in one GeoPackage.

    DRAFT: GADM's own download pages link to the UC Davis mirror; this is the
    world-level file rather than the per-country ones.
    """
    output:
        levels=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels.gpkg",
    params:
        url="https://geodata.ucdavis.edu/gadm/gadm3.6/gadm36_levels_gpkg.zip",
        folder=f"{DATA}/admin_boundaries/gadm36_levels_gpkg",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.url}" -o "{params.folder}/gadm36_levels_gpkg.zip"
        unzip -o -q -j "{params.folder}/gadm36_levels_gpkg.zip" -d "{params.folder}"
        rm "{params.folder}/gadm36_levels_gpkg.zip"
        """


rule gadm_continents:
    """Add the ISO_A3 and continent columns the validation scripts select on."""
    input:
        script=f"{PREPROCESS}/gadm_continents.py",
        levels=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels.gpkg",
    output:
        boundaries=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg",
    shell:
        """
        python "{input.script}" \
            --gadm-levels "{input.levels}" \
            --output-boundaries "{output.boundaries}"
        """


# OpenStreetMap Waterways for Africa, a hosted feature layer on the Africa
# Geoportal. Esri refresh it from OSM, so it is not a pinned input.
AFRICA_GEOPORTAL_DOWNLOAD = "https://www.africageoportal.com/api/download/v1/items"
AFRICA_WATERWAYS_ITEM = "82232d0415c04e7086414dff7eb1310f"


rule download_osm_waterways_africa:
    """OpenStreetMap Waterways for Africa, from the Africa Geoportal.

    DRAFT: this is a hosted feature layer rather than a file, so the download
    goes through the Hub export API, which builds the export on request and
    redirects to it. A large layer can take a couple of attempts while the
    export is still being cut.
    """
    output:
        waterways=f"{INCOMING}/Africa_osm_rivers/OpenStreetMap_Waterways_for_Africa.geojson",
    params:
        url=f"{AFRICA_GEOPORTAL_DOWNLOAD}/{AFRICA_WATERWAYS_ITEM}/geojson?layers=0",
    shell:
        """
        mkdir -p "$(dirname "{output.waterways}")"
        curl -fsSL "{params.url}" -o "{output.waterways}"
        """


rule convert_osm_waterways_africa:
    """Write the waterways out as the geoparquet the workflow reads."""
    input:
        script=f"{PREPROCESS}/convert_vector_format.py",
        waterways=f"{INCOMING}/Africa_osm_rivers/OpenStreetMap_Waterways_for_Africa.geojson",
    output:
        waterways=f"{INCOMING}/Africa_osm_rivers/OpenStreetMap_Waterways_for_Africa.geoparquet",
    shell:
        """
        python "{input.script}" \
            --input-file "{input.waterways}" \
            --output-file "{output.waterways}"
        """
