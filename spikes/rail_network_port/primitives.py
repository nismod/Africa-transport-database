"""The primitives the trg-rail country SQL is built from, without PostGIS.

The upstream build runs in PostgreSQL/PostGIS with pgRouting. Everything it
uses has an equivalent here in DuckDB's spatial extension plus igraph:

    pgr_dijkstra(...)             route_edges()      igraph shortest path
    hvt.rn_split_edge(...)        split_edge()       ST_LineLocatePoint
                                                     + ST_LineSubstring
    hvt.rn_copy_node(...)         copy_node_to_edge()  ST_ClosestPoint, then
                                                       the same split
    hvt.rn_insert_edge(...)       insert_edge()      ST_MakeLine
    hvt.rn_change_source(...)     change_source()    rebuilt vertex list
    hvt.rn_change_target(...)     change_target()

Neither DuckDB spatial 1.5 nor SedonaDB 0.4 has ST_Split, ST_AddPoint,
ST_LineLocateN or ST_SetPoint, which is what the four substitutions above are
for. Both have everything the substitutions need, so the SQL here is portable;
this module is written against DuckDB because it holds tables in a file, and
``python primitives.py`` checks each substitution against a worked example and
then runs the same expressions on SedonaDB to show they agree.

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission. This is spike code - see README.md. It is not part of the
workflow.
"""

import duckdb
import igraph

# DuckDB's ST_Length_Spheroid takes its coordinates as (latitude, longitude),
# the opposite way round from PostGIS ST_LengthSpheroid. Feeding it lon/lat
# silently returns the wrong length - 15% out at South African latitudes - so
# every length here flips first. That matches PostGIS on 95% of edges to the
# centimetre; ``prepare_network.measure_lengths`` uses pyproj instead, which
# manages 99.93%.
LENGTH_M = "round(st_length_spheroid(st_flipcoordinates({geom}))::numeric, 2)"


def connect(database=":memory:"):
    """A DuckDB connection with the spatial extension loaded."""
    con = duckdb.connect(database)
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


# ---------------------------------------------------------------------------
# geometry surgery
# ---------------------------------------------------------------------------


def split_edge(con, edge_oid, node_oid, edges="edges", nodes="nodes"):
    """Split one edge at a node lying on it, as ``hvt.rn_split_edge`` does.

    PostGIS splits with ST_Split, which DuckDB has no equivalent for. Locating
    the node as a fraction along the line and cutting with ST_LineSubstring
    gives the same two parts, and inserts the vertex at the cut for free -
    which is what ``rn_copy_node`` needed ST_AddPoint and ST_LineLocateN for.

    Returns the two new oids, numbered as upstream does: the original oid with
    a row number appended.
    """
    fraction, source, target = con.execute(
        f"""
        select st_linelocatepoint(e.geom, n.geom), e.source, e.target
        from {edges} e, {nodes} n
        where e.oid = ? and n.oid = ?
        """,
        [edge_oid, node_oid],
    ).fetchone()

    # The parts are cut straight out of the stored geometry, so nothing has to
    # travel through Python as WKB and back.
    new_oids = [int(f"{edge_oid}{row}") for row in (1, 2)]
    cuts = [(0.0, fraction, source, node_oid), (fraction, 1.0, node_oid, target)]
    for new_oid, (start, stop, new_source, new_target) in zip(new_oids, cuts):
        con.execute(
            f"""
            insert into {edges} by name
            select * exclude (oid, source, target, length, geom),
                ? as oid,
                ? as source,
                ? as target,
                {LENGTH_M.format(geom="st_linesubstring(geom, ?, ?)")} as length,
                st_linesubstring(geom, ?, ?) as geom
            from {edges} where oid = ?
            """,
            [new_oid, new_source, new_target, start, stop, start, stop, edge_oid],
        )
    con.execute(f"delete from {edges} where oid = ?", [edge_oid])
    return new_oids


def copy_node_to_edge(con, node_oid, edge_oid, edges="edges", nodes="nodes"):
    """Copy a station onto the nearest point of another edge and split there.

    ``hvt.rn_copy_node``: the station keeps its attributes, gets the original
    oid plus 1000000, and sits on the line rather than beside it.
    """
    new_node = node_oid + 1000000
    con.execute(
        f"""
        insert into {nodes} by name
        select n.* exclude (oid, geom),
            ? as oid,
            st_closestpoint(e.geom, n.geom) as geom
        from {nodes} n, {edges} e
        where n.oid = ? and e.oid = ?
        """,
        [new_node, node_oid, edge_oid],
    )
    return new_node, split_edge(con, edge_oid, new_node, edges=edges, nodes=nodes)


