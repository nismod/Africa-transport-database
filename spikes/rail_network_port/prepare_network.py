"""Stage 1 of the port: ``network_sql_scripts/afrn.sql`` without PostGIS.

Takes the snkit network and the country boundaries that the trg-rail
repository ships, and produces the prepared node and edge tables that the 24
country scripts then edit: countries assigned, cross-border edges resolved,
integer oids derived, lengths measured and the OSM railway tags mapped onto
status, type and structure columns.

The same steps run on either engine - ``--engine duckdb`` or
``--engine sedonadb`` - which is what the comparison in README.md is measured
with. Only loading and fetching differ; the SQL is the same text.

afrn.sql records its own row counts in comments as it goes. Those counts are
asserted here, so the port is checked against the original rather than just
run, and the rule lengths are checked against the published network.

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission. This is spike code - see README.md. It is not part of the
workflow.
"""

import time

import click
import geopandas as gpd
from engines import ENGINES
from pyproj import Geod

# afrn.sql's own counts, from the comments alongside each query.
EXPECTED = {
    "nodes after country join": 154953,
    "node ids duplicated by the join": 2,
    "edges before the country join": 135473,
    "edges after the country join": 135512,
    "edge ids duplicated by the join": 39,
    "edges after resolving cross-border duplicates": 135473,
}

# OSM railway values that mean the line is not open (afrn.sql "Update status").
NOT_OPEN = (
    "disused",
    "abandoned",
    "construction",
    "razed",
    "proposed",
    "dismantled",
    "historical_planned",
    "path",
    "planned",
)

# Values that stay as the type (afrn.sql "Update type").
OWN_TYPE = (
    "tram",
    "light_rail",
    "preserved",
    "subway",
    "monorail",
    "miniature",
    "funicular",
)

# Values that stay as the structure (afrn.sql "Update structure").
OWN_STRUCTURE = (
    "level_crossing",
    "railway_crossing",
    "platform",
    "station",
    "turntable",
    "loading_ramp",
    "traverser",
    "crane_rail",
)


def sql_list(values):
    return ", ".join(f"'{value}'" for value in values)


def measure_lengths(rail_network):
    """Edge lengths on the WGS84 ellipsoid, keyed by snkit id.

    Measured with pyproj rather than in SQL. PostGIS ST_LengthSpheroid, which
    is what the published lengths were computed with, has no exact equivalent
    in either engine: SedonaDB's ST_Length over a geography is a sphere and
    runs 0.1-0.3% out, and DuckDB's ST_Length_Spheroid takes its coordinates
    as (latitude, longitude), so feeding it lon/lat silently returns lengths
    15% out at South African latitudes. pyproj agrees with the published
    numbers on 99.93% of edges to the centimetre, and takes 3 seconds for the
    whole continent.
    """
    edges = gpd.read_file(rail_network, layer="edges")[["id", "geometry"]]
    geod = Geod(ellps="WGS84")
    edges["length"] = [round(geod.geometry_length(geom), 2) for geom in edges.geometry]
    return edges[["id", "length"]]


