"""Snakemake workflow for the African Transport Systems Database (AfTS-Db).

The workflow is split into stages, one rule file per stage:

    rules/download.smk  fetch the incoming data that can be fetched
    rules/process.smk   build the database from the incoming data
    rules/validate.smk  compare the database against reference datasets
    rules/plot.smk      map and chart the finished database

"""
import os

if not config:
    configfile: "config.json"


# normpath drops any "./" prefix, which snakemake warns about on every path
PATHS = {key: os.path.normpath(value) for key, value in config["paths"].items()}
INCOMING = PATHS["incoming_data"]
DATA = PATHS["data"]
FIGURES = PATHS["figures"]
RESULTS = PATHS["results"]

PREPROCESS = "scripts/preprocess"
PLOT = "scripts/plot"
MAPS_AND_STATS = "scripts/stats"

# Data layers read inside aftdb.plot.maps.plot_africa_basemap(),
# plot_africa_basemap2(), plot_global_basemap() and plot_ccg_basemap().
BASEMAP_COUNTRIES = f"{INCOMING}/natural_earth/ne_10m_admin_0_countries.shp"
BASEMAP_LAKES = f"{INCOMING}/natural_earth/ne_10m_lakes.shp"
COUNTRY_CODES = f"{INCOMING}/natural_earth/country_codes.csv"

# Frequently reused source datasets.
AFRICA_ADM0 = (
    f"{INCOMING}/usgs_2021_africa/a. Africa_GIS Shapefiles/"
    "AFR_Political_ADM0_Boundaries.shp"
)
USGS_PORTS = (
    f"{INCOMING}/usgs_2021_africa/a. Africa_GIS Shapefiles/"
    "AFR_Infra_Transport_Ports.shp"
)
CORRIDOR_DB = (
    f"{INCOMING}/africa_corridor_developments/"
    "AfricanDevelopmentCorridorDatabase2022.gpkg"
)
NE_110M_COUNTRIES = f"{INCOMING}/ports/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"

# The OpenStreetMap snapshot to build from, as yymmdd. Planet files are cut on
# Mondays, so this has to be a Monday - rules/download.smk cuts the Africa
# extract out of the planet file for this date.
OSM_SNAPSHOT = config.get("osm_snapshot", "260928")
OSM_AFRICA_PBF = f"{INCOMING}/osm/africa-{OSM_SNAPSHOT}.osm.pbf"


rule all:
    """Build the published multi-modal network layers."""
    input:
        f"{DATA}/infrastructure/africa_roads_network.gpkg",
        f"{DATA}/infrastructure/africa_railways_network.gpkg",
        f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        f"{DATA}/infrastructure/africa_iww_network.gpkg",
        f"{DATA}/infrastructure/africa_airport_network.gpkg",
        f"{DATA}/infrastructure/africa_multimodal.gpkg",


include: "rules/download.smk"
include: "rules/process.smk"
include: "rules/validate.smk"
include: "rules/plot.smk"


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
