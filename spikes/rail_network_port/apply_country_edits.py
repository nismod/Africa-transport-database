"""Stage 2 of the port: replay one country's edits onto the prepared network.

The country SQL scripts are a notebook rather than a build - see README.md -
so the port reads each one, keeps the statements that change the network, and
writes them out as data. ``parse_country_sql.py`` does the reading;
``edits/*.yaml`` is what it wrote. This applies one of those files, using the
primitives in ``primitives.py``.

Sixteen operations cover the whole corpus. All of them are here.

Run with --compare to check the result against the published network. The
comparison is by line rather than by country, because a script's edits are not
confined to one country - several lines cross a border, and the `country`
column comes from stage 1's spatial join rather than from the edits.

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission. This is spike code - see README.md. It is not part of the
workflow.
"""

import json
import re
import time

import click
import yaml
from primitives import (
    RouteGraph,
    change_source,
    change_target,
    connect,
    copy_node_to_edge,
    insert_edge,
    split_edge,
)

# The Unicode block the scripts use to tell an Arabic station name from its
# Latin transliteration, in `split_name_script`.
ARABIC = "؀-ۿ"


def country_predicate(edit):
    """The SQL for however an edit names the countries it applies to.

    ``countries`` is a list to match exactly, ``country_like`` a pattern; an
    edit with neither applies wherever the rest of its filter matches, which is
    what the SQL did when it named no country.
    """
    if edit.get("countries"):
        placeholders = ", ".join("?" for _ in edit["countries"])
        return f"country in ({placeholders})", list(edit["countries"])
    if edit.get("country_like"):
        return "country like ?", [edit["country_like"]]
    return "true", []


