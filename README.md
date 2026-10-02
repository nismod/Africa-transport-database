# The African Transport Systems Database  - a geospatial database of multi-modal connected networks

We present the first comprehensive geolocated multi-modal transport database for
the whole continent of Africa, the **African Transport Systems Database
(AfTS-Db)**, including road, rail, aviation, maritime and inland waterway
networks. To do so, we created and standardized asset and network data across
all transport modes, including inter-modal connections, attributes of road and
rail corridors and estimated annual statistics for airports and ports.

The African Transport Systems Database includes:
- airports including their airline routes
- maritime ports and their connections with each other
- inland ports and docking sites with river and lake connections
- railway stations connected across rail lines
- roads mainly comprised of all motorways, trunk roads, primary and secondary
  routes across Africa and some local roads that connect to other transport
  modes

The AfTS-Db provides key information for transport planning, resilience
assessments, asset management and development of transport models and
applications. Furthermore, we expect the data will also be of relevance for
environmental, health, social and economic studies.

The data description paper is published in Scientific Data at
[DOI:10.1038/s41597-025-06483-7](https://doi.org/10.1038/s41597-025-06483-7)

> Colombo, S., Pant, R., Young, M. et al. The African Transport Systems Database
> - a geospatial database of multi-modal connected networks. Sci Data 13, 166
> (2026). https://doi.org/10.1038/s41597-025-06483-7

The data record is on Zenodo at
[DOI:10.5281/zenodo.15527231](https://doi.org/10.5281/zenodo.15527231)

> Colombo, S., Pant, R., Young, M., Thomas, F., Russell, T., Verschuur, J., &
> Hall, J. W. (2025). The African Transport Systems Database - a geospatial
> database of multi-modal connected networks [Data set]. Zenodo.
> https://doi.org/10.5281/zenodo.15527231


This GitHub folder contains the scripts that have been used to create the
database, of particular importance the road network creation and the multimodal
edges creation ones.

The codes for operationalization for downloading and creating network
representations from OSM raw data, via the Open-Gira repository, are available
here: https://github.com/nismod/open-gira. Further Open-Gira documentation is
provided here:
https://nismod.github.io/open-gira/user-guide/usage/network-creation/road.html
and
https://nismod.github.io/open-gira/user-guide/usage/network-creation/rail.html.

The spatially explicit, harmonized AfTS-Db is publicly available and can be
explored [here](https://zenodo.org/uploads/17593244). These files can be easily
accessed, visualized, and manipulated using standard GIS applications such as
QGIS or ArcGIS.

This research has been supported by the **Climate Compatible Growth (CCG)**
program funded by the UK Foreign, Commonwealth and Development Office
([FCDO](https://devtracker.fcdo.gov.uk/programme/GB-GOV-1-300125/summary)).

## Workflow

The workflow is split into stages, one rule file per stage:

1. `rules/download.smk`: fetch the incoming data that can be fetched
2. `rules/process.smk`: build the database from the incoming data
3. `rules/validate.smk`: compare the database against reference datasets
4. `rules/plot.smk`: map and chart the finished database

The contents of `workflow_tree.txt` show the files read and written by the
entire workflow. Regenerate it after changing any rule:

```bash
python tools/workflow_tree.py --output workflow_tree.txt
```

All the scripts used to create the datasets are called by the workflow rules,
can be found in [`./scripts `](./scripts).

These two scripts are particularly important to creating the database:
- [road_connectivity.py](./scripts/preprocess/road_connectivity.py)
- [multi_modal_edges_creation.py](./scripts/preprocess/multi_modal_edges_creation.py)

### Road network creation

The road topological network creation follows 5 main steps:

1. Input the different location data from different extracts (infrastructure
   assets, cities, ...)
2. Input the road edges data for Africa (already extracted from OpenStreet Map)
3. Filter the OSM roads to the preferred geographical scale (in this case up to
   secondary roads)
4. Connect the points of interest with the closest point of the road network,
   creating a topological network
5. Create a more capillary network when the resolution of the filtered roads is
   not enough to connect specific points, connect the selection of smaller roads
   to the network


### Multimodal links creation

The multimodal network creation constists of:

1. Input the different point location data from all the transport datasets:
   airports, maritime ports, inland ports, railway stations and points of
   interest, road nodes
2. Connect the different nodes to the ground transport network (road and rail
   nodes)
3. Differentiate the connection between freight transport (specific rail-road
   connection based on the facility specifics of the rail node) and general
   freight/passenger transport (the rest of the connections, if not specified)
4. The resulting dataset will include edges identified by unique IDs, along with
   references to the source and target nodes they connect, as well as details
   about the link and its usage (freigth or freight/transport)


## Development setup

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

### Lint and format

Use [ruff](https://docs.astral.sh/ruff/) to format and check scripts and source
code:

```bash
ruff format
ruff check
```

### Configure the data paths

Copy `config.template.json` to `config.json` and edit the four paths in it to
point at your local data directories. The workflow reads that file and passes
the resolved paths to the scripts, so the config is the single place where the
data directories are set. Relative paths are relative to the repository root,
which is where snakemake runs.

### Run the workflow

```bash
snakemake --dry-run                       # what would run, and why
snakemake --cores 1                       # build the published network layers
snakemake --cores 1 plot_roads_typology   # run a single rule or create an output file
snakemake --list                          # list each rule
```
Each rule runs one script, and passes every file that script reads or writes as
a command line argument. The scripts take those paths with
[click](https://click.palletsprojects.com/), so any of them can also be run on
its own - `python "scripts/plot/africa_maps_roads.py" --help` lists what a
script needs.


### Work in progress

`explore/` holds investigations that are not part of the workflow yet.
`explore/rail_network_port` is exploring rebuilding the rail network from
OpenStreetMap and applying `trg-rail` edits where they remain necessary.

## Acknowlegments, License, Funding

If using the data or this workflow, cite the data description paper from
Scientific Data,
[DOI:10.1038/s41597-025-06483-7](https://doi.org/10.1038/s41597-025-06483-7)

> Colombo, S., Pant, R., Young, M. et al. The African Transport Systems Database
> - a geospatial database of multi-modal connected networks. Sci Data 13, 166
> (2026). https://doi.org/10.1038/s41597-025-06483-7

This code is made available open-source under the [MIT License](./LICENSE),
Copyright (c) 2024-2026 Raghav Pant, Silvia Colombo, Tom Russell and
contributors.

This research received funding from the UK FCDO Climate Compatible Growth
Programme,
[`GB-GOV-1-300125`](https://devtracker.fcdo.gov.uk/programme/GB-GOV-1-300125/summary).
The views expressed here do not necessarily reflect the UK government's official
policies.
