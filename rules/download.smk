"""Fetch the incoming data.

Rules in this file largely fetch and process from online sources.

Two rules are placeholders for manual download.

Other sources are yet to be incorporated:

Open-gira road network https://github.com/nismod/open-gira
- {INCOMING}/africa_roads/
  - edges_with_topology.geoparquet
  - nodes_with_topology.geoparquet
- TODO - run open-gira (or equivalent) network process from OSM Africa

Rail corridor projects, digitised by the authors from AU-PIDA
https://www.au-pida.org/pida-projects/ and the corridors database
- {INCOMING}/africa_corridor_developments/
  - 17D.1.gpkg
  - Dar_es.gpkg
  - Team.gpkg
  - eastafrica_rail.gpkg
  - guinea_lines.gpkg
  - guinea_rail.shp
  - kinsasha_rail.gpkg
  - tanzania_sgr_lines.gpkg
  - togo_lines.gpkg
- TODO - check where these come from, perhaps prepare an incoming bundle for
  hard-to-access files

Google Places API results, collected by the authors - manual
- {INCOMING}/africa-station-google-points/stations_with_google_api_points.csv
- TODO access

Other admin boundary lookups
- {INCOMING}/admin_boundaries/
  - country_codes.csv
  - centroids/countries_iso3_code.csv
  - country_codes.xlsx
  - un_urban_population/un_pop_df.gpkg
- TODO access

Port utilization
- {INCOMING}/verschuur_2022_global_ports/Port_statistics/port_utilization.csv
- {DATA}/port_statistics/port_utilization.csv
- TODO deduplicate and access

Inland waterways and cost assumptions
- {INCOMING}/IWW_ports/africa_IWW_ports.xlsx
- {INCOMING}/IWW_ports/edges_port_IWW_af.gpkg
- {INCOMING}/IWW_ports/hotosm_ssd_waterways.gpkg
- {INCOMING}/Lobito_corridor.xlsx {INCOMING}/Rail_Costs.xlsx
- {INCOMING}/Roads_Costs.xlsx {INCOMING}/road_corridors.xlsx
- {INCOMING}/ports/africa_ports.gpkg {INCOMING}/ports/all_ports_matches.xlsx
- {INCOMING}/ports/edges_maritime_corrected.gpkg
- {INCOMING}/ports/nodes_maritime.gpkg
- {INCOMING}/egypt-latest-free.shp/suez_canal_ids.csv
- {DATA}/Validation sets/ports.csv {RESULTS}/rails.xlsx
- TODO access

To-do List
----------

- Road corridor extracts. ``road_adjustments`` reads five pairs of corridor
  geoparquets (Lobito, NS, TA, TSH, MDG) but only the Lobito pair has a rule.
  ``scripts/preprocess/road_corridors_NS_corridor.py`` is hard-coded to the
  Lobito spreadsheet and the AGO/COD/ZMB country filter. Generalising it to take
  a corridor name, spreadsheet and country list would turn
  ``road_corridors_ns_corridor`` into one wildcard rule covering all five, and
  is the single biggest gap in the DAG.

- Suez canal path mismatch. ``extract_suez`` writes
  ``{INCOMING}/egypt-latest-free.shp/suez_canal_network.gpkg`` but
  ``ports_data_cleaning`` reads ``{INCOMING}/suez_canal_network.gpkg``, so the
  two rules are not connected. One of the two paths needs to change.

- Rail project file naming. ``rail_data_cleaning`` writes the Conakry-Kankan
  project as ``conakry-kankan_railway.gpkg`` and then reads it back as
  ``guinea_lines.gpkg``. The two names need to agree before the second half of
  the script can use the first half's output.

- Google API matches path mismatch. ``google_api_matches`` reads
  ``{RESULTS}/africa-station-google-points/location_proximity_final.gpkg`` and
  writes
  ``{INCOMING}/africa-station-google-points/location_proximity_final.gpkg``, so
  it cannot be re-run from its own output and does not connect to
  ``plot_rail_facility_proximity``, which reads the ``{RESULTS}`` copy.

- Road network file extensions. ``road_connectivity`` reads
  ``{INCOMING}/africa_roads/*_with_topology.gpq`` while
  ``road_corridors_ns_corridor`` reads ``*_with_topology.geoparquet``. These are
  the same open-gira layers under two extensions.

- Port utilisation location. ``port_cargo_attributes`` reads
   ``{DATA}/port_statistics/port_utilization.csv`` and ``economic`` reads
   ``{INCOMING}/verschuur_2022_global_ports/Port_statistics/port_utilization.csv``.

- Airport network. ``download_world_bank_global_airports`` fetches the World
  Bank point layer, but ``{DATA}/infrastructure/africa_airport_network.gpkg`` is
  read for a ``nodes`` layer keyed on an ``Orig`` IATA column and an ``edges``
  layer of routes between them. Building those two layers from the airport
  points plus a route table is the last mode-level gap.

- PortWatch averages. ``download_portwatch_ports`` fetches the port point layer
  and the daily port activity table. ``ports_new_merge`` reads three tables of
  2019-2024 averages - port calls, capacity called and turnaround time - which
  are per-port means over that daily table. A rule that groups the daily table
  by port and year range would replace three manual files, and needs the daily
  table's column names to be written.

- Inland waterway steps. ``africa_inland_waterways`` now runs all three of its
  steps rather than the last one only, so the river networks it used to need
  supplied by hand are built from the waterways extract.

"""