class Network:
    """The prepared network, and the edits applied to it.

    Routing graphs are cached by the edge filter they were built with, and the
    whole cache is dropped whenever an edit changes the topology - which a
    split, a copy, an insert or an endpoint move does, and an attribute update
    does not. Building one over the continental network takes about half a
    second, and South Africa alone routes 171 times behind the same filter, so
    the cache is worth having.
    """

    def __init__(self, con):
        self.con = con
        self.graphs = {}
        self.applied = 0

    def route_graph(self, where=None):
        if where not in self.graphs:
            self.graphs[where] = RouteGraph(self.con, where=where)
        return self.graphs[where]

    def topology_changed(self):
        self.graphs = {}

    # -- routing ------------------------------------------------------------

    def tag_route(self, edit):
        """Set attributes on every edge of the least-cost path between two nodes."""
        graph = self.route_graph(edit.get("where"))
        oids = graph.tag_route(self.con, edit["from"], edit["to"], **edit["set"])
        return f"{len(oids)} edges"

    # -- topology -----------------------------------------------------------

    def split_edge(self, edit):
        """Split an edge at a node lying on it."""
        new_oids = split_edge(self.con, edit["edge"], edit["node"])
        self.topology_changed()
        return f"-> {new_oids[0]}, {new_oids[1]}"

    def copy_node(self, edit):
        """Copy a node onto the nearest point of an edge, splitting it there."""
        new_node, new_oids = copy_node_to_edge(self.con, edit["node"], edit["edge"])
        self.topology_changed()
        return f"node {new_node}, edges {new_oids[0]}, {new_oids[1]}"

    def insert_edge(self, edit):
        """Add a straight edge between two nodes."""
        insert_edge(self.con, edit["source"], edit["target"], edit["oid"])
        self.topology_changed()
        return str(edit["oid"])

    def change_source(self, edit):
        """Move an edge's first vertex onto a node."""
        change_source(self.con, edit["edge"], edit["node"])
        self.topology_changed()
        return f"edge {edit['edge']} -> node {edit['node']}"

    def change_target(self, edit):
        """Move an edge's last vertex onto a node."""
        change_target(self.con, edit["edge"], edit["node"])
        self.topology_changed()
        return f"edge {edit['edge']} -> node {edit['node']}"

    def insert_node_at(self, edit):
        """Add a node at a given point.

        The scripts do this to give a route an endpoint where OSM has none -
        a port berth, a mine loadout, a border post - and then route to the
        oid it chose, so these have to land before the routes that use them.
        """
        columns = ["oid"] + list(edit.get("set", {}))
        placeholders = ", ".join("?" for _ in columns)
        self.con.execute(
            f"insert into nodes ({', '.join(columns)}, geom)"
            f" values ({placeholders}, st_point(?, ?))",
            [edit["oid"], *edit.get("set", {}).values(), edit["lon"], edit["lat"]],
        )
        self.topology_changed()
        return f"{edit['oid']} at {edit['lon']}, {edit['lat']}"

    def delete_edge(self, edit):
        self.con.execute("delete from edges where oid = ?", [edit["edge"]])
        self.topology_changed()
        return str(edit["edge"])

    def delete_node(self, edit):
        self.con.execute("delete from nodes where oid = ?", [edit["node"]])
        self.topology_changed()
        return str(edit["node"])

    # -- attributes ---------------------------------------------------------

    def _set(self, table, assignments, condition=None, parameters=()):
        columns = ", ".join(f"{column} = ?" for column in assignments)
        where = f" where {condition}" if condition else ""
        self.con.execute(
            f"update {table} set {columns}{where}",
            list(assignments.values()) + list(parameters),
        )

    def set_node(self, edit):
        """Set attributes on one node."""
        self._set("nodes", edit["set"], "oid = ?", [edit["node"]])
        return str(edit["node"])

    def set_edge(self, edit):
        """Set attributes on one edge."""
        self._set("edges", edit["set"], "oid = ?", [edit["edge"]])
        return str(edit["edge"])

    def set_nodes(self, edit):
        """Set the same attributes on several nodes."""
        self._set("nodes", edit["set"], "oid in ?", [edit["nodes"]])
        return f"{len(edit['nodes'])} nodes"

    def set_edges(self, edit):
        """Set the same attributes on several edges."""
        self._set("edges", edit["set"], "oid in ?", [edit["edges"]])
        return f"{len(edit['edges'])} edges"

    def set_all_nodes(self, edit):
        """A whole-table default, from the scripts that predate the continental build."""
        self._set("nodes", edit["set"])
        return "every node"

    def set_all_edges(self, edit):
        self._set("edges", edit["set"])
        return "every edge"

    def set_nodes_on_edges(self, edit):
        """Set attributes on the nodes sitting on edges that match a filter.

        The scripts' "every station on a standard gauge line is standard
        gauge", written as ST_Intersects against ST_Collect of the matching
        edges.
        """
        assignments = ", ".join(f"{column} = ?" for column in edit["set"])
        edge_filter = " and ".join(f"e.{column} = ?" for column in edit["where_edge"])
        scope, parameters = country_predicate(edit)
        railways = edit.get("node_railway")
        if railways:
            scope += f" and railway in ({', '.join('?' for _ in railways)})"
            parameters += list(railways)
        predicate = f"""
            {scope}
              and oid in (
                  select n.oid from nodes n join edges e
                    on st_intersects(n.geom, e.geom)
                  where {edge_filter}
              )
        """
        selection = parameters + list(edit["where_edge"].values())
        matched = self.con.execute(
            f"select count(*) from nodes where {predicate}", selection
        ).fetchone()[0]
        self.con.execute(
            f"update nodes set {assignments} where {predicate}",
            list(edit["set"].values()) + selection,
        )
        return f"{matched} nodes"

    # -- names --------------------------------------------------------------

    def split_name_script(self, edit):
        """Split a bilingual station name into its Arabic and Latin halves.

        The scripts do this with ``regexp_matches`` and ``array_to_string`` in
        Postgres. Doing it in Python keeps it the same on either engine, and
        there are only a few hundred names to rewrite.
        """
        pattern = f"[{'' if edit['keep'] == 'arabic' else '^'}{ARABIC}]+"
        scope, parameters = country_predicate(edit)
        rows = self.con.execute(
            f"select oid, name from nodes where {scope} and name is not null",
            parameters,
        ).fetchall()
        changed = 0
        for oid, name in rows:
            value = " ".join(part.strip() for part in re.findall(pattern, name)).strip()
            self.con.execute(
                f"update nodes set {edit['column']} = ? where oid = ?", [value, oid]
            )
            changed += 1
        return f"{changed} names -> {edit['column']}"

    def copy_node_column(self, edit):
        """Copy one node column to another across a country."""
        scope, parameters = country_predicate(edit)
        self.con.execute(
            f"update nodes set {edit['to']} = {edit['from']} where {scope}", parameters
        )
        return f"{edit['from']} -> {edit['to']}"

    # -----------------------------------------------------------------------

    def apply(self, edit, echo):
        operation = getattr(self, edit["op"], None)
        if operation is None:
            raise SystemExit(f"no such operation: {edit['op']}")
        detail = operation(edit)
        self.applied += 1
        if echo:
            note = f"  ({edit['note']})" if edit.get("note") else ""
            click.echo(f"  {edit['op']:<20} {detail}{note}")


