import click
import quackosm as qo
from tqdm import tqdm

tqdm.pandas()


@click.command()
@click.option("--pbf", required=True, type=click.Path(exists=True))
@click.option("--output-parquet", required=True, type=click.Path())
def main(pbf, output_parquet):
    """Extract airport terminal footprints from an OpenStreetMap PBF extract"""
    qo.convert_pbf_to_parquet(
        pbf_path=pbf,
        result_file_path=output_parquet,
        tags_filter={
            "aeroway": ["terminal"],
            "building": ["terminal", "transportation"],
        },
        explode_tags=False,
    )


if __name__ == "__main__":
    main()