def insert_edge(con, start_node, end_node, oid, edges="edges", nodes="nodes"):
    """Join two nodes with a straight edge, as ``hvt.rn_insert_edge`` does."""
    con.execute(
        f"""
        insert into {edges} (oid, source, target, country, length, geom)
        select ?, ?, ?, a.country,
            {LENGTH_M.format(geom="st_makeline(a.geom, b.geom)")},
            st_makeline(a.geom, b.geom)
        from {nodes} a, {nodes} b
        where a.oid = ? and b.oid = ?
        """,
        [oid, start_node, end_node, start_node, end_node],
    )
    return oid


def _move_end(con, edge_oid, node_oid, end, edges, nodes):
    """ST_SetPoint on the first or last vertex, by rebuilding the vertex list."""
    keep = (
        "list_prepend(n.geom, [st_pointn(e.geom, i::int) "
        "for i in range(2, st_npoints(e.geom) + 1)])"
        if end == "source"
        else "list_append([st_pointn(e.geom, i::int) "
        "for i in range(1, st_npoints(e.geom))], n.geom)"
    )
    con.execute(
        f"""
        update {edges} set
            geom = (select st_makeline({keep}) from {edges} e, {nodes} n
                    where e.oid = ? and n.oid = ?),
            {end} = ?
        where oid = ?
        """,
        [edge_oid, node_oid, node_oid, edge_oid],
    )


def change_source(con, edge_oid, node_oid, edges="edges", nodes="nodes"):
    """Move an edge's first vertex onto a node - ``hvt.rn_change_source``."""
    _move_end(con, edge_oid, node_oid, "source", edges, nodes)


def change_target(con, edge_oid, node_oid, edges="edges", nodes="nodes"):
    """Move an edge's last vertex onto a node - ``hvt.rn_change_target``."""
    _move_end(con, edge_oid, node_oid, "target", edges, nodes)


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


class RouteGraph:
    """The edge table as a routable graph, standing in for pgRouting.

    The country scripts call ``pgr_dijkstra`` 1,060 times, almost always in
    one shape: take the least-cost path between two node oids weighted by
    edge length, then set attributes on every edge along it.
    """

    def __init__(self, con, edges="edges", where=None):
        rows = con.execute(
            f"select oid, source, target, length from {edges}"
            + (f" where {where}" if where else "")
        ).fetchall()
        self.graph = igraph.Graph.TupleList(
            [(row[1], row[2]) for row in rows], directed=False
        )
        self.graph.es["cost"] = [float(row[3]) for row in rows]
        self.graph.es["oid"] = [row[0] for row in rows]

    def route_edges(self, source, target):
        """The oids of the edges on the least-cost path between two nodes."""
        path = self.graph.get_shortest_path(
            self.graph.vs.find(name=source),
            self.graph.vs.find(name=target),
            weights="cost",
            output="epath",
        )
        return [self.graph.es[index]["oid"] for index in path]

    def tag_route(self, con, source, target, edges="edges", **attributes):
        """Set attributes on every edge of one route - the commonest update."""
        oids = self.route_edges(source, target)
        assignments = ", ".join(f"{column} = ?" for column in attributes)
        con.execute(
            f"update {edges} set {assignments} where oid in ?",
            list(attributes.values()) + [oids],
        )
        return oids


# ---------------------------------------------------------------------------
# worked examples, checking each substitution against the PostGIS behaviour
# ---------------------------------------------------------------------------


def _fixture(con):
    con.execute(
        f"""
        create table nodes as select * from (values
            (1::bigint, 'Gabon', st_point(0, 0)),
            (2::bigint, 'Gabon', st_point(3, 0)),
            (3::bigint, 'Gabon', st_point(1.6, 0.4)),
            (4::bigint, 'Gabon', st_point(-0.5, 0.1))
        ) as t(oid, country, geom);
        create table edges as select * from (values
            (10::bigint, 1::bigint, 2::bigint, 'Gabon', 0.0::double,
             st_geomfromtext('LINESTRING(0 0, 1 0, 2 0, 3 0)'))
        ) as t(oid, source, target, country, length, geom);
        update edges set length = {LENGTH_M.format(geom="geom")};
        """
    )


