# Porting the trg-rail build to a local script

Scoping the question raised against `rules/download.smk`: the rail network
comes from [trg-rail/africa_rail_network][trg-rail] as published GeoJSON, and
its build runs in PostgreSQL/PostGIS with pgRouting. Could that build be
ported to explicit steps in a local script - DuckDB or Apache Sedona giving a
SQL interface over files - so it fits the snakemake workflow without a
Postgres dependency?

**Short answer.** DuckDB can do the geometry and igraph can do the routing;
both are proved below against the real data. But "port the SQL" turns out to
be two different projects, and only one of them is a port:

- **Replaying the recorded build** on the inputs it was written against is
  feasible and worth doing. Everything it needs is in the trg-rail repository.
  Stage 1 is written and passes every count the original records. Estimate:
  **3-6 weeks**, most of it on the 24 country scripts.
- **Rebuilding from a current OSM extract** is not a port. The 4,503
  hand-picked feature ids the country scripts are keyed on are row numbers
  from a 2021 snkit run, and cannot be reproduced from a 2026 extract. This
  needs the edits re-keyed to OSM ids first, which is a data migration on top
  of the port, and lossy where OSM has since changed. Estimate: **the port,
  plus 4-8 weeks**, with an accuracy cost that has to be measured.

Recommendation: do neither yet, and keep pinning the published GeoJSON at a
commit. Do the replay port when the network needs changing rather than
refreshing - it converts an unrepeatable GUI session into something reviewable,
which is what makes the research maintainable. Treat the rebuild as a separate
proposal with its own accuracy budget.

## What the upstream build is

Three stages, and the count of what is in each:

| Stage | Files | What it does |
| --- | --- | --- |
| `network_sql_scripts/afrn.sql` | 208 lines | Assigns countries, resolves cross-border edges, derives integer oids, measures lengths, maps OSM railway tags to status/type/structure |
| `countries_sql_scripts/*.sql` | 24 files, 35,372 lines | The research: names lines, sets gauges, statuses and modes, adds stations and facilities, splits and joins edges to make the network route |
| `network_sql_scripts/generate_combined_network.sql` | 486 lines | Merges in the earlier East Africa (HVT) network, renumbers its ids, joins the two at three border crossings, normalises facility names and country capitalisation, flags electrification |

Its inputs are both in that repository: `data/africa-rail.gpkg` (135,473
edges, 154,951 nodes - the output of `snkit` over a Geofabrik africa-211101
extract, via a script in nismod/east-africa-transport) and
`data/osm_admin_boundaries_africa.geojson` (59 boundaries).

What the country scripts contain, by statement:

| | Count |
| --- | --- |
| Statements | 4,075 |
| `update` | 1,249 |
| `pgr_dijkstra` calls | 1,060 |
| `rn_split_edge` calls | 564 |
| `rn_copy_node` calls | 452 |
| `rn_insert_edge` calls | 108 |
| `rn_change_source` / `rn_change_target` calls | 30 |
| Bare exploratory `select` | 1,345 |
| Anonymous `DO $$` blocks | 15 |

The dominant pattern is one shape, 1,060 times: route between two node ids,
then set line, gauge, status, mode and comment on every edge along the path.
946 of those route over the whole edge table or one country's edges; the rest
add a short exclusion list to steer the path.

## Feasibility

### DuckDB or Sedona

DuckDB. Sedona means a JVM and a Spark session, and its routing story
(GraphFrames) is another dependency again; for a 135k-edge network that is a
lot of machinery for no gain. DuckDB is one Python package, runs in-process,
reads and writes GeoPackage and GeoParquet directly, and its SQL is close
enough to Postgres that the statements read the same.

Neither has a pgRouting. igraph does the routing, and is already a dependency
of this repository.

### The function gap, and what closes it

The country scripts use 21 PostGIS functions. DuckDB spatial 1.5 has 17 of
them under the same names. The four it lacks all have exact substitutes:

| PostGIS | DuckDB |
| --- | --- |
| `ST_Split(line, point)` | `ST_LineLocatePoint` then `ST_LineSubstring` twice |
| `ST_AddPoint` + `ST_LineLocateN` | not needed - `ST_LineSubstring` inserts the vertex at the cut |
| `ST_SetPoint(line, n, point)` | rebuild the vertex list with `ST_PointN` and `ST_MakeLine` |
| `ST_RemovePoint` | as above |
| `pgr_dijkstra` | `igraph.Graph.get_shortest_path` |
| `ST_SetSRID` | `ST_SetCRS`, or nothing - everything is already EPSG:4326 |

`primitives.py` implements all six and checks each against a worked example.
The split is exact: a 331,725.87 m edge cut in two gives parts of 176,919.30 m
and 154,806.57 m, summing to 331,725.87 m.

### Measured on the real network

`prepare_network.py` is `afrn.sql`, ported. It asserts the row counts that
`afrn.sql` records in its own comments, and reproduces every one:

| Check | afrn.sql | This port |
| --- | --- | --- |
| Nodes after the country join | 154,953 | 154,953 |
| Node ids duplicated by the join | 2 | 2 |
| Edges before the country join | 135,473 | 135,473 |
| Edges after the country join | 135,512 | 135,512 |
| Edge ids duplicated by the join | 39 | 39 |
| Edges after resolving cross-border duplicates | 135,473 | 135,473 |

It produces 120,929 route km, of which 119,162 edges are open.

Timings, on the whole continent:

