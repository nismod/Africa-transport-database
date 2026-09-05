# Porting the trg-rail build to a local script

Scoping the question raised against `rules/download.smk`: the rail network
comes from [trg-rail/africa_rail_network][trg-rail] as published GeoJSON, and
its build runs in PostgreSQL/PostGIS with pgRouting. Could that build be
ported to explicit steps in a local script - a single-node SQL engine over
files - so it fits the snakemake workflow without a Postgres dependency?

**Short answer.** Yes, on SedonaDB. It does the geometry, igraph does the
routing, and both are proved below against the real data. "Port the SQL" turns
out to be two different projects, and only one of them is a port:

- **Replaying the recorded build** on the inputs it was written against is
  feasible and worth doing. Everything it needs is in the trg-rail repository.
  Stage 1 is written, passes every count the original records, and runs in 14
  seconds. Estimate: **3-6 weeks**, most of it on the 24 country scripts.
- **Rebuilding from a current OSM extract** is not a port. The 4,503
  hand-picked feature ids the country scripts are keyed on are row numbers
  from a 2021 snkit run, and cannot be reproduced from a 2026 extract. This
  needs the edits re-keyed to OSM ids first, which is a data migration on top
  of the port, and lossy where OSM has since changed. Estimate: **the port,
  plus 4-8 weeks**, with an accuracy cost that has to be measured.

Recommendation: do the replay port when the network next needs changing rather
than refreshing - it converts an unrepeatable GUI session into something
reviewable, which is what makes the research maintainable. Until then keep
pinning the published GeoJSON at a commit. Treat the rebuild as a separate
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

## Which engine

SedonaDB - the single-node Rust engine, not Sedona on Spark. Both it and
DuckDB give SQL over files with no server, and `prepare_network.py` runs the
same steps on either (`--engine duckdb`, `--engine sedonadb`) so the two can
be timed side by side. On the whole continent:

| Step | DuckDB 1.5.5 | SedonaDB 0.4.1 |
| --- | ---: | ---: |
| Load the network and boundaries | 11.9s | 10.4s |
| Assign country to 154,951 nodes | 207.0s | 1.4s |
| Assign country to 135,473 edges | 295.4s | 1.4s |
| Resolve 39 cross-border edges | 0.5s | 0.9s |
| Derive oids and attributes | 0.7s | 0.1s |
| **Total** | **515.7s** | **14.2s** |

Identical results on both, including all six of `afrn.sql`'s own row counts.
The difference is entirely the point-in-polygon joins, which are the whole
cost of this stage - 36x on the run, 148x and 211x on the joins themselves.

That is not DuckDB being used wrongly. Its plan shows a `SPATIAL_JOIN`
operator, so it is taking the intended path; an `ST_Intersects_Extent`
prefilter makes it worse (559s) by defeating that operator, and a hand-written
bounding-box prefilter gets the node join to 19.2s - still 11x slower than
SedonaDB with no tuning at all.

Apache Sedona on Spark was the other candidate and is the wrong shape: a JVM,
a Spark session, and GraphFrames for the routing, on a 135k-edge network.
SedonaDB is one Python package and runs in-process.

### What each engine can and cannot do

The country scripts use 21 PostGIS functions. Both engines have 17 of them
under the same names, and neither has `ST_Split`, `ST_AddPoint`,
`ST_LineLocateN` or `ST_SetPoint`. The substitutions:

| PostGIS | DuckDB | SedonaDB |
| --- | --- | --- |
| `ST_Split(line, point)` | `ST_LineLocatePoint` then `ST_LineSubstring` twice | same |
| `ST_AddPoint` + `ST_LineLocateN` | not needed - `ST_LineSubstring` inserts the vertex at the cut | same |
| `ST_ClosestPoint` | native | registered but has no kernel for two geometries; `ST_LineInterpolatePoint(line, ST_LineLocatePoint(line, point))` gives the same point |
| `ST_SetPoint(line, n, point)` | rebuild the vertex list with `ST_PointN` and `ST_MakeLine` | **no equivalent** - `ST_MakeLine` takes two geometries, not a list |
| `ST_SetSRID` | not present; `ST_SetCRS` | native |
| `pgr_dijkstra` | `igraph.Graph.get_shortest_path` | same |