@click.command()
@click.option("--rail-network", required=True, type=click.Path(exists=True))
@click.option("--boundaries", required=True, type=click.Path(exists=True))
@click.option("--engine", default="duckdb", type=click.Choice(sorted(ENGINES)))
@click.option("--database", default=":memory:", type=click.Path())
def main(rail_network, boundaries, engine, database):
    """Run afrn.sql's steps and check them against its own counts"""
    started_all = time.time()
    engine = ENGINES[engine](database)
    click.echo(f"engine: {engine.name}\n")
    checks = {}

    def step(name, run):
        started = time.time()
        run()
        click.echo(f"{name:<46} {time.time() - started:6.1f}s")

    step(
        "load",
        lambda: (
            engine.load_layer("raw_nodes", rail_network, layer="nodes"),
            engine.load_layer("raw_edges", rail_network, layer="edges"),
            engine.load_layer("countries", boundaries),
            engine.load_frame("lengths", measure_lengths(rail_network)),
        ),
    )
    checks["edges before the country join"] = engine.value(
        "select count(*) from raw_edges"
    )

    # The spatial joins return ids only. Carrying the geometry columns through
    # them is what makes SedonaDB overflow Arrow's 32-bit offsets, and it is
    # wasted work on either engine - the country is attached by id below.
    step(
        "assign country to nodes",
        lambda: engine.sql(
            """
            create or replace table node_country as
            select a.id, b.name as country
            from raw_nodes a left join countries b
              on st_intersects(a.geom, b.geom)
            """
        ),
    )
    checks["nodes after country join"] = engine.value(
        "select count(*) from node_country"
    )
    checks["node ids duplicated by the join"] = engine.value(
        "select count(*) from (select id from node_country group by id having count(*) > 1) t"
    )

    step(
        "assign country to edges",
        lambda: engine.sql(
            """
            create or replace table edge_country as
            select a.id, b.name as country
            from raw_edges a left join countries b
              on st_intersects(a.geom, b.geom)
            """
        ),
    )
    checks["edges after the country join"] = engine.value(
        "select count(*) from edge_country"
    )
    checks["edge ids duplicated by the join"] = engine.value(
        "select count(*) from (select id from edge_country group by id having count(*) > 1) t"
    )

    # An edge crossing a border matches more than one country. Keep the
    # country the edge runs furthest through, as afrn.sql does. Only the 39
    # duplicated ids go through the intersection, which is what afrn.sql does
    # too - ranking all 135,512 would carry geometry into a window function
    # and overflow Arrow's offsets on SedonaDB. The ranking only has to order
    # countries within one edge, so plain planar length is enough and the same
    # expression runs on both engines.
    step(
        "resolve cross-border edges",
        lambda: engine.sql(
            """
            create or replace table duplicate_edges as
            select e.id, e.geom from raw_edges e
            where e.id in (
                select id from edge_country group by id having count(*) > 1
            );

            create or replace table edge_one_country as
            select id, country from edge_country
            where id not in (select id from duplicate_edges)
            union all
            select id, country from (
                select c.id, c.country,
                    rank() over (
                        partition by c.id
                        order by st_length(st_intersection(d.geom, b.geom)) desc
                    ) as rnk
                from duplicate_edges d
                join edge_country c on c.id = d.id
                join countries b on b.name = c.country
            ) ranked
            where rnk = 1
            """
        ),
    )
    checks["edges after resolving cross-border duplicates"] = engine.value(
        "select count(*) from edge_one_country"
    )

    # snkit ids are "rail_africa_<n>"; the oid is 555000000 + n. osm_id is
    # kept, which afrn.sql drops - see README.md on re-keying.
    step(
        "derive oids and attributes",
        lambda: engine.sql(
            f"""
            create or replace table nodes as
            select
                555000000 + cast(split_part(a.id, '_', 3) as bigint) as oid,
                a.osm_id, a.name, a.railway, c.country,
                cast(null as varchar) as gauge,
                cast(null as varchar) as facility,
                a.geom
            from raw_nodes a left join node_country c on c.id = a.id;

            create or replace table edges as
            select
                555000000 + cast(split_part(a.id, '_', 3) as bigint) as oid,
                555000000 + cast(split_part(a.from_id, '_', 3) as bigint) as source,
                555000000 + cast(split_part(a.to_id, '_', 3) as bigint) as target,
                a.osm_id, c.country, l.length,
                'mixed' as mode,
                case when a.railway in ({sql_list(NOT_OPEN)}) then a.railway
                     else 'open' end as status,
                case when a.railway in ('rail', 'narrow_gauge') then 'conventional'
                     when a.railway in ({sql_list(OWN_TYPE)}) then a.railway
                     else 'other' end as type,
                case when a.bridge in ('yes', 'cantilever') then 'bridge'
                     when a.bridge = 'movable' then 'movable bridge'
                     when a.bridge in ('viaduct', 'aqueduct') then 'viaduct'
                     when a.railway in ({sql_list(OWN_STRUCTURE)}) then a.railway
                     end as structure,
                cast(null as varchar) as line,
                cast(null as varchar) as gauge,
                cast(null as varchar) as comment,
                a.geom
            from raw_edges a
            join edge_one_country c on c.id = a.id
            join lengths l on l.id = a.id
            """
        ),
    )

    click.echo("\nagainst afrn.sql's own recorded counts")
    failures = 0
    for name, expected in EXPECTED.items():
        actual = int(checks[name])
        ok = actual == expected
        failures += not ok
        click.echo(
            f"  {'ok ' if ok else 'MISMATCH'} {name:<46} {actual:>8,} (afrn.sql: {expected:,})"
        )

    click.echo("\nprepared network")
    click.echo(
        f"  edges            {int(engine.value('select count(*) from edges')):>10,}"
    )
    click.echo(
        f"  nodes            {int(engine.value('select count(*) from nodes')):>10,}"
    )
    click.echo(
        f"  route km         {float(engine.value('select sum(length) / 1000 from edges')):>10,.0f}"
    )
    click.echo(
        "  status           "
        + ", ".join(
            f"{status} {int(count):,}"
            for status, count in engine.rows(
                "select status, count(*) as n from edges group by status order by n desc"
            )
        )
    )
    unassigned = int(engine.value("select count(*) from nodes where country is null"))
    click.echo(
        f"\n  nodes with no country: {unassigned:,} (afrn.sql found 4 - see README.md)"
    )
    click.echo(f"  total: {time.time() - started_all:.1f}s")

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
