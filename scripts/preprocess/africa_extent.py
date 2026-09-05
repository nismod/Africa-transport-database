import click
import geopandas as gpd

# Natural Earth files Mauritius and the Seychelles under "Seven seas (open
# ocean)" rather than Africa, so selecting on CONTINENT alone loses two
# African states that the Geofabrik africa extract has always included.
ISLAND_STATES = "MUS,SYC"


@click.command()
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--output-polygon", required=True, type=click.Path())
@click.option("--include-iso3", default=ISLAND_STATES, show_default=True)
@click.option("--simplify", default=0.01, show_default=True)
@click.option("--buffer", default=0.05, show_default=True)
def main(countries, output_polygon, include_iso3, simplify, buffer):
    """Write the Africa outline used to clip the OSM planet down to size

    Dissolves the Natural Earth country outlines for Africa into a single
    polygon. It is simplified and buffered because osmium walks every vertex
    of the clip polygon once per node in the planet file, and the full 10m
    outline is far more detail than a continent-sized cut needs.
    """
    boundaries = gpd.read_file(countries)
    island_states = [iso3.strip() for iso3 in include_iso3.split(",") if iso3.strip()]
    africa = boundaries[
        (boundaries["CONTINENT"] == "Africa")
        | (boundaries["ADM0_A3"].isin(island_states))
    ]
    if africa.empty:
        raise ValueError(f"No CONTINENT == 'Africa' features in '{countries}'")

    extent = africa.geometry.union_all().simplify(simplify).buffer(buffer)
    gpd.GeoDataFrame(geometry=[extent], crs=africa.crs).to_file(
        output_polygon, driver="GeoJSON"
    )


if __name__ == "__main__":
    main()