# Natural Earth
# - {INCOMING}/natural_earth/
#   - ne_10m_admin_0_countries
#   - ne_10m_lakes
#   - ne_110m_admin_0_countries
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
            f"{INCOMING}/natural_earth/ne_10m_admin_0_countries",
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
            f"{INCOMING}/natural_earth/ne_10m_lakes",
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
            f"{INCOMING}/natural_earth/ne_110m_admin_0_countries",
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

rule download_natural_earth:
    """Download all
    """
    input:
        rules.download_natural_earth_countries.output,
        rules.download_natural_earth_lakes.output,
        rules.download_natural_earth_countries_110m.output,


# OpenStreetMap planet
# - {INCOMING}/osm/
#   - planet-{snapshot}.osm.pbf
#   - africa-{snapshot}.osm.pbf
# - Extract Africa from full planet
# - Every weekly planet snapshot since 2013 is kept; Geofabrik keeps 90 days.
OSM_PLANET_BUCKET = "osm-planet-eu-central-1"
GEOFABRIK_URL = "https://download.geofabrik.de"


rule download_osm_planet:
    """Fetch one weekly OSM planet snapshot, and check it against its md5.

    Roughly 90GB. Snakemake will not re-fetch it once it is on disk, but the
    first run of this rule is a long one, and ``osm_extract_africa`` is the only
    thing that reads it.
    """
    output:
        # planet=protected(f"{INCOMING}/osm/planet-{config['osm_snapshot']}.osm.pbf"),
    params:
        # snapshots are in the bucket folder /planet/pbf/{yyyy}
        # with filename planet-{yymmdd}.osm.pbf
        # we save to planet-{yyyymmdd}.osm.pbf i.e. {config['osm_snapshot']} wildcard should be yyyymmdd
        url=f"s3://{OSM_PLANET_BUCKET}/planet/pbf/{config['osm_snapshot'][:4]}/planet-{config['osm_snapshot'][2:]}.osm.pbf",
    shell:
        """
        mkdir -p $(dirname "{output.planet}")
        aws s3 --no-sign-request cp {params.url} "{output.planet}"
        aws s3 --no-sign-request cp "{params.url}.md5" "{output.planet}.md5"
        md5sum -c "{output.planet}"
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
    """
    input:
        planet=f"{INCOMING}/osm/planet-{config['osm_snapshot']}.osm.pbf",
        polygon=f"{INCOMING}/osm/africa.geojson",
    output:
        pbf=f"{INCOMING}/osm/africa-{config['osm_snapshot']}.osm.pbf",
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
    """OpenStreetMap Egypt, via Geofabrik https://download.geofabrik.de/

    - Download manually if Geofabrik is returning errors (it can be slow/down)
    - Consider - extract Egypt waterways from OSM Africa
    - see docs at http://download.geofabrik.de/osm-data-in-gis-formats-free.pdf
    - osmium tag filter: "w/waterway=river,stream,canal,drain"

    """
    output:
        waterways=f"{INCOMING}/osm/egypt-latest-free.shp/gis_osm_waterways_free_1.shp",
    params:
        url=f"{GEOFABRIK_URL}/africa/egypt-latest-free.shp.zip",
        folder=f"{INCOMING}/osm/egypt-latest-free.shp",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.url}" -o "{params.folder}/egypt-latest-free.shp.zip"
        unzip -o -q "{params.folder}/egypt-latest-free.shp.zip" -d "{params.folder}"
        rm "{params.folder}/egypt-latest-free.shp.zip"
        """


# trg-rail network
# Consider future work to reproduce edits and incorporate OSM updates
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
    """Write the rail edges out as GeoPackage."""
    input:
        edges=f"{INCOMING}/africa_rail_network/network_data/africa_rail_network.geojson",
    output:
        railways=f"{INCOMING}/africa_rail_network/network_data/africa_railways.gpkg",
    shell:
        """
        gdal vector convert "{input.edges}" "{output.railways}" --output-layer edges
        """


rule extract_usgs_africa_gis:
    """Compilation of Geospatial Data (GIS) for the Mineral Industries and
    Related Infrastructure of Africa, USGS https://doi.org/10.5066/P97EQWXP
    - {INCOMING}/usgs_2021_africa/a. Africa_GIS Shapefiles/
    - AFR_Political_ADM0_Boundaries.shp
    - AFR_Infra_Transport_Ports.shp
    - AFR_Mineral_Facilities.shp

    Manually download 'Africa_GIS Supporting Data.zip'

    from https://www.sciencebase.gov/catalog/item/607611a9d34e018b3201cbbf

    to {INCOMING}/usgs_2021_africa

    """
    input:
        zip=f"{INCOMING}/usgs_2021_africa/Africa_GIS Supporting Data.zip"
    output:
        boundaries=AFRICA_ADM0,
        ports=USGS_PORTS,
        facilities=(
            f"{INCOMING}/usgs_2021_africa/a. Africa_GIS Shapefiles/"
            "AFR_Mineral_Facilities.shp"
        ),
    params:
        folder=f"{INCOMING}/usgs_2021_africa",
    shell:
        """
        mkdir -p "{params.folder}"
        unzip -o -q "{params.folder}/Africa_GIS Supporting Data.zip" -d "{params.folder}"
        cd "{params.folder}/a. Africa_GIS Shapefiles"
        pwd
        find . -name "*.zip" -exec unzip -n {{}} \\;
        """


rule download_african_development_corridors:
    """African Development Corridors Database 2022, from Dryad.

    Manually download 'AfricanDevelopmentCorridorDatabase2022.gpkg.gpkg'

    from https://datadryad.org/dataset/doi:10.5061/dryad.9kd51c5hw

    to {INCOMING}/africa_corridor_developments/AfricanDevelopmentCorridorDatabase2022.gpkg
    """
    output:
        corridors=CORRIDOR_DB,
    params:
        url="https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.9kd51c5hw/download",
        folder=f"{INCOMING}/africa_corridor_developments",
    shell:
        """
        echo "Download manually from https://datadryad.org/dataset/doi:10.5061/dryad.9kd51c5hw to {output.corridors}"
        """


rule download_global_port_supply_chains:
    """Verschuur et al. 2022 port network and statistics, from Mendeley Data.
    https://doi.org/10.17632/vzzy3b9gg4.1

    Mendeley's dataset metadata includes a download URL for each published file,
    so the rule pulls the three available files by name.

    The folder layout under ``Network`` and ``Port_statistics`` is the dataset's
    own.

    TODO: the utilization table is not published there and mustbe provided
    separately.
    """
    output:
        nodes=f"{INCOMING}/verschuur_2022_global_ports/Network/nodes_maritime.gpkg",
        value=f"{INCOMING}/verschuur_2022_global_ports/Port_statistics/port_locations_value.csv",
        weight=f"{INCOMING}/verschuur_2022_global_ports/Port_statistics/port_locations_weight.csv",
        # utilization=f"{INCOMING}/verschuur_2022_global_ports/Port_statistics/port_utilizations.csv",
    params:
        api="https://data.mendeley.com/public-api/datasets/vzzy3b9gg4",
        folder=f"{INCOMING}/verschuur_2022_global_ports",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.api}" -o "{params.folder}/files.json"
        for path in {output}; do
            name="$(basename "$path")"
            url="$(jq -r --arg name "$name" \
                '.files[] | select(.filename == $name) | .content_details.download_url' \
                "{params.folder}/files.json")"
            test -n "$url" || {{ echo "No Mendeley file named $name"; exit 1; }}
            mkdir -p "$(dirname "$path")"
            curl -fsSL "$url" -o "$path"
        done
        rm "{params.folder}/files.json"
        """


