import click
import geopandas as gpd
import pandas as pd
from tqdm import tqdm

tqdm.pandas()


def get_road_condition(row: pd.Series) -> tuple[str, str]:
    """
    Given a series with 'surface' and 'highway' labels, infer road:
        - paved status (boolean)
        - surface category from {'asphalt', 'gravel', 'concrete'}

    N.B. There are several surface categories not considered in this function.
    Here are the major roads recorded for OSM in Tanzania as of June 2022:

    (Pdb) df.tag_surface.value_counts()
    unpaved           2521
    paved             2033
    asphalt           1355
    ground             108
    gravel              38
    compacted           23
    dirt                19
    concrete             5
    concrete:lanes       4
    sand                 2
    fine_gravel          1

    Args:
        row: Must have surface (nullable) and highway attributes.

    Returns:
        Boolean paved status and surface category string
    """

    if not row.tag_surface:
        if row.tag_highway in {"motorway", "trunk", "primary"}:
            return True, "asphalt"
        else:
            return False, "gravel"
    elif row.tag_surface == "paved":
        return True, "asphalt"
    elif row.tag_surface == "unpaved":
        return False, "gravel"
    elif row.tag_surface in {"asphalt", "concrete"}:
        return True, row.tag_surface
    else:
        return False, row.tag_surface


def get_asset_type(x):
    if x["tag_bridge"] == "yes":
        return "road_bridge"
    elif x["paved"] == True:
        return "road_paved"
    else:
        return "road_unpaved"


@click.command()
@click.option("--edges", required=True, type=click.Path(exists=True))
@click.option("--output-edges", required=True, type=click.Path())
@click.option("--output-network", required=True, type=click.Path())
def main(edges, output_edges, output_network):
    """Infer paved status, surface material and asset type for road edges"""
    edges = gpd.read_parquet(edges)

    # infer paved status and material type from 'surface' column
    edges["paved_material"] = edges.apply(lambda x: get_road_condition(x), axis=1)
    # unpack 2 item iterable into two columns
    edges[["paved", "material"]] = edges["paved_material"].apply(pd.Series)

    # drop the now redundant columns
    edges.drop(["paved_material"], axis=1, inplace=True)
    edges["asset_type"] = edges.apply(lambda x: get_asset_type(x), axis=1)

    edges.to_parquet(output_edges)
    edges.to_file(output_network, layer="edges", driver="GPKG")


if __name__ == "__main__":
    main()
