"""Stage 2 of the port: replay one country's edits onto the prepared network.

The country SQL scripts are a notebook rather than a build - see README.md -
so the port reads each one, keeps the statements that change the network, and
writes them out as data. ``edits/gabon.yaml`` is what gabon.sql reduces to.
This applies such a file, using the primitives in ``primitives.py``.

Five operations cover Gabon; the whole corpus needs two more
(``insert_edge`` and ``change_source``/``change_target``, 138 calls between
them), which ``primitives.py`` already implements.

Run with --compare to check the result against the published network.

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission. This is spike code - see README.md. It is not part of the
workflow.
"""

import json
import time

import click
import yaml
from primitives import RouteGraph, connect, copy_node_to_edge, split_edge


class Network:
    """The prepared network, and the edits applied to it.

    The routing graph is rebuilt whenever an edit changes the topology, which
    a split or a node copy does and an attribute update does not. Rebuilding
    takes half a second on the continental network, so the rebuild is deferred
    until the next route actually needs it.
    """

    def __init__(self, con):
        self.con = con
        self.graph = None
        self.applied = 0

    def route_graph(self):
        if self.graph is None:
            self.graph = RouteGraph(self.con)
        return self.graph

    def tag_route(self, edit):
        """Set attributes on every edge of the least-cost path between two nodes."""
        oids = self.route_graph().tag_route(
            self.con, edit["from"], edit["to"], **edit["set"]
        )
        return f"{len(oids)} edges"

    def split_edge(self, edit):
        """Split an edge at a node lying on it."""
        new_oids = split_edge(self.con, edit["edge"], edit["node"])
        self.graph = None
        return f"-> {new_oids[0]}, {new_oids[1]}"

    def copy_node(self, edit):
        """Copy a node onto the nearest point of an edge, splitting it there."""
        new_node, new_oids = copy_node_to_edge(self.con, edit["node"], edit["edge"])
        self.graph = None
        return f"node {new_node}, edges {new_oids[0]}, {new_oids[1]}"

    def set_node(self, edit):
        """Set attributes on one node."""
        assignments = ", ".join(f"{column} = ?" for column in edit["set"])
        self.con.execute(
            f"update nodes set {assignments} where oid = ?",
            list(edit["set"].values()) + [edit["node"]],
        )
        return str(edit["node"])

    def set_nodes_on_edges(self, edit):
        """Set attributes on the nodes sitting on edges that match a filter.

        gabon.sql's "every station on a standard gauge line is standard gauge",
        which it wrote as ST_Intersects against ST_Collect of the matching
        edges.
        """
        assignments = ", ".join(f"{column} = ?" for column in edit["set"])
        edge_filter = " and ".join(f"e.{column} = ?" for column in edit["where_edge"])
        predicate = f"""
            country = ?
              and railway in ({", ".join("?" for _ in edit["node_railway"])})
              and oid in (
                  select n.oid from nodes n join edges e
                    on st_intersects(n.geom, e.geom)
                  where {edge_filter}
              )
        """
        selection = (
            [edit["country"]]
            + list(edit["node_railway"])
            + list(edit["where_edge"].values())
        )
        matched = self.con.execute(
            f"select count(*) from nodes where {predicate}", selection
        ).fetchone()[0]
        self.con.execute(
            f"update nodes set {assignments} where {predicate}",
            list(edit["set"].values()) + selection,
        )
        return f"{matched} nodes"

    def apply(self, edit):
        operation = getattr(self, edit["op"])
        detail = operation(edit)
        self.applied += 1
        note = f"  ({edit['note']})" if edit.get("note") else ""
        click.echo(f"  {edit['op']:<20} {detail}{note}")


def compare_with_published(con, published, country):
    """Line by line, against the network the original build produced."""
    with open(published) as fh:
        features = [
            feature["properties"]
            for feature in json.load(fh)["features"]
            if feature["properties"]["country"] == country
        ]

    theirs = {}
    for properties in features:
        count, km = theirs.get(properties["line"], (0, 0.0))
        theirs[properties["line"]] = (count + 1, km + properties["length"] / 1000)

    ours = {
        line: (count, float(km))
        for line, count, km in con.execute(
            "select line, count(*), sum(length) / 1000 from edges"
            " where country = ? and line is not null group by line",
            [country],
        ).fetchall()
    }

    click.echo(f"\n{'line':<28} {'published':>18} {'replayed':>18}  match")
    matched = True
    for line in sorted(set(theirs) | set(ours)):
        their_count, their_km = theirs.get(line, (0, 0.0))
        our_count, our_km = ours.get(line, (0, 0.0))
        same = their_count == our_count and abs(their_km - our_km) < 0.05
        matched &= same
        click.echo(
            f"{line:<28} {their_count:>6} {their_km:>10,.1f} km"
            f" {our_count:>6} {our_km:>10,.1f} km  {'yes' if same else 'NO'}"
        )
    return matched


@click.command()
@click.option("--database", required=True, type=click.Path(exists=True))
@click.option("--edits", required=True, type=click.Path(exists=True))
@click.option("--compare", type=click.Path(exists=True))
def main(database, edits, compare):
    """Replay a country's edits onto the prepared network"""
    with open(edits) as fh:
        document = yaml.safe_load(fh)

    con = connect(database)
    network = Network(con)
    click.echo(f"{document['country']}: {len(document['edits'])} edits\n")

    started = time.time()
    for edit in document["edits"]:
        network.apply(edit)
    click.echo(f"\napplied {network.applied} edits in {time.time() - started:.1f}s")

    tagged = con.execute(
        "select count(*), sum(length) / 1000 from edges where country = ? and line is not null",
        [document["country"]],
    ).fetchone()
    click.echo(f"tagged {tagged[0]:,} edges, {float(tagged[1]):,.1f} km")

    if compare:
        matched = compare_with_published(con, compare, document["country"])
        raise SystemExit(0 if matched else 1)


if __name__ == "__main__":
    main()
