# Porting the trg-rail build to a local script

Scoping the question raised against `rules/download.smk`: the rail network
comes from [trg-rail/africa_rail_network][trg-rail] as published GeoJSON, and
its build runs in PostgreSQL/PostGIS with pgRouting. Could that build be
ported to explicit steps in a local script - a single-node SQL engine over
files - so it fits the snakemake workflow without a Postgres dependency?

**Short answer.** Yes. Both stages of the build are now written and checked
against the original, on the real data:

- **Stage 1** (`prepare_network.py`) reproduces every row count `afrn.sql`
  records in its own comments, in 14 seconds on SedonaDB.
- **Stage 2** (`apply_country_edits.py`) replays a country's edits from a data
  file. Gabon reproduces the published network exactly - all three lines,
  matching on both edge count and length - in 1.3 seconds.

That settles feasibility. What is left is transcription: the 24 country
scripts hold roughly 3,200 edits that have to be read out of a notebook and
written down as data.

"Port the SQL" is still two different projects, and only one of them is a
port:

- **Replaying the recorded build** on the inputs it was written against.
  Everything it needs is in the trg-rail repository. Estimate: **3-6 weeks**,
  almost all of it transcription, and partly automatable - see below.
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

What the country scripts actually contain, counting only live statements
(comments stripped, so commented-out work does not inflate the numbers):

| | Count |
| --- | --- |
| Statements | 4,075 |
| `update`, real | 1,159 |
| `update`, unfilled templates | 73 |
| `update rubbish set rubish` (the trap) | 17 |
| `pgr_dijkstra` routes, real | 758 |
| `pgr_dijkstra` routes with a blank endpoint | 7 |
| `split_edge` operations | 677 |
| `copy_node` operations | 464 |
| `insert_edge` operations | 108 |
| `change_source` / `change_target` | 30 |
| Bare exploratory `select` | 1,345 |
| **Estimated real edits** | **3,196** |

The dominant pattern is one shape: route between two node ids, then set line,
gauge, status, mode and comment on every edge along the path. Most route over
the whole edge table or one country's edges; the rest add a short exclusion
list to steer the path.

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

### The engine choice only covers stage 1

Stage 2 is not set-based. It is 3,196 row-at-a-time edits, and the geometry
surgery among them is done in **shapely**, not in SQL, because neither engine
can be trusted with it:

- Neither DuckDB spatial 1.5 nor SedonaDB 0.4 has `ST_Split`, `ST_AddPoint`,
  `ST_LineLocateN` or `ST_SetPoint`. `ST_LineLocatePoint` with
  `ST_LineSubstring` substitutes for the first three, on both.
- **DuckDB's `ST_LineSubstring` then returns a geometry beginning `-nan
  -nan`** when the line starts with a repeated vertex - which its own previous
  substring produced. Splits chain in this build (an edge split at a station
  is split again for the next station), so the second split of a chain
  produces a NaN geometry and a NaN length, silently, surfacing later as a
  cast error. SedonaDB and shapely both handle the same input correctly and
  agree with each other.
- SedonaDB registers `ST_ClosestPoint` but has no kernel for two geometries;
  `ST_LineInterpolatePoint` at the located fraction gives the same point.
- SedonaDB's `ST_MakeLine` takes two geometries rather than a list, so the
  `ST_SetPoint` rebuild has no SQL form there at all.

Splits and copies are inherently one-feature-at-a-time - 1,141 of them - so
shapely is the natural tool regardless, and it keeps `primitives.py` working
against either engine's tables. Two other SedonaDB rough edges, both worked
around in `prepare_network.py`: carrying geometry columns through a large join
overflows Arrow's 32-bit offsets, and filters do not push into the build side
of a join.

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

So lengths are measured with pyproj throughout, which agrees with the
published numbers on **99.93%** of the 42,489 shared edges to the centimetre
and takes 2.9 seconds for the whole continent. Only 19 edges differ by more
than a metre, and those are the ones whose endpoints the country scripts
moved.

The lesson generalises: check each spatial function against the published
output rather than against its name.

## Stage 1, measured

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

One discrepancy: `afrn.sql` finds 4 nodes with no country and names them, this
port finds 278. 266 of them are on Réunion, which is missing from the
boundaries file in the repository - so the `africa_osm_countries` table the SQL
ran against was not exactly the GeoJSON that shipped. The remaining 12 are
scattered coastal and near-border nodes. Nothing on Réunion reaches the
published network, which names 39 countries, all of them present in the
boundaries file. Low risk, but the shipped boundaries are close to, not
identical to, what was used.

## Stage 2, proved on Gabon

`edits/gabon.yaml` is what `countries_sql_scripts/gabon/gabon.sql` reduces to:
**19 edits from 211 lines**. The rest of that file is notebook - exploratory
selects, unfilled templates, the syntax-error trap, two backup table copies
and a routing test with its endpoints left blank.

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

## What the remaining work looks like

The 3,196 edits are not uniform in difficulty. 1,899 of them - the routes,
splits and copies - are written in a handful of rigid shapes:

```sql
select rn_copy_node(array[555022945], array[555094368]);

