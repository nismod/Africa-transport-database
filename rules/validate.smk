"""Compare the database against reference datasets.

Matching rail facilities to independently mapped locations, and comparing road
surface and length against the HeiGIT road surface dataset, the CIA factbook
and other published figures. The charts that report those comparisons live here
too, next to the rules that produce the numbers behind them, so the scripts
these rules run come from ``scripts/preprocess``, ``scripts/plot`` and
``scripts/maps and stats`` alike.
"""


# ---------------------------------------------------------------------------
# rail facilities against independently mapped locations
# ---------------------------------------------------------------------------


rule google_api_matches:
    """Match rail facilities against mines, ports, airports and Google places."""
    input:
        script=f"{PREPROCESS}/google_api_matches.py",
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
        """
        python {input.script}
        """


rule plot_rail_facility_proximity:
    """Histogram of rail facility distances to matched reference locations."""
    input:
        script=f"{PLOT}/rail_location_proximity_plot.py",
        matches=f"{RESULTS}/africa-station-google-points/location_proximity_final.gpkg",
    output:
        figure=f"{FIGURES}/rail_facility_proximity.png",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# road surface and length against the HeiGIT dataset
# ---------------------------------------------------------------------------


rule merge_heigit_data:
    """Merge the per-country HeiGIT road surface GeoPackages into one file."""
    input:
        script=f"{PREPROCESS}/merge_heigit_data.py",
        # The script reads all heigit_*_roadsurface_lines.gpkg in this folder.
        heigit_folder=f"{INCOMING}/Randhawaetal_2025_Locations",
    output:
        merged=f"{DATA}/infrastructure/validation_file_merge.geoparquet",
    shell:
        """
        python {input.script}
        """


rule heigit_check:
    """Compare database road surfaces against the merged HeiGIT dataset."""
    input:
        script=f"{PREPROCESS}/heigit_check.py",
        database_lines=f"{DATA}/infrastructure/africa_roads_edges.geoparquet",
        heigit_lines=f"{DATA}/infrastructure/validation_file_merge.geoparquet",
        boundaries=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg",
    output:
        merged=f"{RESULTS}/merged_validation_datasets.parquet",
        pivot=f"{RESULTS}/merged_validation_datasets.csv",
        pivot_corrected=f"{RESULTS}/merged_validation_datasets_corrected.csv",
    shell:
        """
        python {input.script}
        """


rule roads_validation_comparison:
    """Clip database and HeiGIT roads by country and compare paved lengths."""
    input:
        script=f"{PREPROCESS}/roads_validation_comparison.py",
        database_lines=f"{DATA}/infrastructure/africa_roads_edges_FINAL_last.geoparquet",
        boundaries=f"{DATA}/admin_boundaries/gadm36_levels_gpkg/gadm36_levels_continents.gpkg",
        # One HeiGIT file per country is read, if present, from this folder.
        heigit_folder=f"{INCOMING}/Randhawaetal_2025_Locations",
    output:
        merged=f"{DATA}/infrastructure/merged_validation_datasets.parquet",
        pivot=f"{DATA}/infrastructure/merged_validation_datasets.csv",
        counts=f"{DATA}/infrastructure/merged_validation_datasets_counts.csv",
    shell:
        """
        python {input.script}
        """


rule plot_heigit_bar_charts:
    """Bar charts comparing this database against HeiGIT and rail references."""
    input:
        script=f"{PLOT}/heigit_bar_charts.py",
        validation=f"{RESULTS}/merged_validation_datasets_corrected.csv",
        country_codes=f"{DATA}/admin_boundaries/country_codes.xlsx",
        rails=f"{RESULTS}/rails.xlsx",
    output:
        comparison=f"{FIGURES}/heigit_comparison.png",
        differences_csv=f"{RESULTS}/merged_validation_datasets_differences.csv",
        differences=f"{FIGURES}/heigit_difference.png",
        rail_comparisons=f"{FIGURES}/rail_comparisons.png",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# port counts against the CIA factbook
# ---------------------------------------------------------------------------


rule maps_validation:
    """Cluster-compare the maritime port database against CIA port counts."""
    input:
        script=f"{MAPS_AND_STATS}/validation.py",
        ports=f"{DATA}/Validation sets/ports.csv",
    output:
        clusters=f"{DATA}/Validation sets/port_cluster_comparison_k3.csv",
    shell:
        """
        python {input.script}
        """


# ---------------------------------------------------------------------------
# multi-modal link lengths
# ---------------------------------------------------------------------------


rule plot_multi_modal_proximity:
    """Histogram of multi-modal link lengths by connection type."""
    input:
        script=f"{PLOT}/multi_proximity_plot.py",
        multimodal=f"{DATA}/infrastructure/africa_multimodal.gpkg",
    output:
        figure=f"{FIGURES}/multi_modal_proximity.png",
    shell:
        """
        python {input.script}
        """
