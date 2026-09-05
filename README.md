# The African Transport Systems Database  - a geospatial database of multi-modal connected networks

We present the first comprehensive geolocated multi-modal transport database for the whole continent of Africa, the **African Transport Systems Database (AfTS-Db)**, including road, rail, aviation, maritime and inland waterway networks. To do so, we created and standardized asset and network data across all transport modes, including inter-modal connections, attributes of road and rail corridors and estimated annual statistics for airports and ports. The African Transport Systems Database includes 234 airports including their airline routes, 179 maritime ports and their connections with each other, 132 inland ports and docking sites with river and lake connections, 4,412 railway stations connected across 99,373 kilometers of rail lines, and 1,004,512 kilometers of roads mainly comprised of all motorways, trunk roads, primary and secondary routes across Africa and some local roads that connect to other transport modes. The AfTS-Db provides key information for transport planning, resilience assessments, asset management and development of transport models and applications. Furthermore, we expect the data will also be of relevance for environmental, health, social and economic studies.

The data description paper is published in Scientific Data at [DOI:10.1038/s41597-025-06483-7](https://doi.org/10.1038/s41597-025-06483-7)

> Colombo, S., Pant, R., Young, M. et al. The African Transport Systems Database - a geospatial database of multi-modal connected networks. Sci Data 13, 166 (2026). https://doi.org/10.1038/s41597-025-06483-7

The data record is on Zenodo at [DOI:10.5281/zenodo.17861120](https://doi.org/10.5281/zenodo.17861120)

> Colombo, S., Pant, R., Young, M., Thomas, F., Russell, T., Verschuur, J., & Hall, J. W. (2025). The African Transport Systems Database - a geospatial database of multi-modal connected networks [Data set]. Zenodo. https://doi.org/10.5281/zenodo.17861120

This repository is archived on Zenodo at [DOI:10.5281/zenodo.17609113](https://doi.org/10.5281/zenodo.17609113)

> Pant, R., Colombo, S., Russell, T., & Thomas, F. (2025). nismod/Africa-transport-database: The African Transport Systems Database (AfTS-Db) (v1.0.0). Zenodo. https://doi.org/10.5281/zenodo.17609113

This GitHub folder contains the scripts that have been used to create the database, of particular importance the road network creation and the multimodal edges creation ones.

The codes for operationalization for downloading and creating network representations from OSM raw data, via the Open-Gira repository, are available here: https://github.com/nismod/open-gira. Further Open-Gira documentation is provided here: https://nismod.github.io/open-gira/user-guide/usage/network-creation/road.html and https://nismod.github.io/open-gira/user-guide/usage/network-creation/rail.html.

The spatially explicit, harmonized AfTS-Db is publicly available and can be explored [here](https://zenodo.org/uploads/17593244). These files can be easily accessed, visualized, and manipulated using standard GIS applications such as QGIS or ArcGIS.

This research has been supported by the **Climate Compatible Growth (CCG)** program funded by the UK Foreign, Commonwealth and Development Office ([FCDO](https://devtracker.fcdo.gov.uk/programme/GB-GOV-1-300125/summary)).

## About the scripts
All the scripts used to create the datasets are available and free to use in the [**scripts folder**](https://github.com/nismod/Africa-transport-database/tree/main/scripts), ensuring replicability of the database. Most of them represent simple cleaning and validation (in the [**preprocess**](https://github.com/nismod/Africa-transport-database/tree/main/scripts/preprocess) folder) or plots and figures (in the [**maps and stats**](github.com/nismod/Africa-transport-database/tree/main/scripts/maps%20and%20stats) and [**plot**](https://github.com/nismod/Africa-transport-database/tree/main/scripts/plot) folders) reproduction codes. <br/>
Of major importance and representing the novelty of how the dataset has been developed, are the [road network creation](https://github.com/nismod/Africa-transport-database/blob/main/scripts/preprocess/road_connectivity.py) and the [multimodal links creation](https://github.com/nismod/Africa-transport-database/blob/main/scripts/preprocess/multi_modal_edges_creation.py).

### Development setup

The scripts are in the process of being developed into an open-source
[snakemake](https://snakemake.readthedocs.io/en/stable/) workflow. This aims to
improve the ease of re-running the scripts to reproduce and update dataset.

The repository comes with a `environment.yml` file describing the `conda` and
`PyPI` packages required to run the workflow. We recommend using
[micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html#micromamba)
to install and manage these packages.

Create the environment (once per machine):

```bash
micromamba env create -f environment.yml -y
```

Activate the environment (once per work session):

```bash
micromamba activate aftdb
```

Reinstall or update the environment (after adding or updating dependencies):

```bash
micromamba install -f environment.yml -y
```

#### Lint and format

Use [ruff](https://docs.astral.sh/ruff/) to format and check scripts and source code:

```bash
ruff format
ruff check
```

#### Configure the data paths

Copy `config.template.json` to `config.json` and edit the four paths in it to
point at your local data directories. The workflow reads that file and passes
the resolved paths to the scripts, so the config is the single place where the
data directories are set. Relative paths are relative to the repository root,
which is where snakemake runs.

#### Run the workflow

```bash
snakemake --dry-run                       # what would run, and why
snakemake --cores 1                       # build the published network layers
snakemake --cores 1 plot_roads_typology   # or name a single rule or output file
snakemake --list                          # every rule, with what it does
```

The workflow is split into stages, one rule file per stage:

| File                 | Stage                                                |
| -------------------- | ---------------------------------------------------- |
| `rules/download.smk` | fetch the incoming data that can be fetched           |
| `rules/process.smk`  | build the database from the incoming data             |
| `rules/validate.smk` | compare the database against reference datasets       |
| `rules/plot.smk`     | map and chart the finished database                   |

The `Snakefile` itself holds only what the stages share: the config, the data
paths, the datasets several rules read, and the default target.

Each rule runs one script, and passes every file that script reads or writes
as a command line argument. The scripts take those paths with
[click](https://click.palletsprojects.com/), so any of them can also be run on
its own - `python "scripts/plot/mine_ownership_maps.py" --help` lists what a
script needs. Nothing under `scripts/` reads `config.json`: the rule that
calls a script is the only place its paths are written down.

The docstring at the top of `rules/download.smk` inventories every external
input, where it comes from, and whether a rule fetches it or it has to be put
in place by hand. Some sources - the corridor project alignments, the Google
Places matches, the cost spreadsheets - were compiled or digitised by the
authors and cannot be fetched at all; that docstring says so for each one, and
lists the gaps that stop the workflow running end to end.

Each download rule there is marked *tested* or *drafted*. A drafted rule
follows the source's documented download API but has not been run against it,
so the first person to run one should check that what comes out of the archive
lands at the paths the rule declares.

The road and rail networks are built from OpenStreetMap. `osm_extract_africa`
cuts the Africa extract out of a weekly planet file from the OpenStreetMap
Foundation's S3 bucket, which keeps every snapshot, rather than from a
Geofabrik extract, which is only served for 90 days. The snapshot to build
from is the `osm_snapshot` date in `config.json`; planet files are cut on
Mondays, so it has to be a Monday. That download is around 90GB and the
extract reads all of it, so it is much the longest step in the workflow.

### Road network creation
The road topological network creation follows 5 main steps: <br/>
<br/>
**Step 1:** Input the different location data from different extracts (infrastructure assets, cities, ...)<br/>
**Step 2:** Input the road edges data for Africa (already extracted from Oper Street Map)<br/>
**Step 3:** Filter the OSM roads to the preferred geographical scale (in this case up to secondary roads)<br/>
**Step 4:** Connect the points of interest with the closest point of the road network, creating a topological network <br/>
**Step 5:** Create a more capillary network when the resolution of the filtered roads is not enough to connect specific points, connect the selection of smaller roads to the network<br/>


### Multimodal links creation
The multimodal network creation constists on:<br/>
<br/>
**Step 1:** Input the different point location data from all the transport datasets: airports, maritime ports, inland ports, railway stations and points of interest, road nodes <br/>
**Step 2:** Connect the different nodes to the ground transport network (road and rail nodes) <br/>
**Step 3:** Differentiate the connection between freight transport (specific rail-road connection based on the facility specifics of the rail node) and general freight/passenger transport (the rest of the connections, if not specified) <br/>
**Step 4:** The resulting dataset will include edges identified by unique IDs, along with references to the source and target nodes they connect, as well as details about the link and its usage (freigth or freight/transport)
