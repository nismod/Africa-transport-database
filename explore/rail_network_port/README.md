# Explore porting trg-rail

The rail network comes from `trg-rail/africa_rail_network` as a one-off dataset.
That project developed the dataset in PostgreSQL/PostGIS with pgRouting.

Can we port those edits to run against a fresh OpenStreetMap extract
within the snakemake workflow here?

Initial steps:

1. `prepare_network.py` reproduces `afrn.sql` using SedonaDB.
2. `apply_country_edits.py` replays a country's edits from a data
  file. Gabon reproduces the published network - all three lines,
  matching on both edge count and length.

The 24 country scripts in `trg-rail` contain roughly 3,200 edits to port.

Smaller/large scope:

- **Replaying the recorded build** on the inputs it was written against.
  Everything it needs is in the trg-rail repository.
- **Rebuilding from a current OSM extract** is not a port. The 4,503 feature ids
  mentioned in the country scripts match row numbers from a 2021 snkit run and
  the original input. These cannot be reproduced from a new (e.g. 2026) extract.
  This needs the edits re-keyed to OSM ids, and possibly point locations, to
  handle cases where OSM has since changed.

## Notes on the original process

Three stages:

1. `network_sql_scripts/afrn.sql`: 208 lines. Assigns countries, resolves
   cross-border edges, derives integer oids, measures lengths, maps OSM railway
   tags to status/type/structure.
2. `countries_sql_scripts/*.sql`: 24 files, 35,372 lines. Names lines, sets
   gauges, statuses and modes, adds stations and facilities, splits and joins
   edges to make the network route.
3. `network_sql_scripts/generate_combined_network.sql`: 486 lines. Merges in the
   earlier East Africa (HVT) network, renumbers its ids, joins the two at three
   border crossings, normalises facility names and country capitalisation, flags
   electrification.

Main inputs:
- `data/africa-rail.gpkg` (135,473 edges, 154,951 nodes - the output of `snkit` over a Geofabrik africa-211101
extract, via a script in nismod/east-africa-transport)
- `data/osm_admin_boundaries_africa.geojson` (59 boundaries)

Kinds of statement in the country scripts:

- total: 4,075
- `update`, real: 1,159
- `update`, unfilled templates: 73
- `update rubbish set rubish` (force execution to stop): 17
- `pgr_dijkstra` routes, real: 758
- `pgr_dijkstra` routes with a blank endpoint: 7
- `split_edge` operations: 677
- `copy_node` operations: 464
- `insert_edge` operations: 108
- `change_source` / `change_target`: 30
- `select`, exploratory: 1,345
- **Estimated meaningful edits**: **3,196**

Main operation: route between two node ids, then set line, gauge, status, mode
and comment on every edge along the path. Most route over the whole edge table
or one country's edges; the rest add a short exclusion list to steer the path.

## Stage 1

Generally works fine using `prepare_network.py`.

One discrepancy: `afrn.sql` finds 4 nodes with no country and names them, this
port finds 278.

266 of them are on Réunion, which is missing from the boundaries file in the
repository - so this is not exactly the original `africa_osm_countries` table.

The remaining 12 are scattered coastal and near-border nodes.

## Stage 2 demo for Gabon

`edits/gabon.yaml` is what `countries_sql_scripts/gabon/gabon.sql` reduces to 19
edits from 211 lines. The rest of that file is notebook - exploratory selects,
unfilled templates, the syntax-error trap, two backup table copies and a routing
test with its endpoints left blank.

`apply_country_edits.py` replays it onto the prepared network and compares
with what the original build published:

| Line | Published | Replayed | Match |
| --- | --- | --- | --- |
| Trans-Gabon Railway | 144 edges, 645.8 km | 144 edges, 645.8 km | yes |
| Port of Owendo | 10 edges, 5.5 km | 10 edges, 5.5 km | yes |
| Moanda Mine | 6 edges, 2.7 km | 6 edges, 2.7 km | yes |

19 edits in 1.3 seconds. The script exits non-zero if any line stops matching.

Two things this proves beyond feasibility:

- **The derived-id convention is right.** Upstream numbers a split's parts by
  appending a row number to the parent oid, and a copied node by adding
  1000000. Later edits refer to those derived ids: Gabon splits `555057990`,
  then splits the resulting `5550579902`, then copies a station onto
  `55505799021`. The replay follows that chain to the same features, which it
  could not do if the numbering were even slightly different.
