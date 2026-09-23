"""Transcribe one country's SQL script into an edits file.

The country scripts are a notebook rather than a build - see README.md - but
the statements that change the network are written in a handful of rigid
shapes, because they were typed against the same few helper functions over and
over. This reads a script and writes out the ones that change the published
network, in the form ``apply_country_edits.py`` replays.

The point of the exercise is that nothing is dropped quietly. Every statement
in the file lands in exactly one of three places:

  * an edit, written to the YAML;
  * a *skip*, one of the named categories below, counted in the report;
  * *unhandled*, listed in full in the report with its line number.

So the report is the thing to read after a run: a country with no unhandled
statements has been transcribed completely, and a country with some has been
transcribed as far as this goes, with the rest named exactly.

The skip categories are all statements that cannot reach the published
network:

  ``exploratory``   a bare select - counting, looking, checking
  ``trap``          ``update rubbish set rubish``, the deliberate syntax
                    error 17 of the 24 scripts open with to stop anyone
                    running the whole file
  ``template``      one of the boilerplate blocks with its values left
                    blank, copied between scripts and never filled in
  ``backup``        ``create table <country>_osm_edges as select ...``, and
                    the later edits to those copies. generate_combined_network
                    .sql reads only africa_osm_edges and africa_osm_nodes, so
                    a backup table is a dead end
  ``function``      a plpgsql function body pasted into the script;
                    primitives.py implements these
  ``routing test``  a bare pgr_dijkstra select, run to look at a path

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission. This is spike code - see README.md. It is not part of the
workflow.
"""

import collections
import itertools
import re
from pathlib import Path

import click
import yaml

# The tables the combine step reads. Anything written to another table - the
# per-country backup copies - cannot reach the published network.
LIVE_TABLES = {"africa_osm_nodes", "africa_osm_edges"}

# Columns the scripts set, in the order the published network carries them, so
# that a transcribed `set` block reads the same way from country to country.
COLUMN_ORDER = [
    "line",
    "mode",
    "type",
    "gauge",
    "status",
    "structure",
    "comment",
    "name",
    "railway",
    "facility",
    "country",
]


class Statement:
    """One SQL statement, with the comments written above it."""

    def __init__(self, sql, comments, line):
        self.sql = sql
        self.comments = comments
        self.line = line
        # Whitespace-collapsed and lowercased, for matching. Keep `sql` intact
        # for pulling string literals back out with their case.
        self.flat = " ".join(sql.split())
        self.low = self.flat.lower()

    def __repr__(self):
        return f"<Statement line {self.line}: {self.flat[:60]}>"


def split_statements(text):
    """Split a script into statements, keeping the comments above each one.

    Written out by hand rather than with a regex because the scripts contain
    semicolons inside string literals - South Africa has two comment fields
    with one in - and inside the plpgsql function bodies some scripts paste in.
    A naive split on ";" silently truncates those, which turns an update with a
    `where` into one without.
    """
    statements = []
    buffer = []
    comments = []
    line = 1
    start_line = 1
    index = 0
    while index < len(text):
        char = text[index]
        ahead = text[index : index + 2]

        if char == "\n":
            line += 1
            buffer.append(char)
            index += 1
        elif ahead == "--":
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            # A comment only counts as a note for the next statement if
            # nothing of that statement has been read yet.
            if not "".join(buffer).strip():
                comments.append(text[index + 2 : end].strip())
            index = end
        elif ahead == "/*":
            end = text.find("*/", index + 2)
            end = len(text) if end < 0 else end + 2
            line += text.count("\n", index, end)
            index = end
        elif char == "'":
            end = index + 1
            while end < len(text):
                if text[end] == "'":
                    if text[end : end + 2] == "''":  # an escaped quote
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            line += text.count("\n", index, end)
            buffer.append(text[index:end])
            index = end
        elif ahead == "$$":
            end = text.find("$$", index + 2)
            end = len(text) if end < 0 else end + 2
            line += text.count("\n", index, end)
            buffer.append(text[index:end])
            index = end
        elif char == ";":
            sql = "".join(buffer).strip()
            if sql:
                statements.append(Statement(sql, comments, start_line))
            buffer, comments = [], []
            start_line = line
            index += 1
        else:
            buffer.append(char)
            index += 1

    sql = "".join(buffer).strip()
    if sql:
        statements.append(Statement(sql, comments, start_line))
    return statements


