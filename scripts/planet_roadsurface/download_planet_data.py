"""
Downloads each country's Planet GeoPackage using the manifest that
query_planet_countries.py produced.

Skips a country if the file already exists. Pass --force to re-download.

Usage:
    python3 download_planet_data.py
    python3 download_planet_data.py --force
"""
import json
import sys
from pathlib import Path
import requests
from config_utils import load_config

# DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# MANIFEST_PATH = DATA_DIR / "planet_catalog_manifest.json"
# RAW_DIR = DATA_DIR / "planet_raw"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_one(entry: dict, raw_dir: Path, force: bool) -> str:
    out_path = raw_dir / f"{entry['iso3']}_planet_roadsurface.gpkg"

    if out_path.exists() and not force:
        return "skipped(already exists)"

    tmp_path = out_path.with_suffix(".gpkg.part")

    with requests.get(
        entry["gpkg_url"],
        headers=HEADERS,
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()

        with tmp_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    # Replace the destination only after the download completes.
    tmp_path.replace(out_path)
    size_mb = out_path.stat().st_size / 1024 / 1024
    return f"downloaded({size_mb:.1f}MB)"


def main(config):
    incoming_data_path = config["paths"]["incoming_data"]
    processed_data_path = config["paths"]["data"]

    manifest_path = (
        processed_data_path
        / "planet_roadsurface"
        / "planet_catalog_manifest.json"
    )
    raw_dir = incoming_data_path / "planet_raw"
    force = "--force" in sys.argv

    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"{manifest_path} not found. "
            "Run query_planet_countries.py first."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest:
        raise ValueError("The download manifest is empty.")

    raw_dir.mkdir(parents=True, exist_ok=True)
    print(f"{len(manifest)} countries in manifest, force={force}\n")

    results = {"downloaded": 0, "skipped": 0, "failed": 0}

    for entry in manifest:
        try:
            status = download_one(entry, raw_dir, force)
            print(
                f"  {entry['iso3']} ({entry['country_name']}): {status}"
            )
            if status.startswith("downloaded"):
                results["downloaded"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            print(
                f"  {entry['iso3']} ({entry['country_name']}): "
                f"failed - {e}"
            )
            results["failed"] += 1

    print(
        f"\ndone: {results['downloaded']} downloaded, "
        f"{results['skipped']} skipped, "
        f"{results['failed']} failed"
    )
    print(f"files in: {raw_dir}")

    if results["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    CONFIG = load_config()
    main(CONFIG)