rule download_global_mine_polygons:
    """Tang and Werner 2023 global mining footprint polygons, from Zenodo.

    https://doi.org/10.5281/zenodo.7894216
    """
    output:
        polygons=f"{INCOMING}/tang_2023_mines/74548_projected polygons.shp",
    params:
        record="7894216",
    shell:
        """
        dir="$(dirname "{output.polygons}")"
        cd "$dir"
        zenodo_get -w links.txt --record={params.record}
        wget --content-disposition -i links.txt
        """

# PortWatch is available through ArcGIS Hub site.
PORTWATCH_DOWNLOAD = "https://hub.arcgis.com/api/v3/datasets"
PORTWATCH_PORTS_ITEM = "acc668d199d1472abaaf2467133d4ca4_0"
PORTWATCH_DAILY_ITEM = "83b1bbc7b3354c5fb1f40673bb8f852e_0"

rule download_portwatch_ports:
    """IMF PortWatch port locations and daily port activity. https://portwatch.imf.org/

    PortWatch publishes the port point layer and a daily activity table; the three
    "average_2019-2024" tables are aggregates of the daily table.

    Download:
    - Ports.shp
    - daily_port_activity.csv

    TODO process:
    - port_calls_average_2019-2024.csv
    - port_capacity_called_average_2019-2024.csv
    - port_turn_around_time_average_2019-2024.csv
    """
    output:
        ports=f"{INCOMING}/portwatch/Ports.shp",
        daily=f"{INCOMING}/portwatch/daily_port_activity.csv",
    params:
        ports_url=f"{PORTWATCH_DOWNLOAD}/{PORTWATCH_PORTS_ITEM}/downloads/data?format=shp&spatialRefId=4326&where=1%3D1",
        daily_url=f"{PORTWATCH_DOWNLOAD}/{PORTWATCH_DAILY_ITEM}/downloads/data?format=csv&spatialRefId=4326&where=1%3D1",
        folder=f"{INCOMING}/portwatch",
    shell:
        """
        mkdir -p "{params.folder}"
        curl -fsSL "{params.ports_url}" -o "{params.folder}/ports.zip"
        unzip -o -q -j "{params.folder}/ports.zip" -d "{params.folder}"
        rm "{params.folder}/ports.zip"
        curl -fsSL "{params.daily_url}" -o "{output.daily}"
        """