`primitives.py` implements all six operations the plpgsql functions provide,
checks each against a worked example, and then asks both engines the same
expressions. Only the `ST_SetPoint` rebuild fails to port, and it is 30 calls
upstream - do those in Python, or on DuckDB.

Two other SedonaDB rough edges, both worked around in `prepare_network.py`:

- Carrying geometry columns through a large join overflows Arrow's 32-bit
  offsets (`Offset overflow error: 2151937982`). Project the spatial joins
  down to ids and attach the rest afterwards. That is better SQL on either
  engine anyway.
- Filters do not push into the build side of a join, so restricting to the 39
  cross-border edges has to be materialised first rather than left as a
  predicate.

It has no GDAL reader of its own, so GeoPackage comes in through geopandas and
pyogrio, and goes back out the same way; GeoParquet is native. Tables live in
memory rather than in a database file, which suits a workflow that passes
files between rules.

### Neither engine measures length like PostGIS

The published lengths come from PostGIS `ST_LengthSpheroid`, and this is where
the port could have gone quietly wrong:

- **DuckDB's `ST_Length_Spheroid` takes its coordinates as (latitude,
  longitude)**, the opposite way round from PostGIS. Fed lon/lat it returns
  lengths 15% out at South African latitudes, with no error. Wrapping the
  geometry in `ST_FlipCoordinates` fixes it, and then it agrees with the
  published numbers on 94.8% of shared edges to the centimetre.
- **SedonaDB's `ST_Length` over a geography is a sphere**, not the WGS84
  ellipsoid, and runs 0.1-0.3% out.

So `prepare_network.py` measures lengths with pyproj instead, which agrees
with the published numbers on **99.93%** of the 42,489 shared edges to the
centimetre and takes 2.9 seconds for the whole continent. Only 19 edges differ
by more than a metre, and those are the ones whose endpoints the country
scripts moved.

The lesson generalises: check each spatial function against the published
output rather than against its name.

### Measured on the real network

`prepare_network.py` is `afrn.sql`, ported. It asserts the row counts that
`afrn.sql` records in its own comments, and reproduces every one on both
engines:

| Check | afrn.sql | This port |
| --- | --- | --- |
| Nodes after the country join | 154,953 | 154,953 |
| Node ids duplicated by the join | 2 | 2 |
| Edges before the country join | 135,473 | 135,473 |
| Edges after the country join | 135,512 | 135,512 |
| Edge ids duplicated by the join | 39 | 39 |
| Edges after resolving cross-border duplicates | 135,473 | 135,473 |

It produces 120,201 route km, of which 119,162 edges are open.

Routing is not the problem it looked like: igraph builds the 154,951-vertex
graph in 0.5s and answers a real 474-edge path across South Africa in 40ms, so
the 1,060 routed updates cost under a minute. The updates around them cost
more than the paths do, and want batching rather than one statement at a time.

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
split, merged or deleted the way. Sizing it means counting how many of the
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

So the port cannot be "run the SQL through SedonaDB". Each file has to be read
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

## Attribution

The trg-rail repository carries no licence file, and its author has confirmed
that adapting the build and deriving country edit files from it is fine, with
explicit attribution wherever it is included. So each file here carries a line
saying what it is derived from, and any country edit files produced by the
port should carry the same, naming the trg-rail script they came from. The
underlying geometry is OpenStreetMap, so ODbL terms reach the network itself.

## Running the spike

Needs `duckdb`, `sedonadb`, `igraph` and `pyproj`; only the last two are in
`environment.yml`, because none of this is wired into the workflow.

```bash
pip install duckdb sedonadb
python primitives.py           # check each substitution, on both engines
```

`prepare_network.py` needs a clone of the trg-rail repository:

```bash
git clone https://github.com/trg-rail/africa_rail_network /tmp/africa_rail_network
python prepare_network.py --engine sedonadb \
    --rail-network /tmp/africa_rail_network/data/africa-rail.gpkg \
    --boundaries /tmp/africa_rail_network/data/osm_admin_boundaries_africa.geojson
```

It exits non-zero if any of `afrn.sql`'s counts stop matching. Fifteen seconds
on SedonaDB, nine minutes on DuckDB.

[trg-rail]: https://github.com/trg-rail/africa_rail_network
