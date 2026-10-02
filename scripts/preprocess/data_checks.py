import click
import geopandas as gpd
from tqdm import tqdm

tqdm.pandas()


@click.command()
@click.option("--multimodal", required=True, type=click.Path())
def main(multimodal):
    """Reduce the multi-modal edge layer to the published set of columns

    The GeoPackage is read and written back in place.
    """
    multi_df = gpd.read_file(
        multimodal,
        layer="edges",
    )

    multi_df = multi_df[
        [
            "id",
            "from_id",
            "to_id",
            "from_infra",
            "to_infra",
            "from_iso3",
            "to_iso3",
            "link_type",
            "length_m",
            "geometry",
        ]
    ]

    multi_df.to_file(
        multimodal,
        layer="edges",
        driver="GPKG",
    )


if __name__ == "__main__":
    main()
