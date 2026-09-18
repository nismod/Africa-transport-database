# Planet Road Surface Enrichment

Adds 11 `planet_*` attributes to AfTS-Db road edges using OSM way IDs. Original input files are preserved.

## 1. Create the environment

Run from the repository root:

```bash
conda env create -f environment.yml
conda activate roadsurface
```

If the environment already exists, only run the activation command.

## 2. Prepare AfTS-Db

Download the road network from:

https://zenodo.org/records/17861120

Place `africa_roads_network.gpkg` under your input directory:

```text
incoming_data/
└── aftsdb/
    └── africa_roads_network.gpkg
```

## 3. Configure paths

Copy `config.template.json` to `config.json`. Set the paths for your computer. For example:

```json
{
    "paths": {
        "incoming_data": "./incoming_data",
        "data": "./processed_data",
        "figures": "./figures"
    }
}
```

For these scripts, relative paths are resolved from the repository root.

The target country list is included in `config/aftsdb_countries.json`.

## 4. Run

From the repository root:

```bash
python scripts/planet_roadsurface/query_planet_countries.py
python scripts/planet_roadsurface/download_planet_data.py
python scripts/planet_roadsurface/match_planet_aftsdb.py
python scripts/planet_roadsurface/build_enriched_aftsdb.py
```

These steps query download links, download Planet data, report matches, and generate the enriched road layer.

Planet files are saved under the configured input directory in `planet_raw/`. Existing files are skipped without checking for online updates. Adding `--force` to the download command replaces existing files.

## Outputs

Outputs are saved under the configured `data` directory in `planet_roadsurface/`:

- `planet_catalog_manifest.json`: download links.
- `rerun_<date>.csv`: matching statistics.
- `AfTSDb_Africa_enriched_with_Planet.gpkg`: enriched road edges.
- `AfTSDb_Africa_enriched_with_Planet.fields.csv`: field descriptions.

The GeoPackage contains only `edges_enriched`; the original nodes are not included. All AfTS-Db edges are retained, with empty Planet fields where no match exists.

Rerunning can overwrite outputs with the same names.

## Current scope

The workflow currently runs locally. AfTS-Db must be downloaded manually; Planet downloads are scripted. GitHub Actions is not yet configured.