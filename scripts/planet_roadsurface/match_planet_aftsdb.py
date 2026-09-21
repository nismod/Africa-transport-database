"""
Matches Planet road-surface data against AfTS-Db using OSM way id, not
a spatial join. Reports match rate and conflict rate for each country.

Reads the country files downloaded by download_planet_data.py.

Usage:
    python3 match_planet_aftsdb.py
Output:
    results/rerun_<date>.csv
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pyogrio
from config_utils import load_config

# ROOT = Path(__file__).resolve().parent.parent
# AFTSDB_PATH = ROOT / "data" / "aftsdb" / "africa_roads_network.gpkg"
# PLANET_RAW_DIR = ROOT / "data" / "planet_raw"
# OUT_DIR = ROOT / "results"

LINK_MAP = {
    "primary_link": "primary",
    "secondary_link": "secondary",
    "trunk_link": "trunk",
    "motorway_link": "motorway",
}


# def load_all_planet_files() -> list[str]:
#     return sorted(p.stem.split("_")[0] for p in PLANET_RAW_DIR.glob("*_planet_roadsurface.gpkg"))

def load_all_planet_files(planet_raw_dir: Path) -> list[str]:
    return sorted(
        p.stem.split("_")[0]
        for p in planet_raw_dir.glob("*_planet_roadsurface.gpkg")
    )


def process_country(
    iso3: str,
    afts_all: pd.DataFrame,
    planet_raw_dir: Path,
) -> dict | None:
    planet_path = planet_raw_dir / f"{iso3}_planet_roadsurface.gpkg"
    planet = pyogrio.read_dataframe(
        planet_path,
        read_geometry=False,
        columns=["osm_id", "osm_tags_highway", "osm_tags_surface"],
    )
    planet["osm_id_num"] = (
        planet["osm_id"]
        .str.replace("way/", "", regex=False)
        .astype("int64")
    )

    afts = afts_all[
        (afts_all["from_iso3"] == iso3)
        | (afts_all["to_iso3"] == iso3)
    ]
    afts_way_level = afts.drop_duplicates("osm_way_id")

    planet_ids = set(planet["osm_id_num"])
    afts_ids = set(afts_way_level["osm_way_id"].dropna())
    if not planet_ids or not afts_ids:
        return None

    overlap = planet_ids & afts_ids
    seg_counts = afts["osm_way_id"].value_counts()

    merged = planet.merge(
        afts_way_level[["osm_way_id", "tag_highway", "tag_surface"]],
        left_on="osm_id_num",
        right_on="osm_way_id",
        how="inner",
    )

    hw_norm = merged["osm_tags_highway"].replace(LINK_MAP)
    hw_mismatch_rate = (
        (hw_norm != merged["tag_highway"]).mean() * 100
        if len(merged)
        else float("nan")
    )

    both_present = (
        merged["osm_tags_surface"].notna()
        & merged["tag_surface"].notna()
    )
    genuine_mismatch = both_present & (
        merged["osm_tags_surface"] != merged["tag_surface"]
    )
    surface_conflict_rate = (
        genuine_mismatch.sum() / both_present.sum() * 100
        if both_present.sum()
        else 0.0
    )

    return {
        "iso3": iso3,
        "planet_records": len(planet_ids),
        "aftsdb_unique_roads": len(afts_ids),
        "overlap": len(overlap),
        "match_rate_planet": round(len(overlap) / len(planet_ids) * 100, 2),
        "match_rate_aftsdb": round(len(overlap) / len(afts_ids) * 100, 2),
        "avg_segments": round(seg_counts.mean(), 2),
        "highway_mismatch_pct": round(hw_mismatch_rate, 2),
        "surface_conflict_pct": round(surface_conflict_rate, 2),
    }


def main(config):
    incoming_data_path = config["paths"]["incoming_data"]
    processed_data_path = config["paths"]["data"]

    aftsdb_path = (
        incoming_data_path / "aftsdb" / "africa_roads_network.gpkg"
    )
    planet_raw_dir = incoming_data_path / "planet_raw"
    out_dir = processed_data_path / "planet_roadsurface"

    print("loading AfTS-Db edges (whole continent, filter per country in memory)...")
    afts_all = pyogrio.read_dataframe(
        aftsdb_path,
        layer="edges",
        read_geometry=False,
        columns=[
            "from_iso3",
            "to_iso3",
            "osm_way_id",
            "tag_highway",
            "tag_surface",
        ],
    )
    afts_all["osm_way_id"] = afts_all["osm_way_id"].astype("Int64")
    print(f"  {len(afts_all)} edges")

    countries = load_all_planet_files(planet_raw_dir)
    print(f"found {len(countries)} country files")

    rows = []
    for iso3 in countries:
        result = process_country(iso3, afts_all, planet_raw_dir)
        if result:
            rows.append(result)
            print(
                f"  {iso3}: "
                f"match_planet {result['match_rate_planet']}% / "
                f"match_aftsdb {result['match_rate_aftsdb']}%"
            )
        else:
            print(f"  {iso3}: skipped (empty)")

    df = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"rerun_{date.today().isoformat()}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nsaved: {out_path}  ({len(df)} countries)")


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)