| Step | Time |
| --- | --- |
| Load the GeoPackage and boundaries | 7s |
| Assign country to 154,951 nodes | 209s |
| Assign country to 135,473 edges | 326s |
| Resolve cross-border edges | 16s |
| Derive oids, lengths, attributes | 1s |
| Build the routing graph (154,951 vertices) | 0.5s |
| One shortest path across South Africa (474 edges, 479 km) | 0.04s |

Nine and a half minutes, and the two point-in-polygon joins are all of it.
Worth optimising before the country scripts run on top - both are joins
against 59 boundaries and should be bounded by a bounding-box prefilter.

Routing is not the problem it looked like: 1,060 shortest paths at 40 ms is
under a minute. The updates around them cost more than the paths do, and
should be batched rather than run one statement at a time.

### One discrepancy

`afrn.sql` finds 4 nodes with no country and names them. This port finds 278.
266 of them are on Réunion, which is missing from the boundaries file in the
repository - so the `africa_osm_countries` table the SQL ran against was not
exactly the GeoJSON that shipped. The remaining 12 are scattered coastal and
near-border nodes. Nothing on Réunion reaches the published network, which
names 39 countries, all of them present in the boundaries file. Low risk, but
it means the shipped boundaries are close to, not identical to, what was used.

## Why a rebuild from current OSM is a different project

The ids everything is keyed on are not OSM ids. `rail_africa_preprocess.sh`
runs `osmium tags-filter` and `ogr2ogr`, then `process_rail.py` builds a snkit
network and calls `snkit.network.add_ids(..., edge_prefix="rail_africa")`,
which numbers features **by row position**. The oid is `555000000` plus that
number. So an id depends on the extract's contents, on snkit's snapping and
splitting, and on row order.

The country scripts carry 6,276 hard-coded oid references, 4,503 of them
distinct: 3,988 from that numbering and 515 created by the `rn_*` functions
(`oid + 1000000` for copied nodes, `oid || row_number` for split parts). Re-run
the preprocessing on a 2026 extract and every one of them points at a
different feature - silently, because the ids still exist.

There is a way through, and it is the reason to keep `osm_id` in the port:
`africa-rail.gpkg` carries `osm_id` on both layers, and `afrn.sql` drops it.
`prepare_network.py` keeps it. That makes it possible to rewrite each edit from
"row 128,466" to "the way with this OSM id" - and for split-derived features,
"the way with this OSM id, at this fraction along it". That migration is
mechanical for edits on a single way, and needs judgement where OSM has since
split, merged or deleted the way. Sizing that means counting how many of the
3,988 ids still resolve against a current extract, which is a day's work and
the right next question if a rebuild is ever wanted.

## The blocker nobody mentions in the README

The country scripts are not runnable. They are a working notebook, executed a
statement at a time in a database GUI:

- 17 of the 24 begin with `update rubbish set rubish` - a deliberate syntax
  error, commented "trap running entire script".
- 73 statements are unfilled templates (`where oid = ;`, `in ()`).
- 1,345 statements are exploratory `select`s whose results informed the next
  edit and are not part of the build.

So the port cannot be "run the SQL through DuckDB". Each file has to be read
and the load-bearing statements separated from the notebook around them. That
is the bulk of the 3-6 weeks, and it is the same work whatever engine runs the
result. It is also the main argument *for* doing it: the current state is a
build no one can repeat, and the port makes it a build that runs from files.

Per-country, so the work can be split up:

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

South Africa alone is a third of it.

## Proposed decomposition

Six rules, each reading files and writing files:

1. `rail_prepare_network` - `afrn.sql`. Written, see `prepare_network.py`.
   Inputs: the snkit GeoPackage and the boundaries. Output: a GeoPackage of
   prepared nodes and edges.
2. `rail_country_edits` - one wildcard rule per country, reading a country's
   edits and applying them. Output: that country's nodes and edges.
3. `rail_combine_countries` - concatenate the 24 outputs.
4. `rail_merge_hvt` - the East Africa merge and renumbering from
   `generate_combined_network.sql`, including the three border joins.
5. `rail_normalise` - the facility, status and country-name lookups. These are
   pure value mappings and belong in a CSV the rule reads, not in code.
6. `rail_electrification` - the electrified flag, which is part rule-based on
   the comment text and part three routed paths.

The edits themselves want to be data, not Python. The natural form is one file
per country of records like `{op: tag_route, source: ..., target: ...,
line: ..., gauge: ...}`, which makes them diffable, reviewable by someone who
knows the railways rather than the code, and re-keyable to OSM ids later
without touching the code that applies them.

## Before starting

**The trg-rail repository has no licence.** No `LICENSE` file, no statement in
its README. Its data is OSM-derived, so ODbL terms reach the network, but the
SQL and the research behind it are unlicensed. Nothing here copies it - the
code in this directory reimplements the operations - but vendoring the SQL, or
deriving country edit files from it, needs asking first. That is the first
action item, before any of the estimates above mean anything.

## Running the spike

Needs `duckdb` and `igraph`; only igraph is in `environment.yml`, because none
of this is wired into the workflow.

```bash
pip install duckdb
python primitives.py           # check each PostGIS substitution
```

`prepare_network.py` needs a clone of the trg-rail repository:

```bash
git clone https://github.com/trg-rail/africa_rail_network /tmp/africa_rail_network
python prepare_network.py \
    --rail-network /tmp/africa_rail_network/data/africa-rail.gpkg \
    --boundaries /tmp/africa_rail_network/data/osm_admin_boundaries_africa.geojson \
    --database /tmp/rail.duckdb
```

It exits non-zero if any of `afrn.sql`'s counts stop matching. Allow ten
minutes.

[trg-rail]: https://github.com/trg-rail/africa_rail_network
