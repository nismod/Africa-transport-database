"""Stage 1 of the port: ``network_sql_scripts/afrn.sql`` in DuckDB.

Takes the snkit network and the country boundaries that the trg-rail
repository ships, and produces the prepared node and edge tables that the 24
country scripts then edit: countries assigned, cross-border edges resolved,
integer oids derived, lengths measured and the OSM railway tags mapped onto
status, type and structure columns.

afrn.sql records its own row counts in comments as it goes. Those counts are
asserted here, so the port is checked against the original rather than just
run. See README.md for the numbers this reproduces.

This is spike code - see README.md. It is not part of the workflow.
"""

import time

import click
from primitives import connect

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


@click.command()
@click.option("--rail-network", required=True, type=click.Path(exists=True))
@click.option("--boundaries", required=True, type=click.Path(exists=True))
@click.option("--database", required=True, type=click.Path())
def main(rail_network, boundaries, database):
    """Run afrn.sql's steps in DuckDB and check them against its own counts"""
    con = connect(database)
    checks = {}

    def step(name, sql):
        started = time.time()
        con.execute(sql)
        click.echo(f"{name:<46} {time.time() - started:6.1f}s")

    # The GeoPackage layers carry no CRS, so state it rather than transform.
    step(
        "load",
        f"""
        create or replace table raw_nodes as
        select * exclude geom, st_setcrs(geom, 'EPSG:4326') as geom
        from st_read('{rail_network}', layer = 'nodes');

        create or replace table raw_edges as
        select * exclude geom, st_setcrs(geom, 'EPSG:4326') as geom
        from st_read('{rail_network}', layer = 'edges');

        create or replace table countries as
        select name, geom from st_read('{boundaries}');
        """,
    )
    checks["edges before the country join"] = con.execute(
        "select count(*) from raw_edges"
    ).fetchone()[0]

    step(
        "assign country to nodes",
        """
        create or replace table nodes_with_country as
        select a.*, b.name as country
        from raw_nodes a left join countries b on st_intersects(a.geom, b.geom);
        """,
    )
    checks["nodes after country join"] = con.execute(
        "select count(*) from nodes_with_country"
    ).fetchone()[0]
    checks["node ids duplicated by the join"] = con.execute(
        "select count(*) from (select id from nodes_with_country"
        " group by id having count(*) > 1)"
    ).fetchone()[0]

    step(
        "assign country to edges",
        """
        create or replace table edges_with_country as
        select row_number() over () as vid, a.*, b.name as country
        from raw_edges a left join countries b on st_intersects(a.geom, b.geom);
        """,
    )
    checks["edges after the country join"] = con.execute(
        "select count(*) from edges_with_country"
    ).fetchone()[0]
    checks["edge ids duplicated by the join"] = con.execute(
        "select count(*) from (select id from edges_with_country"
        " group by id having count(*) > 1)"
    ).fetchone()[0]

    # An edge crossing a border matches more than one country. Keep the
    # country the edge runs furthest through, as afrn.sql does.
    step(
        "resolve cross-border edges",
        """
        create or replace table edges_one_country as
        with ranked as (
            select a.vid,
                rank() over (
                    partition by a.id
                    order by st_length_spheroid(st_intersection(a.geom, b.geom)) desc
                ) as rank
            from edges_with_country a
            left join countries b on a.country = b.name
            where a.id in (
                select id from edges_with_country group by id having count(*) > 1
            )
        )
        select * from edges_with_country
        where vid not in (select vid from ranked where rank != 1);
        """,
    )
    checks["edges after resolving cross-border duplicates"] = con.execute(
        "select count(*) from edges_one_country"
    ).fetchone()[0]

    # snkit ids are "rail_africa_<n>"; the oid is 555000000 + n. osm_id is
    # kept, which afrn.sql drops - see README.md on re-keying.
    step(
        "derive oids, lengths and attributes",
        f"""
        create or replace table nodes as
        select
            555000000 + cast(regexp_extract(id, '(\\d+)$', 1) as bigint) as oid,
            osm_id, name, railway, country,
            null::text as gauge, null::text as facility,
            geom
        from nodes_with_country;

        create or replace table edges as
        select
            555000000 + cast(regexp_extract(id, '(\\d+)$', 1) as bigint) as oid,
            555000000 + cast(regexp_extract(from_id, '(\\d+)$', 1) as bigint) as source,
            555000000 + cast(regexp_extract(to_id, '(\\d+)$', 1) as bigint) as target,
            osm_id, country,
            round(st_length_spheroid(geom)::numeric, 2) as length,
            'mixed' as mode,
            case when railway in ({sql_list(NOT_OPEN)}) then railway
                 else 'open' end as status,
            case when railway in ('rail', 'narrow_gauge') then 'conventional'
                 when railway in ({sql_list(OWN_TYPE)}) then railway
                 else 'other' end as type,
            case when bridge in ('yes', 'cantilever') then 'bridge'
                 when bridge = 'movable' then 'movable bridge'
                 when bridge in ('viaduct', 'aqueduct') then 'viaduct'
                 when railway in ({sql_list(OWN_STRUCTURE)}) then railway
                 end as structure,
            null::text as line,
            null::text as gauge,
            null::integer as speed_freight,
            null::integer as speed_passenger,
            null::text as comment,
            geom
        from edges_one_country;
        """,
    )

    click.echo("\nagainst afrn.sql's own recorded counts")
    failures = 0
    for name, expected in EXPECTED.items():
        actual = checks[name]
        ok = actual == expected
        failures += not ok
        click.echo(
            f"  {'ok ' if ok else 'MISMATCH'} {name:<46} {actual:>8,} (afrn.sql: {expected:,})"
        )

    click.echo("\nprepared network")
    click.echo(
        f"  edges            {con.execute('select count(*) from edges').fetchone()[0]:>10,}"
    )
    click.echo(
        f"  nodes            {con.execute('select count(*) from nodes').fetchone()[0]:>10,}"
    )
    click.echo(
        f"  route km         {con.execute('select round(sum(length) / 1000) from edges').fetchone()[0]:>10,.0f}"
    )
    click.echo(
        "  status           "
        + ", ".join(
            f"{status} {count:,}"
            for status, count in con.execute(
                "select status, count(*) from edges group by status order by 2 desc"
            ).fetchall()
        )
    )
    click.echo(
        f"\n  nodes with no country: "
        f"{con.execute('select count(*) from nodes where country is null').fetchone()[0]:,}"
        " (afrn.sql found 4 - see README.md)"
    )

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
