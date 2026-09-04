import os

import geopandas as gpd
from tqdm import tqdm

from aftdb.utils import load_config

tqdm.pandas()

config = load_config()
incoming_data_path = config["paths"]["incoming_data"]
processed_data_path = config["paths"]["data"]


def main():

    processed_data_path = config["paths"]["data"]

    multi_df = gpd.read_file(
        os.path.join(processed_data_path, "infrastructure", "africa_multimodal.gpkg"),
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
        os.path.join(processed_data_path, "infrastructure", "africa_multimodal.gpkg"),
        layer="edges",
        driver="GPKG",
    )


if __name__ == "__main__":
    main()
