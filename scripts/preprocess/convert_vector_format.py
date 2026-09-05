import click
import geopandas as gpd


@click.command()
@click.option("--input-file", required=True, type=click.Path(exists=True))
@click.option("--output-file", required=True, type=click.Path())
@click.option("--input-layer", default=None)
@click.option("--output-layer", default=None)
def main(input_file, output_file, input_layer, output_layer):
    """Read one vector file and write it out in another format

    Used by the download rules to turn what a source publishes into what the
    processing scripts read - a GeoJSON download into the GeoPackage layer or
    the geoparquet that the rest of the workflow expects.
    """
    if input_layer:
        df = gpd.read_file(input_file, layer=input_layer)
    else:
        df = gpd.read_file(input_file)

    if output_file.endswith((".geoparquet", ".parquet", ".gpq")):
        df.to_parquet(output_file)
    elif output_layer:
        df.to_file(output_file, layer=output_layer, driver="GPKG")
    else:
        df.to_file(output_file)


if __name__ == "__main__":
    main()
