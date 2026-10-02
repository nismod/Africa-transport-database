import click

"""Road network risks and adaptation maps"""


import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from tqdm import tqdm

from aftdb.plot.maps import (
    get_projection,
    plot_africa_basemap2,
    save_fig,
)

tqdm.pandas()


@click.command()
@click.option("--railways", required=True, type=click.Path(exists=True))
@click.option("--countries", required=True, type=click.Path(exists=True))
@click.option("--lakes", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(railways, countries, lakes, output_figure):
    """Map railway stations by facility type"""

    map_epsg = 4326
    ax_proj = get_projection(epsg=map_epsg)
    _fig, ax_plots = plt.subplots(
        1, 1, subplot_kw={"projection": ax_proj}, figsize=(12, 12), dpi=500
    )

    edges_df = gpd.read_file(
        railways,
        layer="edges",
    )
    nodes_df = gpd.read_file(
        railways,
        layer="nodes",
    )

    output_column = "facility"

    # Clean and standardize values
    nodes_df[output_column] = (
        nodes_df[output_column].astype(str).str.strip().str.title()
    )

    # Filter out bad values
    nodes_df = nodes_df[
        ~nodes_df[output_column].isin(["Not Known", "Unknown", "", "Nan", "None"])
    ]
    nodes_df = nodes_df[nodes_df[output_column].notna()]

    # Count occurrences
    facility_counts = nodes_df[output_column].value_counts().to_dict()

    # Convert to categorical and drop unused categories
    nodes_df[output_column] = pd.Categorical(nodes_df[output_column])
    nodes_df[output_column] = nodes_df[output_column].cat.remove_unused_categories()

    # Number of colors
    num_colors = len(nodes_df[output_column].unique())
    print("Number of facilities:", num_colors)

    # Build colormap
    cmap = plt.get_cmap("hsv", num_colors)
    custom_cmap = ListedColormap([cmap(i) for i in range(num_colors)])

    # Plot base
    bold_font = font_manager.FontProperties(weight="bold", size=14)
    ax = plot_africa_basemap2(ax_plots, countries, lakes)

    # Plot edges
    edges_df.plot(ax=ax, zorder=3, color="black", linewidth=1)

    # Plot nodes
    nodes_df.plot(
        ax=ax,
        zorder=5,
        column=output_column,
        cmap=custom_cmap,
        markersize=25,
        legend=True,
        legend_kwds={
            "title": "Railway Node Facility Type",
            "title_fontproperties": bold_font,
            "fontsize": 10,
            "loc": "lower left",
            "fancybox": True,
            "frameon": True,
            "edgecolor": "black",
            "facecolor": "white",
            "ncol": 2,
        },
        missing_kwds={"color": "lightgrey", "linewidth": 1},
    )

    # Format legend labels to include counts
    legend = ax.get_legend()
    for text in legend.get_texts():
        label = text.get_text()
        count = facility_counts.get(label.lower().title(), 0)
        text.set_text(f"{label} ({count})")

    # Save
    plt.tight_layout()
    save_fig(output_figure)


if __name__ == "__main__":
    main()
