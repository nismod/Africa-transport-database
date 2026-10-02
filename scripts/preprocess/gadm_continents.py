import click
import country_converter as coco
import geopandas as gpd


@click.command()
@click.option("--gadm-levels", required=True, type=click.Path(exists=True))
@click.option("--output-boundaries", required=True, type=click.Path())
@click.option("--layer", default="level0", show_default=True)
def main(gadm_levels, output_boundaries, layer):
    """Add the ISO_A3 and CONTINENT columns the validation scripts look for

    GADM names its country column GID_0; ``heigit_check`` and
    ``roads_validation_comparison`` both select on ISO_A3. The continent is
    looked up from the ISO3 code, which is where the "_continents" in the file
    name comes from.
    """
    boundaries = gpd.read_file(gadm_levels, layer=layer)
    boundaries = boundaries.rename(columns={"GID_0": "ISO_A3", "NAME_0": "NAME"})
    boundaries["CONTINENT"] = coco.CountryConverter().convert(
        names=boundaries["ISO_A3"].values.tolist(), src="ISO3", to="continent"
    )
    boundaries.to_file(output_boundaries, driver="GPKG")


if __name__ == "__main__":
    main()
