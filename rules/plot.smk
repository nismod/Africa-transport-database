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
        python "{input.script}" \
            --airports "{input.airports}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --output-figure "{output.figure}"
        """


rule plot_ports_and_iww:
    """Map maritime ports, inland ports and their routes."""
    input:
        script=f"{PLOT}/africa_maps_ports.py",
        maritime=f"{DATA}/infrastructure/africa_maritime_network.gpkg",
        iww=f"{DATA}/infrastructure/africa_iww_network.gpkg",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
        ccg_countries=COUNTRY_CODES,
    output:
        figure=f"{FIGURES}/IWW_and_ports.png",
    shell:
        """
        python "{input.script}" \
            --maritime "{input.maritime}" \
            --iww "{input.iww}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --ccg-countries "{input.ccg_countries}" \
            --output-figure "{output.figure}"
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
        python "{input.script}" \
            --maritime "{input.maritime}" \
            --iww "{input.iww}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --output-figure "{output.figure}"
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
        python "{input.script}" \
            --railways "{input.railways}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --output-figure "{output.figure}"
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
        python "{input.script}" \
            --railways "{input.railways}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --output-figure "{output.figure}"
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
        python "{input.script}" \
            --road-edges "{input.road_edges}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --output-figure "{output.figure}"
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
        python "{input.script}" \
            --road-edges "{input.road_edges}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --output-legend "{output.legend}" \
            --output-figure "{output.figure}"
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
        python "{input.script}" \
            --railways "{input.railways}" \
            --output-figure "{output.figure}"
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
        python "{input.script}" \
            --road-edges "{input.road_edges}" \
            --output-figure "{output.figure}"
        """


# ---------------------------------------------------------------------------
# scripts/maps and stats
# ---------------------------------------------------------------------------



rule maps_graphs_transport:
    """Plot the final road edges by corridor over the Africa basemap.
    """
    input:
        script=f"{MAPS_AND_STATS}/graphs_transport.py",
        road_edges=f"{DATA}/infrastructure/africa_roads_edges_FINAL.geoparquet",
        countries=BASEMAP_COUNTRIES,
        lakes=BASEMAP_LAKES,
        ccg_countries=COUNTRY_CODES,
    output:
        figure=f"{FIGURES}/roads_test.png",
    shell:
        """
        python "{input.script}" \
            --road-edges "{input.road_edges}" \
            --countries "{input.countries}" \
            --lakes "{input.lakes}" \
            --ccg-countries "{input.ccg_countries}" \
            --output-figure "{output.figure}"
        """