rule download_ourairports:
    """OurAirports airport table

    Since 2021, hosted at GitHub - see https://ourairports.com/data/
    """
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
    """OurAirports conversion to Geopackage"""
    input:
        airports=f"{INCOMING}/airports/airports.csv",
    output:
        airports=f"{INCOMING}/airports/africa_airports_ourairport.gpkg",
    shell:
        """
        gdal vector pipeline \
            ! read "{input.airports}" \
            ! make-point --x longitude_deg --y latitude_deg --output-crs EPSG:4326 \
            ! filter --where "continent = 'AF'" \
            ! write "{output.airports}" --overwrite
        """


rule download_world_bank_global_airports:
    """World Bank Global Airports point layer

    https://datacatalog.worldbank.org/search/dataset/0038117/Global-Airports

    - Towards {DATA}/infrastructure/africa_airport_network.gpkg
    - TODO build network
    """
    output:
        csv=f"{INCOMING}/world_bank_2023_airports/airport_volume_airport_locations.csv",
        shp=f"{INCOMING}/world_bank_2023_airports/airport_flows.shp",
    shell:
        """
        dir="$(dirname "{output.csv}")"
        cd $dir
        wget https://datacatalogfiles.worldbank.org/ddh-published/0038117/2/DR0046411/airport_volume_airport_locations.csv
        wget https://datacatalogfiles.worldbank.org/ddh-published/0038117/2/DR0046413/airport_flows.zip
        unzip airport_flows.zip
        """