def compare_with_published(con, published, lines):
    """Line by line, against the network the original build produced.

    Only the lines this edits file names are compared: replaying one country
    onto the continental network leaves every other country untagged, so a
    whole-network comparison would report the rest of Africa as missing.
    """
    with open(published) as fh:
        features = [feature["properties"] for feature in json.load(fh)["features"]]

    theirs = {}
    for properties in features:
        line = properties["line"]
        if line not in lines:
            continue
        count, km = theirs.get(line, (0, 0.0))
        theirs[line] = (count + 1, km + properties["length"] / 1000)

    ours = {
        line: (count, float(km))
        for line, count, km in con.execute(
            "select line, count(*), sum(length) / 1000 from edges"
            " where line in ? group by line",
            [sorted(lines)],
        ).fetchall()
    }

    width = max(len(line) for line in lines) if lines else 10
    click.echo(f"\n{'line':<{width}} {'published':>18} {'replayed':>18}  match")
    matched = 0
    for line in sorted(lines):
        their_count, their_km = theirs.get(line, (0, 0.0))
        our_count, our_km = ours.get(line, (0, 0.0))
        same = their_count == our_count and abs(their_km - our_km) < 0.05
        matched += same
        click.echo(
            f"{line:<{width}} {their_count:>6} {their_km:>10,.1f} km"
            f" {our_count:>6} {our_km:>10,.1f} km  {'yes' if same else 'NO'}"
        )
    click.echo(f"\n{matched} of {len(lines)} lines match")
    return matched, len(lines)


@click.command()
@click.option("--database", required=True, type=click.Path(exists=True))
@click.option("--edits", required=True, type=click.Path(exists=True))
@click.option("--compare", type=click.Path(exists=True))
@click.option("--quiet", is_flag=True, help="Do not echo every edit as it is applied.")
def main(database, edits, compare, quiet):
    """Replay a country's edits onto the prepared network"""
    with open(edits) as fh:
        document = yaml.safe_load(fh)

    con = connect(database)
    network = Network(con)
    click.echo(f"{document['country']}: {len(document['edits'])} edits\n")

    started = time.time()
    for index, edit in enumerate(document["edits"]):
        try:
            network.apply(edit, echo=not quiet)
        except Exception as error:
            raise SystemExit(f"edit {index} ({edit['op']}) failed: {error}") from error
    click.echo(f"\napplied {network.applied} edits in {time.time() - started:.1f}s")

    tagged = con.execute(
        "select count(*), sum(length) / 1000 from edges where line is not null"
    ).fetchone()
    click.echo(f"tagged {tagged[0]:,} edges, {float(tagged[1] or 0):,.1f} km")

    if compare:
        lines = {
            edit["set"]["line"]
            for edit in document["edits"]
            if edit["op"] in ("tag_route", "set_edge", "set_edges")
            and edit["set"].get("line")
        }
        if not lines:
            click.echo("\nthis file names no lines, so there is nothing to compare")
            return
        matched, total = compare_with_published(con, compare, lines)
        raise SystemExit(0 if matched == total else 1)


if __name__ == "__main__":
    main()