with tmp as (SELECT X.* FROM pgr_dijkstra('SELECT oid as id, ...', A, B, false) ...)
update africa_osm_edges set line = '...', gauge = '...' where oid in (select edge from tmp);
```

A parser for those shapes would produce most of each country's edit file
mechanically, leaving the 1,159 real `update` statements and the 15 anonymous
`DO` blocks to be read by hand. That is the difference between the low and
high ends of the 3-6 week estimate, and it is worth writing the parser first
against Gabon, where the answer is already known.

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

(Raw counts including comments, which is why they exceed the live-statement
table above.) South Africa alone is a third of it.

## Proposed decomposition

Six rules, each reading files and writing files:

1. `rail_prepare_network` - `afrn.sql`. **Written**, `prepare_network.py`.
   Inputs: the snkit GeoPackage and the boundaries. Output: prepared nodes and
   edges.
2. `rail_country_edits` - one wildcard rule per country, applying that
   country's edit file. **Written**, `apply_country_edits.py`; one of 24 edit
   files exists.
3. `rail_combine_countries` - concatenate the 24 outputs.
4. `rail_merge_hvt` - the East Africa merge and renumbering from
   `generate_combined_network.sql`, including the three border joins.
5. `rail_normalise` - the facility, status and country-name lookups. These are
   pure value mappings and belong in a CSV the rule reads, not in code.
6. `rail_electrification` - the electrified flag, which is part rule-based on
   the comment text and part three routed paths.

Keeping the edits as data rather than Python is what makes this worth doing:
`edits/gabon.yaml` is diffable, reviewable by someone who knows the railways
rather than the code, and re-keyable to OSM ids later without touching the
code that applies it.

## Why a rebuild from current OSM is a different project

The ids everything is keyed on are not OSM ids. `rail_africa_preprocess.sh`
runs `osmium tags-filter` and `ogr2ogr`, then `process_rail.py` builds a snkit
network and calls `snkit.network.add_ids(..., edge_prefix="rail_africa")`,
which numbers features **by row position**. The oid is `555000000` plus that
number. So an id depends on the extract's contents, on snkit's snapping and
splitting, and on row order.

The country scripts carry 6,276 hard-coded oid references, 4,503 of them
distinct: 3,988 from that numbering and 515 created by the `rn_*` functions.
Re-run the preprocessing on a 2026 extract and every one of them points at a
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

## Attribution

The trg-rail repository carries no licence file, and its author has confirmed
that adapting the build and deriving country edit files from it is fine, with
explicit attribution wherever it is included. So each file here carries a line
saying what it is derived from, and `edits/gabon.yaml` names the script it
came from. The underlying geometry is OpenStreetMap, so ODbL terms reach the
network itself.

## Running the spike

Needs `duckdb`, `sedonadb`, `igraph`, `pyproj`, `shapely` and `pyyaml`; only
the last four are in `environment.yml`, because none of this is wired into the
workflow.

```bash
pip install duckdb sedonadb
python primitives.py           # check each operation, and both engines
```

The rest needs a clone of the trg-rail repository:

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

Both exit non-zero if they stop matching the original. Stage 1 takes fifteen
seconds on SedonaDB and nine minutes on DuckDB - but stage 2 needs the tables
in a file, so run stage 1 on DuckDB when the two are chained, or write the
prepared network out to GeoPackage in between.

[trg-rail]: https://github.com/trg-rail/africa_rail_network