- **Routing is not the bottleneck.** igraph builds the 154,951-vertex graph in
  0.5s and answers a real 474-edge path across South Africa in 40ms. The
  graph is rebuilt only when an edit changes the topology.

Five operations covered Gabon: `copy_node`, `split_edge`, `tag_route`,
`set_node` and `set_nodes_on_edges`. The whole corpus needs two more,
`insert_edge` and `change_source`/`change_target` (138 calls between them),
which `primitives.py` already implements and checks.

## Next steps

Parse the country edits files into sets of operations. Most of the data processing is:
- route
- split
- copy

| Country | Lines | Updates | Routes | Splits | Copies |
| --- | --- | --- | --- | --- | --- |
| south africa | 11,085 | 719 | 419 | 279 | 196 |
| tunisia | 2,824 | 273 | 53 | 0 | 0 |
| zimbabwe | 2,308 | 128 | 63 | 63 | 29 |
| mozambique | 2,274 | 103 | 47 | 32 | 70 |
| egypt | 1,969 | 153 | 62 | 49 | 12 |
| algeria | 1,887 | 144 | 48 | 0 | 0 |
| west_africa_ex_nigeria | 1,800 | 130 | 52 | 27 | 20 |
| morocco | 1,079 | 71 | 32 | 0 | 0 |
| malawi | 1,015 | 60 | 33 | 21 | 4 |
| drc | 1,004 | 63 | 33 | 23 | 9 |
| *14 others* | 6,127 | 385 | 218 | 70 | 112 |
| **total** | **35,372** | **2,329** | **1,060** | **564** | **452** |


Currently plan for six workflow rules, with accompanying script:

1. `rail_prepare_network` - `afrn.sql`. **Done**, `prepare_network.py`.
   Inputs: the snkit GeoPackage and the boundaries. Output: prepared nodes and
   edges.
2. `rail_country_edits` - one wildcard rule per country, applying that
   country's edit file. **Done**, `apply_country_edits.py`; one of 24 edit
   files exists.
3. `rail_combine_countries` - concatenate the 24 outputs.
4. `rail_merge_hvt` - the East Africa merge and renumbering from
   `generate_combined_network.sql`, including the three border joins.
5. `rail_normalise` - the facility, status and country-name lookups. These are
   pure value mappings and belong in a CSV the rule reads, not in code.
6. `rail_electrification` - the electrified flag, which is part rule-based on
   the comment text and part three routed paths.

### What to do with oids

The ids everything is keyed on are not OSM ids. `rail_africa_preprocess.sh` runs
`osmium tags-filter` and `ogr2ogr`, then `process_rail.py` builds a snkit
network and calls `snkit.network.add_ids(..., edge_prefix="rail_africa")`, which
numbers features by row position. The oid is `555000000` plus that number. The
country scripts carry 6,276 hard-coded oid references, 4,503 of them distinct:
3,988 from that numbering and 515 created by the `rn_*` functions.

Notes towards a plan:
- `africa-rail.gpkg` carries `osm_id` on both layers, and `afrn.sql` drops it
- `prepare_network.py` keeps it
- the original dataset can be processed to output reference point/line locations
  for each oid
- adjust the parsed edits to keep OSM ID and point location wherever only oid is
  used at present, then applying the split/rename/whatever operation can be
  done based on location and OSM ID, which will be more durable and reliable

## Development

Needs `duckdb`, `sedonadb`, `igraph`, `pyproj`, `shapely` and `pyyaml`; not all
in top-level `environment.yml`, until we port this into the main workflow.

```bash
pip install duckdb sedonadb
python primitives.py
```

The rest needs a clone of the [`trg-rail`](https://github.com/trg-rail/africa_rail_network) repository:

```bash
git clone https://github.com/trg-rail/africa_rail_network /tmp/africa_rail_network
RAIL=/tmp/africa_rail_network

python prepare_network.py --engine duckdb --database /tmp/rail.duckdb \
    --rail-network $RAIL/data/africa-rail.gpkg \
    --boundaries $RAIL/data/osm_admin_boundaries_africa.geojson

python apply_country_edits.py --database /tmp/rail.duckdb \
    --edits edits/gabon.yaml \
    --compare $RAIL/network/africa_rail_network.geojson
```

SedonaDB is faster in testing, but current implementation uses the duckdb file between
steps - so to simplify and keep the fast implementation, need to output to
geoparquet instead for persistence, and drop the duckdb engine option.
