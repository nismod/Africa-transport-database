# Country edit files

One file per script in `countries_sql_scripts`, transcribed by
`parse_country_sql.py`. Each is the list of statements from that script that
change the published network, as data. `apply_country_edits.py` replays one
onto the network `prepare_network.py` builds.

`gabon.yaml` is the reference: it was written by hand before the parser
existed, and replaying it reproduces the published Gabon network exactly.
`transcribe_all.py` re-parses `gabon.sql` on every run and fails if the parser
stops agreeing with it.

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission.

## Status

`gaps` counts statements the parser would not guess at. They are listed with
their line numbers by `parse_country_sql.py --verbose`.

This table is about *transcription*. For how the edits then behave when they
are replayed onto the prepared network - 3,651 of 3,685 applied, 822 of 906
lines reproduced - run `verify_all.py`, or see "Replayed against the published
network" in [`../README.md`](../README.md).

| script | lines | edits | skipped | gaps |
| --- | ---: | ---: | ---: | ---: |
| [`algeria.yaml`](algeria.yaml) | 1,888 | 228 | 13 | 1 |
| [`angola.yaml`](angola.yaml) | 660 | 101 | 16 |  |
| [`botswana.yaml`](botswana.yaml) | 577 | 44 | 16 |  |
| [`cameroon.yaml`](cameroon.yaml) | 296 | 29 | 15 |  |
| [`congo_brazzaville.yaml`](congo_brazzaville.yaml) | 273 | 21 | 15 |  |
| [`drc.yaml`](drc.yaml) | 1,005 | 95 | 16 |  |
| [`egypt.yaml`](egypt.yaml) | 1,970 | 234 | 23 | 1 |
| [`eritrea_djibouti_ethiopia.yaml`](eritrea_djibouti_ethiopia.yaml) | 577 | 51 | 16 |  |
| [`eswatini.yaml`](eswatini.yaml) | 484 | 38 | 16 |  |
| [`gabon.yaml`](gabon.yaml) | 212 | 19 | 15 |  |
| [`kenya.yaml`](kenya.yaml) * | 816 | 41 | 14 | 14 |
| [`malawi.yaml`](malawi.yaml) | 1,016 | 98 | 17 |  |
| [`morocco.yaml`](morocco.yaml) | 1,080 | 104 | 7 | 1 |
| [`mozambique.yaml`](mozambique.yaml) | 2,275 | 259 | 22 |  |
| [`namibia.yaml`](namibia.yaml) | 742 | 88 | 16 |  |
| [`nigeria.yaml`](nigeria.yaml) | 675 | 67 | 17 |  |
| [`south_africa.yaml`](south_africa.yaml) | 11,085 | 1,296 | 25 |  |
| [`sudan.yaml`](sudan.yaml) | 614 | 56 | 21 |  |
| [`tanzania.yaml`](tanzania.yaml) * | 905 | 47 | 18 | 13 |
| [`tunisia.yaml`](tunisia.yaml) | 2,825 | 410 | 20 |  |
| [`uganda.yaml`](uganda.yaml) * | 611 | 24 | 14 | 10 |
| [`west_africa_ex_nigeria.yaml`](west_africa_ex_nigeria.yaml) | 1,800 | 174 | 37 |  |
| [`zambia.yaml`](zambia.yaml) * | 695 | 28 | 15 | 9 |
| [`zimbabwe.yaml`](zimbabwe.yaml) | 2,309 | 273 | 17 |  |
| **24 scripts** | **35,390** | **3,825** | **421** | **49** |

`*` runs on its own tables, not the continental ones - see below.

## Operations

| operation | count |
| --- | ---: |
| `tag_route` | 1,015 |
| `set_node` | 983 |
| `split_edge` | 780 |
| `copy_node` | 579 |
| `insert_edge` | 158 |
| `insert_node_at` | 105 |
| `set_edge` | 64 |
| `set_nodes_on_edges` | 40 |
| `set_nodes` | 26 |
| `change_target` | 20 |
| `set_edges` | 20 |
| `change_source` | 19 |
| `split_name_script` | 6 |
| `set_all_edges` | 4 |
| `delete_edge` | 3 |
| `delete_node` | 2 |
| `copy_node_column` | 1 |

## Statements skipped

None of these can reach the published network.

| reason | count |
| --- | ---: |
| exploratory | 153 |
| template | 119 |
| schema | 44 |
| routing test | 41 |
| backup | 40 |
| trap | 17 |
| recomputed length | 7 |

## The four that came through the HVT pipeline

Kenya, Tanzania, Uganda and Zambia are a separate case. Their scripts edit
`<country>_osm_edges` and `<country>_osm_nodes`, built from per-country OSM
extracts, and `data/old_hvt/generate_combined_network.sql` unions those four
into `hvt_rail_network`. The current `generate_combined_network.sql` re-keys
that (`oid + 666600000000` for edges, `+ 660000000` for nodes) and unions it
with `africa_osm_edges`. So these four came through an earlier pipeline, and
their ids are in a different space from every other script's.

Their edits are transcribed here for the record, but they cannot be replayed:
the per-country tables are not in the repo, and their stage-1 equivalent is
the part of each script this parser reports rather than transcribes - deriving
`oid`, `source` and `target` from snkit's `from_id`/`to_id` strings.

They do not need replaying. Their output *is* shipped, as
`data/old_hvt/network.geojson`: 6,276 edges - Tanzania 2,650, Kenya 1,716,
Zambia 1,112, Uganda 798 - which is exactly what the published network carries
for those four countries. The port reads it as an input to the combine step,
which is what the original build does too.