# HeiGIT publish one GeoPackage per country on HDX, served from ohsome.
HEIGIT_URL = "https://downloads.ohsome.org/hdx/mapillary_road_surface"

# The 54 African states
AFRICA_ISO3 = [
    "AGO", "BDI", "BEN", "BFA", "BWA", "CAF", "CIV", "CMR", "COD", "COG",
    "COM", "CPV", "DJI", "DZA", "EGY", "ERI", "ETH", "GAB", "GHA", "GIN",
    "GMB", "GNB", "GNQ", "KEN", "LBR", "LBY", "LSO", "MAR", "MDG", "MLI",
    "MOZ", "MRT", "MUS", "MWI", "NAM", "NER", "NGA", "RWA", "SDN", "SEN",
    "SLE", "SOM", "SSD", "STP", "SWZ", "SYC", "TCD", "TGO", "TUN", "TZA",
    "UGA", "ZAF", "ZMB", "ZWE",
]


rule download_heigit_road_surface:
    """HeiGIT road surface (Mapillary dataset, Randhawa et al. 2025)

    https://doi.org/10.1016/j.isprsjprs.2025.02.020
    """
    output:
        gpkg=f"{INCOMING}/randhawa_2025_road_surface/heigit_{{iso3}}_roadsurface_lines.gpkg",
    params:
        url=lambda wildcards: f"{HEIGIT_URL}/heigit_{wildcards.iso3.lower()}_roadsurface_lines.gpkg",
    shell:
        """
        mkdir -p "$(dirname "{output.gpkg}")"
        curl -fsSL "{params.url}" -o "{output.gpkg}"
        """


rule download_heigit_road_surface_all:
    """Fetch every African country's HeiGIT road surface GeoPackage."""
    input:
        expand(
            f"{INCOMING}/randhawa_2025_road_surface/heigit_{{iso3}}_roadsurface_lines.gpkg",
            iso3=[iso3.lower() for iso3 in AFRICA_ISO3],
        ),


rule download_gadm:
    """GADM 3.6 administrative areas, all levels in one GeoPackage.

    See https://gadm.org/
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
        levels=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels.gpkg",
    output:
        boundaries=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg",
    run:
        import country_converter as coco
        import geopandas as gpd
        boundaries = gpd.read_file(input.levels, layer="level0")
        boundaries = boundaries.rename(columns={"GID_0": "ISO_A3", "NAME_0": "NAME"})
        boundaries["CONTINENT"] = coco.CountryConverter().convert(
            names=boundaries["ISO_A3"].values.tolist(), src="ISO3", to="continent"
        )
        boundaries.to_file(output.boundaries, driver="GPKG")


# OpenStreetMap Waterways for Africa, a hosted feature layer on the Africa
# Geoportal. Esri refresh it from OSM, so it is not a pinned input.
AFRICA_GEOPORTAL_DOWNLOAD = "https://www.africageoportal.com/api/download/v1/items"
AFRICA_WATERWAYS_ITEM = "82232d0415c04e7086414dff7eb1310f"


rule download_osm_waterways_africa:
    """OpenStreetMap Waterways for Africa, from the Africa Geoportal.

    https://www.africageoportal.com/datasets/82232d0415c04e7086414dff7eb1310f_0/about

    TODO: convert from OSM pbf export
    """
    output:
        waterways=f"{INCOMING}/osm/osm_waterways_africa.geojson",
    params:
        url=f"{AFRICA_GEOPORTAL_DOWNLOAD}/{AFRICA_WATERWAYS_ITEM}/geojson?layers=0",
    shell:
        """
        curl -fsSL "{params.url}" -o "{output.waterways}"
        """


rule convert_osm_waterways_africa:
    """Write the waterways out as the geoparquet the workflow reads."""
    input:
        script=f"{PREPROCESS}/convert_vector_format.py",
        geojson=f"{INCOMING}/osm/osm_waterways_africa.geojson",
    output:
        geoparquet=f"{INCOMING}/osm/osm_waterways_africa.geoparquet",
    shell:
        """
        gdal vector convert {input.geojson} {output.geoparquet} --output-format Parquet
        """
