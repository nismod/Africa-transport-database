import click

"""Road network risks and adaptation maps"""


import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from tqdm import tqdm

from aftdb.plot.maps import save_fig

tqdm.pandas()


@click.command()
@click.option("--railways", required=True, type=click.Path(exists=True))
@click.option("--output-figure", required=True, type=click.Path())
def main(railways, output_figure):
    """Stacked bar chart of railway length by country and status"""

    rail_df = gpd.read_file(
        railways,
        layer="edges",
    )

    rail_df["length_km"] = rail_df["length_m"] / 1000
    # Group the data by country and status, summing the length_m column
    grouped_data = (
        rail_df.groupby(["country", "status"])["length_km"].sum().reset_index()
    )

    # Pivot the data to prepare for stacked bar plot
    grouped_data["status"] = grouped_data["status"].str.capitalize()
    pivot_data = grouped_data.pivot(
        index="country", columns="status", values="length_km"
    ).fillna(0)
    # Preview the pivot table
    print(pivot_data.head())

    # Create a font property for bold text
    bold_font = font_manager.FontProperties(weight="bold")
    colormap = {
        "Abandoned": "#fddbcc",
        "Disused": "#f97306",
        "Razed": "#c1272d",
        "Suspended": "#801515",
        "Open": "#fbb03b",
        "Planned": "#d0e4f7",
        "Proposed": "#8c8ccf",
        "Construction": "#6a5acd",
        "Rehabilitation": "#800080",
        "Unknown": "#d3d3d3",
    }

    # Get color values from the colormap
    colors = [colormap[status] for status in pivot_data.columns]

    # Plot with colormap
    pivot_data.plot(kind="bar", stacked=True, figsize=(12, 8), color=colors)

    # Add labels and title
    plt.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.7)
    plt.title("Length by Country and Status")
    plt.xlabel("Country")
    plt.ylabel("Total Length (km)")
    # Adjust x-axis labels
    plt.xticks(rotation=30, ha="right")
    plt.legend(title="Status", title_fontproperties=bold_font, fontsize="small")

    plt.subplots_adjust(bottom=0.1)
    plt.tight_layout()

    save_fig(output_figure)


if __name__ == "__main__":
    main()