def main():
    con = connect()
    _fixture(con)

    whole = con.execute("select length from edges where oid = 10").fetchone()[0]
    node_on_line = con.execute(
        "insert into nodes values (5, 'Gabon', st_point(1.6, 0)) returning oid"
    ).fetchone()[0]

    new_oids = split_edge(con, 10, node_on_line)
    parts = con.execute(
        "select oid, source, target, length, st_astext(geom) from edges order by oid"
    ).fetchall()
    print("split_edge (rn_split_edge)")
    print(f"  whole edge      {whole:>12,.2f} m")
    for oid, source, target, length, wkt in parts:
        print(f"  {oid:<15} {length:>12,.2f} m  {source} -> {target}  {wkt}")
    print(f"  parts sum to    {sum(part[3] for part in parts):>12,.2f} m")
    print(f"  new oids        {new_oids}")

    con.execute("delete from edges")
    con.execute(
        """insert into edges values
           (10, 1, 2, 'Gabon', 0.0,
            st_geomfromtext('LINESTRING(0 0, 1 0, 2 0, 3 0)'))"""
    )
    con.execute("update edges set length = " + LENGTH_M.format(geom="geom"))
    new_node, _ = copy_node_to_edge(con, 3, 10)
    print("\ncopy_node_to_edge (rn_copy_node)")
    print(
        f"  node 3 at       {con.execute('select st_astext(geom) from nodes where oid = 3').fetchone()[0]}"
    )
    print(
        f"  copied to       {con.execute('select st_astext(geom) from nodes where oid = ?', [new_node]).fetchone()[0]} as {new_node}"
    )

    insert_edge(con, 1, 4, 99)
    print("\ninsert_edge (rn_insert_edge)")
    print(
        f"  edge 99         {con.execute('select st_astext(geom) from edges where oid = 99').fetchone()[0]}"
    )

    change_source(con, 99, 2)
    change_target(con, 99, 3)
    print("\nchange_source / change_target (rn_change_source / rn_change_target)")
    print(
        f"  edge 99         {con.execute('select st_astext(geom) from edges where oid = 99').fetchone()[0]}"
    )

    graph = RouteGraph(con)
    print("\nRouteGraph (pgr_dijkstra)")
    print(f"  1 -> 3          {graph.route_edges(1, 3)}")

    check_engines_agree()


# The substitutions as plain SQL, per engine, so both can be asked the same
# question. Where an engine spells one differently, that is the finding.
LINE = "ST_GeomFromText('LINESTRING(0 0, 1 0, 2 0, 3 0)')"
SHORT = "ST_GeomFromText('LINESTRING(0 0, 1 0, 2 0)')"
POINT = "ST_Point(1.6, 0.4)"

SUBSTITUTIONS = {
    "ST_Split, first part": {
        "duckdb": f"ST_AsText(ST_LineSubstring({LINE}, 0, ST_LineLocatePoint({LINE}, {POINT})))",
        "sedonadb": f"ST_AsText(ST_LineSubstring({LINE}, 0, ST_LineLocatePoint({LINE}, {POINT})))",
    },
    "ST_Split, second part": {
        "duckdb": f"ST_AsText(ST_LineSubstring({LINE}, ST_LineLocatePoint({LINE}, {POINT}), 1))",
        "sedonadb": f"ST_AsText(ST_LineSubstring({LINE}, ST_LineLocatePoint({LINE}, {POINT}), 1))",
    },
    # SedonaDB registers ST_ClosestPoint but has no kernel for two geometries;
    # interpolating at the located fraction gives the same point.
    "closest point on the line": {
        "duckdb": f"ST_AsText(ST_ClosestPoint({LINE}, {POINT}))",
        "sedonadb": f"ST_AsText(ST_LineInterpolatePoint({LINE}, ST_LineLocatePoint({LINE}, {POINT})))",
    },
    # SedonaDB's ST_MakeLine takes two geometries, not a list, so a line
    # cannot be rebuilt from its vertices in SQL - do those 30 edits in
    # Python, or on DuckDB.
    "ST_SetPoint on the first vertex": {
        "duckdb": (
            f"ST_AsText(ST_MakeLine(list_prepend(ST_Point(-0.5, 0.1),"
            f" [ST_PointN({SHORT}, i::int)"
            f" for i in range(2, ST_NPoints({SHORT}) + 1)])))"
        ),
        "sedonadb": None,
    },
}


def check_engines_agree():
    """Ask DuckDB and SedonaDB the same substitutions and compare the answers."""
    try:
        import sedonadb
    except ImportError:
        print("\nsedonadb not installed, skipping the cross-engine check")
        return

    con = connect()
    sd = sedonadb.connect()

    def ask(engine, expression):
        if expression is None:
            return "no equivalent"
        try:
            if engine == "duckdb":
                return str(con.execute(f"select {expression}").fetchone()[0])
            return str(sd.sql(f"select {expression}").to_pandas().values[0][0])
        except (duckdb.Error, RuntimeError, ValueError) as error:
            return f"failed: {str(error).splitlines()[0][:30]}"

    print(f"\n{'substitution':<34} {'duckdb':<26} {'sedonadb':<26} same")
    for label, per_engine in SUBSTITUTIONS.items():
        duck = ask("duckdb", per_engine["duckdb"])
        sedona = ask("sedonadb", per_engine["sedonadb"])
        # The two print geometries slightly differently, so compare loosely.
        same = duck.replace(" ", "") == sedona.replace(" ", "")
        print(f"{label:<34} {duck:<26} {sedona:<26} {'yes' if same else 'no'}")


if __name__ == "__main__":
    main()