def split_top_level(text, separator=",", keep_empty=False):
    """Split on a separator that is not inside quotes or parentheses.

    ``keep_empty`` holds on to blank segments, which is what a values list
    needs: the unfilled templates are written ``values ( , null, ...)`` and the
    blank is the point - dropping it would make the row look one column short
    rather than obviously unfilled.
    """
    parts, buffer, depth, index = [], [], 0, 0
    while index < len(text):
        char = text[index]
        if char == "'":
            end = index + 1
            while end < len(text):
                if text[end] == "'":
                    if text[end : end + 2] == "''":
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            buffer.append(text[index:end])
            index = end
            continue
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        if char == separator and depth == 0:
            parts.append("".join(buffer))
            buffer = []
        else:
            buffer.append(char)
        index += 1
    parts.append("".join(buffer))
    stripped = [part.strip() for part in parts]
    return stripped if keep_empty else [part for part in stripped if part]


def mask_strings(text):
    """A copy of the text with string-literal contents blanked out.

    Same length as the original, so an index into the mask is an index into the
    text. Everything that looks for a keyword does it here: the scripts have
    the word "where" inside a comment field, and an ``oid`` inside a URL, and
    matching those as SQL silently truncates the statement.
    """
    out = list(text)
    index = 0
    while index < len(text):
        if text[index] != "'":
            index += 1
            continue
        end = index + 1
        while end < len(text):
            if text[end] == "'":
                if text[end : end + 2] == "''":
                    out[end] = out[end + 1] = "\x00"
                    end += 2
                    continue
                break
            out[end] = "\x00"
            end += 1
        index = end + 1
    return "".join(out)


def depths(mask):
    """Parenthesis depth at each position of a masked string."""
    level, out = 0, []
    for char in mask:
        if char in "([":
            out.append(level)
            level += 1
        elif char in ")]":
            level -= 1
            out.append(level)
        else:
            out.append(level)
    return out


def find_top_level(text, pattern, start=0):
    """The first match of a pattern outside quotes and outside parentheses."""
    mask = mask_strings(text)
    level = depths(mask)
    for match in re.finditer(pattern, mask[start:], re.IGNORECASE):
        at = start + match.start()
        if level[at] == 0:
            return at, start + match.end()
    return None


# The keywords that begin a statement. Several scripts are missing a
# semicolon between two statements, which runs them together; splitting on
# these recovers the pair rather than reporting one unreadable statement.
STATEMENT_START = r"\b(?:update\s+\w*osm_\w+|insert\s+into|delete\s+from|select\s+rn_|with\s+\w+\s+as)"


def resplit_runons(statement):
    """Split a statement that has another statement run on to the end of it."""
    text = statement.sql
    mask = mask_strings(text)
    level = depths(mask)
    cuts = [
        match.start()
        for match in re.finditer(STATEMENT_START, mask, re.IGNORECASE)
        if level[match.start()] == 0
    ]
    # The first keyword is this statement's own start, so it is never a cut.
    # A route is written `with tmp as (...) update ...`, which matches twice:
    # the `update` belongs to the `with`, so drop that one too.
    cuts = cuts[1:]
    if statement.low.startswith("with"):
        for index, cut in enumerate(cuts):
            if re.match(r"update|insert", mask[cut:], re.IGNORECASE):
                cuts = cuts[index + 1 :]
                break
    if not cuts:
        return [statement]
    pieces, bounds = [], [0] + cuts + [len(text)]
    for start, end in itertools.pairwise(bounds):
        piece = text[start:end].strip()
        if piece:
            line = statement.line + text.count("\n", 0, start)
            pieces.append(
                Statement(piece, statement.comments if start == 0 else [], line)
            )
    return pieces


