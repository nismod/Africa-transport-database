import click

"""Road network risks and adaptation maps"""


import matplotlib.pyplot as plt
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    plot_africa_basemap,
    save_fig,
)

tqdm.pandas()


@click.command()
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--ccg-countries", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(countries, lakes, ccg_countries, output_figure):
    """Plot the Africa basemap on its own"""
    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )
    plot_africa_basemap(ax_plots, countries, lakes, ccg_countries)
    plt.tight_layout()
    save_fig(output_figure)
    plt.close()


if __name__ == "__main__":
    main()
