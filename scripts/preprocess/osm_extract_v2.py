import os

import quackosm as qo
from tqdm import tqdm

from aftdb.utils import load_config

tqdm.pandas()


def main(config):
    incoming_data_path = config["paths"]["incoming_data"]
    in_path = os.path.join(incoming_data_path, "osm", "africa-260219.osm.pbf")
    out_path = os.path.join(
        incoming_data_path, "infrastructure", "africa_osm_airports_terminals.parquet"
    )

    qo.convert_pbf_to_parquet(
        pbf_path=in_path,
        result_file_path=out_path,
        tags_filter={
            "aeroway": ["terminal"],
            "building": ["terminal", "transportation"],
        },
        explode_tags=False,
    )


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