def read_value(text):
    """Turn one SQL literal into the value it stands for.

    Returns UNPARSED for anything that is not a literal - an expression, a
    subquery - so that the caller reports the statement rather than guessing.
    """
    text = text.strip()
    if text.lower() == "null":
        return None
    if text.startswith("'") and text.endswith("'") and len(text) >= 2:
        return text[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        return text
    return UNPARSED


def read_id(text):
    """One id, whether it was written bare or in quotes."""
    text = text.strip().strip("'").strip()
    return int(text) if re.fullmatch(r"\d+", text) else None


UNPARSED = object()


def set_and_where(statement):
    """The text of the ``set`` clause and of the ``where`` clause.

    Both boundaries are found outside quotes and outside parentheses, because
    a comment field may contain the word "where" and a `set` may contain a
    subquery that has a real one.
    """
    opening = find_top_level(statement.flat, r"\bset\b")
    if not opening:
        return None, None
    where = find_top_level(statement.flat, r"\bwhere\b", opening[1])
    if where:
        return statement.flat[opening[1] : where[0]], statement.flat[where[1] :].strip()
    return statement.flat[opening[1] :], None


def read_set_clause(statement):
    """The ``set a = 1, b = 'x'`` of an update, as a dict in column order."""
    clause, _ = set_and_where(statement)
    if clause is None:
        return None
    assignments = {}
    for part in split_top_level(clause):
        if "=" not in part:
            return None
        column, _, value = part.partition("=")
        column = column.strip().lower()
        parsed = read_value(value)
        if parsed is UNPARSED:
            return None
        assignments[column] = parsed
    ordered = {c: assignments.pop(c) for c in COLUMN_ORDER if c in assignments}
    ordered.update(assignments)  # anything unexpected, kept, in its own order
    return ordered or None


def read_ids(text):
    """Every integer in a fragment, in order."""
    return [int(number) for number in re.findall(r"\b\d+\b", text)]


def arrays_of(call):
    """The two ``array[...]`` arguments of an rn_ helper call.

    Tolerant of two typos in the corpus - one ``arary[`` and one ``array[...)``
    closed with the wrong bracket - because both are unambiguous and rejecting
    them would drop a real edit.
    """
    pattern = r"ar(?:ra|ar)y\s*\[([^\]\)]*)[\]\)]"
    return [read_ids(group) for group in re.findall(pattern, call, re.IGNORECASE)]


def note_from(statement, used_ids):
    """The comment above a statement, if it says anything the statement does not.

    The scripts label a copied station with its name on the line above, which
    is worth keeping. They also restate the call itself - "split 555025328 at
    555125285" - which is not.
    """
    for comment in reversed(statement.comments):
        text = comment.strip().strip("-").strip()
        if not text or len(text) > 90:
            continue
        if any(str(oid) in text for oid in used_ids):
            continue  # a restatement of the call
        if re.fullmatch(r"[\W_]+", text):
            continue  # a rule of dashes or equals
        lowered = text.lower()
        if lowered in SECTION_WORDS or lowered.startswith(("trap ", "select ")):
            continue
        return text
    return None


SECTION_WORDS = {
    "features",
    "tunnel",
    "ports",
    "stations",
    "incorrect nodes",
    "update line information",
    "update/copy stations as required",
    "set additional node for stations or update details",
    "insert node to enable link to be inserted",
    "will then be inserted onto correct edge below",
    "extract tables for egypt (backup)",
    "test routing",
    "bridge",
}


def target_table(statement):
    """The table an update or insert writes to.

    Searched rather than anchored, because an insert may be preceded by the
    CTE that builds the row it inserts.
    """
    match = re.search(r"\b(?:update|insert\s+into)\s+([a-z_]+)", statement.low)
    return match.group(1) if match else None


def route_endpoints(statement):
    """The two node ids a pgr_dijkstra call routes between, and any edge filter.

    The call is ``pgr_dijkstra('SELECT ... FROM <table> [where ...]', a, b,
    false)``. The inner select sometimes restricts the edges the route may use,
    which changes the path, so it is carried through to the edit.
    """
    match = re.search(
        r"pgr_dijkstra\s*\((.*)\)", statement.flat, re.IGNORECASE | re.DOTALL
    )
    if not match:
        return None
    arguments = split_top_level(match.group(1))
    if len(arguments) < 3 or not arguments[0].startswith("'"):
        return None
    endpoints = [read_value(argument) for argument in arguments[1:3]]
    if any(value is UNPARSED or value is None for value in endpoints):
        return None  # a template with its endpoints left blank
    # The edge query is a string literal, so its own quotes are doubled.
    inner = arguments[0][1:-1].replace("''", "'")
    where = None
    from_match = re.search(r"\bfrom\s+(.*)$", inner, re.IGNORECASE)
    source = from_match.group(1).strip() if from_match else ""
    if not re.fullmatch(r"[a-z_]+", source, re.IGNORECASE):
        table_match = re.match(r"([a-z_]+)\s+where\s+(.*)$", source, re.IGNORECASE)
        if not table_match:
            return None  # a subquery as the edge source: report it
        source, where = table_match.group(1), table_match.group(2).strip()
    return int(endpoints[0]), int(endpoints[1]), source.lower(), where


class Parser:
    """Reads one script, and records what it did with every statement."""

    def __init__(self, country, tables=None):
        self.country = country
        self.tables = set(tables) if tables else set(LIVE_TABLES)
        self.edits = []
        self.skipped = collections.Counter()
        self.unhandled = []
        self.backup_tables = set()

    def skip(self, reason):
        self.skipped[reason] += 1

    def report_unhandled(self, statement, why):
        self.unhandled.append((statement.line, why, statement.flat[:160]))

    def add(self, **edit):
        note = edit.pop("note", None)
        if note:
            edit["note"] = note
        self.edits.append(edit)

    def run(self, statements):
        for statement in statements:
            # A pasted function body has `delete from` and `insert into` in it,
            # which are part of the function, not statements run on to the end.
            pieces = [statement] if "$$" in statement.sql else resplit_runons(statement)
            for piece in pieces:
                self.classify(piece)
        return self

    def classify(self, statement):
        # A few statements have a stray word in front of them - a shell prompt
        # pasted in with the SQL, or a comment that lost its leading dashes.
        stray = re.match(
            r"^(?:postgres|split \d+ at \d+)\s+(?=update|select|insert|delete)",
            statement.flat,
            re.IGNORECASE,
        )
        if stray:
            statement = Statement(
                statement.flat[stray.end() :], statement.comments, statement.line
            )
        low = statement.low

        if low.startswith(
            (
                "alter table",
                "create index",
                "create unique index",
                "vacuum",
                "analyze",
                "begin",
                "commit",
                "rollback",
                "set ",
            )
        ):
            return self.skip("schema")
        if low.startswith("delete from "):
            return self.delete(statement)
        if low.startswith("update rubbish"):
            return self.skip("trap")
        # A DO block is sometimes glued to the statement above it by a missing
        # semicolon, so look for one anywhere rather than only at the start.
        opens_block = re.search(r"\bdo\s*\$\$", statement.flat, re.IGNORECASE)
        if opens_block and opens_block.start() > 0:
            head = statement.flat[: opens_block.start()].strip()
            if head:
                self.classify(Statement(head, statement.comments, statement.line))
            return self.classify(
                Statement(statement.flat[opens_block.start() :], [], statement.line)
            )
        if opens_block:
            return self.do_block(statement)
        if "$$" in statement.sql or low.startswith(
            ("create function", "create or replace function")
        ):
            return self.skip("function")
        if low.startswith("create table"):
            match = re.match(r"create table ([a-z_]+)", low)
            if match:
                self.backup_tables.add(match.group(1))
            return self.skip("backup")
        if low.startswith("drop table"):
            return self.skip("backup")

        if re.match(r"select\s+rn_", low):
            return self.helper_call(statement)
        if "pgr_dijkstra" in low:
            return self.route(statement)
        if low.startswith("update "):
            return self.update(statement)
        if low.startswith("insert into ") or (
            low.startswith("with")
            and find_top_level(statement.flat, r"\binsert\s+into\b")
        ):
            return self.insert(statement)
        if low.startswith(("select", "with", "\\", "explain")):
            return self.skip("exploratory")
        return self.report_unhandled(statement, "unrecognised statement")

    def helper_call(self, statement):
        """rn_copy_node, rn_split_edge, rn_insert_edge, rn_change_source/target."""
        name = re.match(r"select\s+(rn_\w+)", statement.low).group(1)

        if name in ("rn_copy_node", "rn_split_edge"):
            arrays = arrays_of(statement.flat)
            if len(arrays) != 2:
                return self.report_unhandled(statement, f"{name}: expected two arrays")
            first, second = arrays
            if not first and not second:
                return self.skip("template")
            if len(first) != len(second):
                return self.report_unhandled(
                    statement, f"{name}: arrays of unequal length"
                )
            for left, right in zip(first, second):
                if name == "rn_copy_node":
                    # rn_copy_node(nodes, edges): copy each node onto its edge.
                    self.add(
                        op="copy_node",
                        node=left,
                        edge=right,
                        note=note_from(statement, (left, right))
                        if len(first) == 1
                        else None,
                    )
                else:
                    # rn_split_edge(edges, nodes): split each edge at its node.
                    self.add(
                        op="split_edge",
                        edge=left,
                        node=right,
                        note=note_from(statement, (left, right))
                        if len(first) == 1
                        else None,
                    )
            return None

        arguments = split_top_level(
            re.search(r"\((.*)\)", statement.flat, re.DOTALL).group(1)
        )
        values = [read_value(argument) for argument in arguments]
        if any(value is UNPARSED or value is None for value in values):
            return self.skip("template")
        numbers = [int(value) for value in values]

        if name == "rn_insert_edge":
            if len(numbers) != 3:
                return self.report_unhandled(
                    statement, "rn_insert_edge: expected three ids"
                )
            source, target, oid = numbers
            return self.add(
                op="insert_edge",
                source=source,
                target=target,
                oid=oid,
                note=note_from(statement, numbers),
            )
        if name in ("rn_change_source", "rn_change_target"):
            if len(numbers) != 2:
                return self.report_unhandled(statement, f"{name}: expected two ids")
            return self.add(
                op=name[3:],
                edge=numbers[0],
                node=numbers[1],
                note=note_from(statement, numbers),
            )
        return self.report_unhandled(statement, f"unknown helper {name}")

    def route(self, statement):
        """A pgr_dijkstra path, with the update that tags the edges along it."""
        if not re.search(r"\bupdate\b", statement.low):
            return self.skip("routing test")

        table = target_table_of_update(statement)
        if table not in self.tables:
            return self.skip("backup")

        endpoints = route_endpoints(statement)
        if endpoints is None:
            if re.search(r",\s*,", statement.flat):
                return self.skip("template")
            return self.report_unhandled(statement, "route: could not read endpoints")
        source, target, edge_table, where = endpoints
        if edge_table not in self.tables:
            return self.skip("backup")

        assignments = read_set_clause(statement)
        if not assignments:
            return self.report_unhandled(
                statement, "route: could not read the set clause"
            )

        if table.endswith("_nodes"):
            # The handful that tag the nodes along a path rather than the edges.
            edit = dict(
                op="tag_route_nodes", **{"from": source, "to": target}, set=assignments
            )
        else:
            edit = dict(
                op="tag_route", **{"from": source, "to": target}, set=assignments
            )
        if where:
            edit["where"] = where
        edit["note"] = note_from(statement, (source, target))
        return self.add(**edit)

    def update(self, statement):
        table = target_table(statement)
        if table not in self.tables:
            return self.skip("backup")

        entity = "node" if table.endswith("_nodes") else "edge"
        assignments = read_set_clause(statement)
        if assignments is None:
            return self.expression_update(statement)

        _, condition = set_and_where(statement)
        if condition is None:
            # The four scripts that predate the continental build set a few
            # whole-table defaults before editing individual features.
            return self.add(
                op=f"set_all_{entity}s",
                set=assignments,
                note=note_from(statement, []),
            )
        # "every station on a line with these attributes", written as an
        # st_intersects against an st_collect of the matching edges.
        collect = re.search(
            r"st_intersects\s*\(\s*geom\s*,\s*\(\s*select\s+st_collect\(geom\)\s+from\s+"
            r"[a-z_]*osm_edges\s+where\s+(.*?)\)\s*\)",
            condition,
            re.IGNORECASE,
        )
        if collect:
            return self.nodes_on_edges(statement, condition, collect, assignments)

        single = re.fullmatch(r"oid\s*=\s*'?(\d+)'?", condition, re.IGNORECASE)
        if single:
            return self.add(
                op=f"set_{entity}",
                **{entity: int(single.group(1))},
                set=assignments,
                note=note_from(statement, [single.group(1)]),
            )

        many = re.fullmatch(r"oid\s+in\s*\(([^)]*)\)", condition, re.IGNORECASE)
        if many:
            ids = read_ids(many.group(1))
            if not ids:
                return self.skip("template")
            return self.add(
                op=f"set_{entity}s",
                **{f"{entity}s": ids},
                set=assignments,
                note=note_from(statement, ids),
            )

        if re.fullmatch(r"oid\s*=\s*", condition, re.IGNORECASE):
            return self.skip("template")
        return self.report_unhandled(
            statement, f"update: unhandled where clause: {condition[:80]}"
        )

    def nodes_on_edges(self, statement, condition, collect, assignments):
        """The "every station on a matching line" update."""
        edge_filter = read_conditions(collect.group(1))
        if edge_filter is None:
            return self.report_unhandled(
                statement, "nodes-on-edges: could not read the edge filter"
            )

        rest = condition[: collect.start()] + condition[collect.end() :]
        railways = re.search(r"railway\s+in\s*\(([^)]*)\)", rest, re.IGNORECASE)
        edit = {"op": "set_nodes_on_edges"}
        edit.update(read_country_filter(rest) or {})
        if railways:
            edit["node_railway"] = [
                value.strip().strip("'") for value in railways.group(1).split(",")
            ]
        edit["where_edge"] = edge_filter
        edit["set"] = assignments
        return self.add(**edit)

    def expression_update(self, statement):
        """An update whose `set` is an expression rather than a literal.

        Four shapes account for all of them:

        * ``geom = ST_SetPoint(geom, 0, (select geom from nodes where oid = N)),
          source = N`` - move an edge's first vertex onto a node and re-point
          its source. That is ``change_source``; the same with
          ``ST_NPoints(geom) - 1`` and ``target`` is ``change_target``.
        * ``name_arabic = (... regexp_matches(name, '[\u0600-\u06ff]+') ...)``
          and its complement on ``name`` - split a bilingual station name into
          its Arabic and Latin halves.
        * ``name_arabic = name`` - copy the name across before splitting it.
        * ``length = st_length(...)`` - recompute a length, which this port
          does for every edge with pyproj, so the statement is redundant.
        """
        clause, condition = set_and_where(statement)
        if clause is None:
            return self.report_unhandled(
                statement, "update: could not read the set clause"
            )
        if re.fullmatch(r"length\s*=.*", clause.strip(), re.IGNORECASE | re.DOTALL):
            return self.skip("recomputed length")
        if condition is None:
            return self.report_unhandled(
                statement, f"update with no where clause: {clause.strip()[:70]}"
            )

        parts = split_top_level(clause)
        assignments = {}
        for part in parts:
            column, _, value = part.partition("=")
            assignments[column.strip().lower()] = value.strip()

        edge = re.fullmatch(r"oid\s*=\s*'?(\d+)'?", condition, re.IGNORECASE)

        # Moving an edge end onto a node.
        if (
            "geom" in assignments
            and edge
            and ("source" in assignments or "target" in assignments)
        ):
            geom = assignments["geom"]
            if not re.match(r"st_setpoint\s*\(", geom, re.IGNORECASE):
                return self.report_unhandled(
                    statement, f"update: unhandled geometry expression: {geom[:70]}"
                )
            end = "source" if "source" in assignments else "target"
            node = read_id(assignments[end])
            inner = re.search(r"oid\s*=\s*(\d+)", geom, re.IGNORECASE)
            if node is None or not inner or int(inner.group(1)) != node:
                return self.report_unhandled(
                    statement, f"update: {end} move does not name one node consistently"
                )
            at_start = re.search(
                r"st_setpoint\s*\(\s*geom\s*,\s*0\s*,", geom, re.IGNORECASE
            )
            if (end == "source") != bool(at_start):
                return self.report_unhandled(
                    statement, f"update: {end} move does not match the vertex it sets"
                )
            return self.add(
                op=f"change_{end}",
                edge=int(edge.group(1)),
                node=node,
                note=note_from(statement, [edge.group(1), node]),
            )

        countries = read_country_filter(condition)

        # Splitting a bilingual name into its two scripts.
        if countries and len(assignments) == 1:
            ((column, value),) = assignments.items()
            if column in ("name", "name_arabic") and "regexp_matches" in value.lower():
                negated = "[^" in value
                return self.add(
                    op="split_name_script",
                    **countries,
                    column=column,
                    keep="latin" if negated else "arabic",
                    note=note_from(statement, []),
                )
            if column == "name_arabic" and value.strip().lower() == "name":
                return self.add(
                    op="copy_node_column",
                    **countries,
                    **{"from": "name", "to": "name_arabic"},
                    note=note_from(statement, []),
                )

        if set(assignments) == {"length"}:
            return self.skip("recomputed length")

        return self.report_unhandled(
            statement, f"update: could not read the set clause: {clause.strip()[:70]}"
        )

    def do_block(self, statement):
        """An anonymous ``DO $$ ... $$`` block: rn_copy_node or rn_split_edge,
        written out inline and run over a pair of arrays.

        Seven of these carry real work in the continental scripts, and between
        them they account for most of what the rest of the port could not
        resolve - the ids they create (a copy is ``oid + 1000000``) are routed
        to further down each file.

        The catch is that the arrays were edited in place and re-run: the file
        holds the *last* pair, one id each, with the full pair left above it as
        a comment. The full pair is what was executed - the ids it creates are
        the ones later statements use, and the active single is its last
        element - so that is what is transcribed, and each batch says so.
        """
        body = statement.sql
        pairing = re.search(
            r"for\s+(\w+)\s*,\s*(\w+)\s+in\s+select\s+unnest\s*\(\s*(\w+)",
            body,
            re.IGNORECASE,
        )
        if not pairing:
            return self.report_unhandled(statement, "DO block: no unnest loop")

        if re.search(r"oid\s*\+\s*1000000", body):
            operation = "copy_node"
        elif re.search(r"st_split", body, re.IGNORECASE):
            operation = "split_edge"
        else:
            return self.report_unhandled(statement, "DO block: not a copy or a split")

        # Every declaration of each array, commented or not; the longest is the
        # run that was actually made.
        arrays = {}
        for name in ("nodes", "edges"):
            found = re.findall(
                rf"\b{name}\s+INT8\s+ARRAY\s+DEFAULT\s+ARRAY\s*\[([^\]]*)\]",
                body,
                re.IGNORECASE,
            )
            arrays[name] = max(
                (read_ids(group) for group in found), key=len, default=[]
            )
        if not arrays["nodes"] or not arrays["edges"]:
            return self.report_unhandled(statement, "DO block: no node and edge arrays")

        # `select unnest(a), unnest(b)` stops at the shorter of the two.
        pairs = min(len(arrays["nodes"]), len(arrays["edges"]))
        note = (
            f"{pairs} {operation.replace('_', ' ')}s from a DO block, whose array "
            "survives only as a comment"
        )
        if len(arrays["nodes"]) != len(arrays["edges"]):
            note += (
                f" ({len(arrays['nodes'])} nodes and {len(arrays['edges'])} edges "
                "declared; the loop stops at the shorter)"
            )
        for index in range(pairs):
            node, edge = arrays["nodes"][index], arrays["edges"][index]
            self.add(
                op=operation,
                node=node,
                edge=edge,
                note=note if index == 0 else None,
            )
        return None

    def makeline_edge(self, statement):
        """``rn_insert_edge`` written out by hand.

        A CTE draws a straight line between two nodes and the insert adds it as
        an edge with a chosen oid, which is exactly what the helper does. The
        length the SQL computes is discarded: this port measures every edge
        with pyproj at the end of stage 1.
        """
        endpoints = re.search(
            r"a\.oid\s*=\s*(\d+)\s+and\s+b\.oid\s*=\s*(\d+)",
            statement.flat,
            re.IGNORECASE,
        )
        if not endpoints:
            return self.report_unhandled(
                statement, "insert: could not read the line endpoints"
            )
        source, target = int(endpoints.group(1)), int(endpoints.group(2))

        tail = statement.flat[statement.low.rindex("insert into") :]
        selection = re.sub(r"^.*?\bselect\b", "", tail, flags=re.IGNORECASE | re.DOTALL)
        source_clause = find_top_level(selection, r"\bfrom\b")
        if source_clause:
            selection = selection[: source_clause[0]]
        ids = [
            int(part)
            for part in split_top_level(selection)
            if re.fullmatch(r"\d+", part)
        ]
        if len(ids) < 3 or ids[-3:-1] != [source, target]:
            return self.report_unhandled(
                statement, "insert: line endpoints and columns disagree"
            )
        return self.add(
            op="insert_edge",
            source=source,
            target=target,
            oid=ids[-1],
            note=note_from(statement, ids),
        )

    def delete(self, statement):
        """``delete from africa_osm_edges where oid = N``."""
        table = re.match(r"delete from ([a-z_]+)", statement.low).group(1)
        if table not in self.tables:
            return self.skip("backup")
        _, condition = None, None
        where = find_top_level(statement.flat, r"\bwhere\b")
        if where:
            condition = statement.flat[where[1] :].strip()
        single = re.fullmatch(r"oid\s*=\s*'?(\d+)'?", condition or "", re.IGNORECASE)
        if not single:
            return self.report_unhandled(
                statement, f"delete: unhandled where clause: {condition}"
            )
        entity = "node" if table.endswith("_nodes") else "edge"
        return self.add(
            op=f"delete_{entity}",
            **{entity: int(single.group(1))},
            note=note_from(statement, [single.group(1)]),
        )

    def insert(self, statement):
        table = target_table(statement)
        if table not in self.tables:
            return self.skip("backup")

        columns = re.search(
            r"\(([^)]*)\)\s*values", statement.flat, re.IGNORECASE | re.DOTALL
        )
        values = re.search(
            r"\bvalues\s*\((.*)\)\s*$", statement.flat, re.IGNORECASE | re.DOTALL
        )
        if not columns or not values:
            if re.search(r"st_makeline", statement.low):
                return self.makeline_edge(statement)
            return self.report_unhandled(
                statement, "insert: could not read columns and values"
            )

        names = [name.strip().lower() for name in columns.group(1).split(",")]
        parts = split_top_level(values.group(1), keep_empty=True)
        if any(not part for part in parts):
            return self.skip("template")
        # One row is written `'station' 'Metehara'`, missing the comma between
        # them. Two literals with only space between can only be that.
        parts = [
            piece
            for part in parts
            for piece in (
                re.findall(r"'(?:[^']|'')*'", part)
                if re.fullmatch(r"'(?:[^']|'')*'(?:\s+'(?:[^']|'')*')+", part)
                else [part]
            )
        ]
        if len(names) != len(parts):
            return self.report_unhandled(
                statement, "insert: columns and values do not line up"
            )

        record, point = {}, None
        for name, part in zip(names, parts):
            if name == "geom":
                point = read_point(part)
                if point is None:
                    return self.skip("template")  # ST_Point() with nothing in it
                continue
            parsed = read_value(part)
            if parsed is UNPARSED:
                return self.report_unhandled(
                    statement, f"insert: could not read {name}"
                )
            record[name] = parsed

        if record.get("oid") is None:
            return self.skip("template")
        if point is None:
            return self.report_unhandled(statement, "insert: no geometry")

        entity = "node" if table.endswith("_nodes") else "edge"
        return self.add(
            op=f"insert_{entity}_at",
            oid=int(record.pop("oid")),
            lon=point[0],
            lat=point[1],
            set={
                key: value for key, value in record.items() if value not in (None, "")
            },
            note=note_from(statement, [record.get("oid")]),
        )


def read_point(text):
    """The longitude and latitude of an ``ST_Point(lon, lat)``, or None.

    Only the point's own two arguments: the column is written
    ``ST_SetSRID(ST_Point(8.00607, 35.66806), 4326)``, and reading every
    number in that would take the 4326 for a coordinate.
    """
    match = re.search(r"st_point\s*\(([^)]*)\)", text, re.IGNORECASE)
    if not match:
        return None
    parts = [part.strip() for part in match.group(1).split(",")]
    if len(parts) != 2 or not all(re.fullmatch(r"-?\d+\.?\d*", part) for part in parts):
        return None
    return [float(part) for part in parts]


def read_country_filter(text):
    """How a statement names the countries it applies to, or None.

    Three shapes appear: ``country = 'Gabon'``, ``country in ('Ethiopia',
    'Djibouti')`` and ``country like '%Sudan%'``. The last two matter - the
    network spells Morocco "Morocco except Western Sahara", so a `like` cannot
    be flattened to the name inside it, and several scripts cover a region
    rather than a country.
    """
    listed = re.search(r"\bcountry\s+in\s*\(([^)]*)\)", text, re.IGNORECASE)
    if listed:
        names = [
            value.strip().strip("'").replace("''", "'")
            for value in listed.group(1).split(",")
        ]
        return {"countries": [name for name in names if name]}
    pattern = re.search(r"\bcountry\s+like\s+'([^']*)'", text, re.IGNORECASE)
    if pattern:
        return {"country_like": pattern.group(1)}
    single = re.search(r"\bcountry\s*=\s*'([^']*)'", text, re.IGNORECASE)
    if single:
        return {"countries": [single.group(1)]}
    return None


def read_conditions(text):
    """``a = 'x' and b = 'y'`` as a dict, or None if it is anything else."""
    conditions = {}
    for part in re.split(r"\s+and\s+", text, flags=re.IGNORECASE):
        if "=" not in part:
            return None
        column, _, value = part.partition("=")
        parsed = read_value(value)
        if parsed is UNPARSED:
            return None
        conditions[column.strip().lower()] = parsed
    return conditions or None


def target_table_of_update(statement):
    """The table the update inside a route statement writes to."""
    match = re.search(r"\bupdate\s+([a-z_]+)", statement.low)
    return match.group(1) if match else None


HEADER = """\
# {country} rail network edits.
#
# Derived from {source} in trg-rail/africa_rail_network, adapted with the
# author's permission.
#
# Transcribed by parse_country_sql.py from {lines:,} lines of SQL: {edits} edits,
# {skipped} statements skipped as unable to reach the published network
# ({breakdown}){unhandled_note}.
#
# Order matters. Splitting an edge replaces it with two new ones, so an id used
# further down may be one an earlier edit created.
"""


def write_edits(parser, path, source, lines):
    breakdown = ", ".join(
        f"{count} {name}" for name, count in sorted(parser.skipped.items())
    )
    unhandled_note = (
        f",\n# and {len(parser.unhandled)} not transcribed - see the report"
        if parser.unhandled
        else ""
    )
    document = {"country": parser.country, "edits": parser.edits}
    body = yaml.dump(
        document,
        sort_keys=False,
        allow_unicode=True,
        width=100,
        default_flow_style=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        HEADER.format(
            country=parser.country,
            source=source,
            lines=lines,
            edits=len(parser.edits),
            skipped=sum(parser.skipped.values()),
            breakdown=breakdown or "none",
            unhandled_note=unhandled_note,
        )
        + "\n"
        + body
    )


def report(parser, verbose):
    operations = collections.Counter(edit["op"] for edit in parser.edits)
    click.echo(
        f"  {len(parser.edits):4} edits: "
        + ", ".join(f"{n} {o}" for o, n in operations.most_common())
    )
    click.echo(
        f"  {sum(parser.skipped.values()):4} skipped: "
        + ", ".join(f"{n} {r}" for r, n in parser.skipped.most_common())
    )
    if parser.unhandled:
        click.echo(f"  {len(parser.unhandled):4} NOT TRANSCRIBED:")
        shown = parser.unhandled if verbose else parser.unhandled[:10]
        for line, why, sql in shown:
            click.echo(f"       line {line}: {why}")
            click.echo(f"         {sql}")
        if len(shown) < len(parser.unhandled):
            click.echo(
                f"       ... and {len(parser.unhandled) - len(shown)} more (--verbose for all)"
            )
    else:
        click.echo("     0 not transcribed - the script is fully covered")


@click.command()
@click.option(
    "--sql",
    required=True,
    type=click.Path(exists=True),
    help="The country script to read.",
)
@click.option(
    "--country", required=True, help="The country name, as the network spells it."
)
@click.option(
    "--output", required=True, type=click.Path(), help="The edits file to write."
)
@click.option("--verbose", is_flag=True, help="List every statement not transcribed.")
@click.option(
    "--tables",
    help="Comma-separated tables whose edits count, if not the africa_osm_ ones. "
    "The four scripts that predate the continental build - Kenya, Tanzania, "
    "Uganda, Zambia - work on their own per-country tables instead.",
)
def main(sql, country, output, verbose, tables):
    """Transcribe a country's SQL script into an edits file"""
    text = Path(sql).read_text(errors="replace")
    statements = split_statements(text)
    live = [name.strip() for name in tables.split(",")] if tables else None
    parser = Parser(country, live).run(statements)

    lines = text.count("\n") + 1
    click.echo(f"{country}: {lines:,} lines, {len(statements)} statements")
    report(parser, verbose)
    write_edits(parser, Path(output), Path(sql).name, lines)
    click.echo(f"  wrote {output}")


if __name__ == "__main__":
    main()
