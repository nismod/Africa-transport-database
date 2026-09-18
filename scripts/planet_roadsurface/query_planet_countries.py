"""
Finds which countries HeiGIT has a Planet road-surface dataset for and
grabs each one's direct .gpkg download URL. Does not download anything.

Uses HDX's package_search API. One call returns every dataset, already
including country code and resource URLs.

The target country list comes from data/aftsdb_countries.json.
"""
import json

from pathlib import Path

import requests
from config_utils import load_config

# DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# COUNTRIES_CONFIG = DATA_DIR / "aftsdb_countries.json"

HDX_SEARCH_URL = "https://data.humdata.org/api/3/action/package_search"
HDX_SEARCH_PARAMS = {
    "q": (
        "organization:heidelberg-institute-for-geoinformation-technology "
        'AND title:"Planet Road Surface"'
    ),
    "rows": 300,
}
HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_target_countries(countries_path: Path) -> set[str]:
    countries = json.loads(countries_path.read_text(encoding="utf-8"))
    return set(countries["iso3_codes"])


def query_planet_catalog() -> list[dict]:
    resp = requests.get(
        HDX_SEARCH_URL,
        params=HDX_SEARCH_PARAMS,
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json()["result"]["results"]

    entries = []
    for pkg in results:
        groups = pkg.get("groups") or []
        if not groups:
            continue

        iso3 = groups[0]["name"].upper()
        gpkg_url = next(
            (
                r["url"]
                for r in pkg.get("resources", [])
                if r.get("format") == "Geopackage"
            ),
            None,
        )
        entries.append({
            "iso3": iso3,
            "country_name": groups[0]["title"],
            "hdx_name": pkg["name"],
            "gpkg_url": gpkg_url,
            "last_modified": pkg.get("last_modified"),
        })

    return entries


def main(config):
    processed_data_path = config["paths"]["data"]

    project_root = Path(__file__).resolve().parents[2]
    countries_path = project_root / "config" / "aftsdb_countries.json"

    out_dir = processed_data_path / "planet_roadsurface"
    manifest_path = out_dir / "planet_catalog_manifest.json"

    target_countries = load_target_countries(countries_path)
    print(f"target list: {len(target_countries)} countries")

    print("\nquerying HDX for HeiGIT Planet datasets...")
    all_entries = query_planet_catalog()
    print(f"  {len(all_entries)} datasets worldwide")

    matched = [
        entry
        for entry in all_entries
        if entry["iso3"] in target_countries and entry["gpkg_url"]
    ]
    matched.sort(key=lambda entry: entry["iso3"])
    print(f"  {len(matched)} matched our target list")

    missing = target_countries - {entry["iso3"] for entry in matched}
    if missing:
        print(
            f"  {len(missing)} in target list but not found: "
            f"{sorted(missing)}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(matched, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nsaved: {manifest_path}")
    print("(query only, no GeoPackage files downloaded)")


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)