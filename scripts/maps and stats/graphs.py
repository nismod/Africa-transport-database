import click
import geopandas as gpd
import matplotlib.pyplot as plt
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    plot_africa_basemap,
    save_fig,
)

tqdm.pandas()


@click.command()
@click.option("--ccg-countries", required=True, type=click.Path(exists=True))
@click.option("--main-roads", required=True, type=click.Path(exists=True))
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(ccg_countries, main_roads, countries, lakes, output_figure):
    """Plot the main road network over the Africa basemap"""
    roads_df = gpd.read_file(
        main_roads,
        layer="edges",
    )

    ax_proj = get_projection(epsg=4326)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    plot_africa_basemap(ax_plots, countries, lakes, ccg_countries)
    roads_df.plot()
    plt.tight_layout()
    save_fig(output_figure)
    plt.close()


if __name__ == "__main__":
    main()
