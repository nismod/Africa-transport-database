"""
Merges Planet's road-surface attributes into AfTS-Db for the whole
continent. AfTS-Db is the base table. Every edge stays in the output,
even ones from countries with no Planet data, those just get empty
planet_* columns.

Reads all 55 country files, stacks them into one table, then does a
single left join onto AfTS-Db.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio


# ROOT = Path(__file__).resolve().parent.parent
# AFTSDB_PATH = ROOT / "data" / "aftsdb" / "africa_roads_network.gpkg"
# PLANET_RAW_DIR = ROOT / "data" / "planet_raw"
# OUT_PATH = ROOT / "results" / "AfTSDb_Africa_enriched_with_Planet.gpkg"

from config_utils import load_config

PLANET_NEW_COLS = [
    "DL_road_class_2024", "DL_road_class_2020", "surface_change_paved",
    "paved_pixels_2024", "paved_pixels_2020", "unpaved_pixels_2024", "unpaved_pixels_2020",
    "rw_class", "Passability_Alphanumeric_Code", "Passability_Descriptive_Code",
    "Passability_Numerical_Risk_Score",
]


# def load_all_planet_attributes() -> pd.DataFrame:
#     files = sorted(PLANET_RAW_DIR.glob("*_planet_roadsurface.gpkg"))
def load_all_planet_attributes(planet_raw_dir: Path) -> pd.DataFrame:
    files = sorted(planet_raw_dir.glob("*_planet_roadsurface.gpkg"))
    print(f"reading {len(files)} country files...")

    country_tables = []
    for path in files:
        table = pyogrio.read_dataframe(
            path, read_geometry=False, columns=["osm_id"] + PLANET_NEW_COLS,
        )
        country_tables.append(table)

    combined = pd.concat(country_tables, ignore_index=True)
    combined["osm_id_num"] = combined["osm_id"].str.replace("way/", "", regex=False).astype("int64")
    before = len(combined)
    combined = combined.drop_duplicates("osm_id_num")
    print(f"  {before} records, {len(combined)} unique osm_id after dedup")
    return combined




def main(config):
    incoming_data_path = config["paths"]["incoming_data"]
    processed_data_path = config["paths"]["data"]

    AFTSDB_PATH = incoming_data_path / "aftsdb" / "africa_roads_network.gpkg"
    PLANET_RAW_DIR = incoming_data_path / "planet_raw"
    OUT_PATH = (
        processed_data_path
        / "planet_roadsurface"
        / "AfTSDb_Africa_enriched_with_Planet.gpkg"
    )

    print("loading AfTS-Db (all edges, with geometry)...")
    afts = gpd.read_file(AFTSDB_PATH, layer="edges", engine="pyogrio")
    afts["osm_way_id"] = afts["osm_way_id"].astype("Int64")
    print(f"  {len(afts)} edges")

    planet = load_all_planet_attributes(PLANET_RAW_DIR)

    print("\njoining...")
    enriched = afts.merge(
        planet[["osm_id_num"] + PLANET_NEW_COLS].rename(
            columns={c: f"planet_{c}" for c in PLANET_NEW_COLS}
        ),
        left_on="osm_way_id",
        right_on="osm_id_num",
        how="left",
    ).drop(columns=["osm_id_num"])

    matched = enriched["planet_rw_class"].notna().sum()
    print(
        f"\n{matched} / {len(enriched)} AfTS-Db edges got Planet attributes "
        f"({matched / len(enriched) * 100:.1f}%)"
    )

    print("\nmatch rate by country (top 10):")
    per_country = (
        enriched.groupby("from_iso3")["planet_rw_class"]
        .apply(lambda s: s.notna().mean() * 100)
        .sort_values(ascending=False)
    )
    print(per_country.head(10).round(1))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_file(OUT_PATH, driver="GPKG", layer="edges_enriched")
    print(f"\nsaved: {OUT_PATH}")

    doc_path = OUT_PATH.with_suffix(".fields.csv")
    import csv

    with open(doc_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["field", "source", "meaning"])
        w.writerow([
            "(21 original AfTS-Db fields)",
            "AfTS-Db",
            "id/from_id/to_id/osm_way_id/tag_highway/tag_surface/tag_lanes/... (unchanged)",
        ])
        w.writerow([
            "planet_DL_road_class_2024/2020",
            "Planet (PlanetScope + deep learning)",
            "surface class from two imagery epochs: Paved/Unpaved/Unknown",
        ])
        w.writerow([
            "planet_surface_change_paved",
            "Planet (epoch comparison)",
            "flags a 2020->2024 surface change",
        ])
        w.writerow([
            "planet_paved_pixels_2024/2020, unpaved_pixels_2024/2020",
            "Planet",
            "segmentation mask pixel counts, a rough confidence signal",
        ])
        w.writerow([
            "planet_rw_class",
            "Planet",
            "road width class: Class1(<3.5m)/Class2(3.5-5.5m)/Class3(>5.5m). "
            "AfTS-Db had no width field before this",
        ])
        w.writerow([
            "planet_Passability_Alphanumeric_Code/Descriptive_Code/Numerical_Risk_Score",
            "Planet",
            "humanitarian passability index, Score1(best)-Score6(worst). "
            "New to AfTS-Db",
        ])
        w.writerow([
            "(blank planet_* fields)",
            "-",
            "no Planet match: either the country isn't in our 55 "
            "(e.g. Namibia, Western Sahara), the road class is outside "
            "Planet's arterial-only scope, or a small residual of unmatched records",
        ])

    print(f"field notes: {doc_path}")


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)
