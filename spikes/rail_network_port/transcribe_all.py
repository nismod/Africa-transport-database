"""Transcribe every country script, and write the checklist of what happened.

``parse_country_sql.py`` does one script. This does all 24 and writes
``edits/README.md``, which is the status table for the port: how many edits
came out of each script, how many statements were skipped and why, and what is
left.

Gabon is the regression test rather than an output. ``edits/gabon.yaml`` was
written by hand from gabon.sql before the parser existed, and replaying it
reproduces the published Gabon network exactly, so it is the one file where the
right answer is known independently. This checks the parser still produces the
same operations from the same SQL, and fails if it does not.

Four of the scripts - Kenya, Tanzania, Uganda and Zambia - predate the
continental build and work on their own per-country tables, which the repo does
not ship. See ``HVT_NOTE`` below.

    python transcribe_all.py --scripts <trg-rail>/countries_sql_scripts

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission. This is spike code - see README.md. It is not part of the
workflow.
"""

import collections
from pathlib import Path

import click
import yaml
from parse_country_sql import Parser, split_statements, write_edits

# slug, script, the name to put in the file, and the tables whose edits count.
# The label is the script's own subject; the `country` column of the prepared
# network comes from stage 1's spatial join, not from these, and several
# scripts cover a region rather than one country.
COUNTRIES = [
    ("algeria", "algeria/algeria.sql", "Algeria", None),
    ("angola", "angola/angola.sql", "Angola", None),
    ("botswana", "botswana/botswana.sql", "Botswana", None),
    ("cameroon", "cameroon/cameroon.sql", "Cameroon", None),
    (
        "congo_brazzaville",
        "congo-brazzaville/congo-brazzaville.sql",
        "Congo-Brazzaville",
        None,
    ),
    ("drc", "drc/drc.sql", "Democratic Republic of the Congo", None),
    ("egypt", "egypt/egypt.sql", "Egypt", None),
    (
        "eritrea_djibouti_ethiopia",
        "eritrea_djibouti_ethiopia/eritrea_djibouti_ethiopia.sql",
        "Eritrea, Djibouti and Ethiopia",
        None,
    ),
    ("eswatini", "eswatini/eswatini.sql", "Eswatini", None),
    ("gabon", "gabon/gabon.sql", "Gabon", None),
    ("kenya", "kenya/kenya.sql", "Kenya", ["kenya_osm_edges", "kenya_osm_nodes"]),
    ("malawi", "malawi/malawi.sql", "Malawi", None),
    ("morocco", "morocco/morocco.sql", "Morocco", None),
    ("mozambique", "mozambique/mozambique.sql", "Mozambique", None),
    ("namibia", "namibia/namibia.sql", "Namibia", None),
    ("nigeria", "nigeria/nigeria.sql", "Nigeria", None),
    ("south_africa", "south africa/southafrica.sql", "South Africa", None),
    ("sudan", "sudan/sudan.sql", "Sudan and South Sudan", None),
    (
        "tanzania",
        "tanzania/tanzania.sql",
        "Tanzania",
        ["tanzania_osm_edges", "tanzania_osm_nodes"],
    ),
    ("tunisia", "tunisia/tunisia.sql", "Tunisia", None),
    ("uganda", "uganda/uganda.sql", "Uganda", ["uganda_osm_edges", "uganda_osm_nodes"]),
    (
        "west_africa_ex_nigeria",
        "west_africa_ex_nigeria/west_africa.sql",
        "West Africa except Nigeria",
        None,
    ),
    ("zambia", "zambia/zambia.sql", "Zambia", ["zambia_osm_edges", "zambia_osm_nodes"]),
    ("zimbabwe", "zimbabwe/zimbabwe.sql", "Zimbabwe", None),
]

# The file the parser is checked against, rather than one it writes.
REFERENCE = "gabon"

HVT_NOTE = """\
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
"""


def transcribe(root, slug, script, label, tables, output_directory):
    """Parse one script. Returns the parser and the number of lines read."""
    path = root / script
    text = path.read_text(errors="replace")
    parser = Parser(label, tables).run(split_statements(text))
    lines = text.count("\n") + 1
    if slug != REFERENCE:
        write_edits(parser, output_directory / f"{slug}.yaml", path.name, lines)
    return parser, lines


def check_reference(parser, path):
    """Compare the parser's Gabon against the hand-written file.

    The notes differ - the hand-written ones are paraphrases, the parser keeps
    the script's own words - so only the operations are compared.
    """
    expected = yaml.safe_load(path.read_text())["edits"]

    def strip(edit):
        return {key: value for key, value in edit.items() if key != "note"}

    if len(expected) != len(parser.edits):
        return f"{len(expected)} edits in the file, {len(parser.edits)} from the parser"
    for index, (left, right) in enumerate(zip(expected, parser.edits)):
        if strip(left) != strip(right):
            return f"edit {index} differs: {strip(left)} vs {strip(right)}"
    return None


TABLE_HEADER = """\
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
"""


def write_checklist(rows, path, totals, operations, skips, hvt):
    lines = [TABLE_HEADER.rstrip("\n")]
    for slug, label, line_count, parser in rows:
        mark = " *" if slug in hvt else ""
        lines.append(
            f"| [`{slug}.yaml`]({slug}.yaml){mark} | {line_count:,} | {len(parser.edits):,} | "
            f"{sum(parser.skipped.values()):,} | {len(parser.unhandled) or ''} |"
        )
    lines.append(
        f"| **{len(rows)} scripts** | **{totals['lines']:,}** | **{totals['edits']:,}** | "
        f"**{totals['skipped']:,}** | **{totals['gaps']}** |"
    )
    lines.append("")
    lines.append("`*` runs on its own tables, not the continental ones - see below.")
    lines.append("")
    lines.append("## Operations")
    lines.append("")
    lines.append("| operation | count |")
    lines.append("| --- | ---: |")
    for operation, count in operations.most_common():
        lines.append(f"| `{operation}` | {count:,} |")
    lines.append("")
    lines.append("## Statements skipped")
    lines.append("")
    lines.append("None of these can reach the published network.")
    lines.append("")
    lines.append("| reason | count |")
    lines.append("| --- | ---: |")
    for reason, count in skips.most_common():
        lines.append(f"| {reason} | {count:,} |")
    lines.append("")
    lines.append("## The four that came through the HVT pipeline")
    lines.append("")
    lines.append(HVT_NOTE)
    path.write_text("\n".join(lines))


@click.command()
@click.option(
    "--scripts",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="The countries_sql_scripts directory of a trg-rail checkout.",
)
@click.option(
    "--output", default="edits", type=click.Path(), help="Where the edit files go."
)
@click.option("--verbose", is_flag=True, help="List every statement not transcribed.")
def main(scripts, output, verbose):
    """Transcribe every country script and write the checklist"""
    root = Path(scripts)
    output_directory = Path(output)
    output_directory.mkdir(parents=True, exist_ok=True)

    rows = []
    operations = collections.Counter()
    skips = collections.Counter()
    totals = collections.Counter()
    hvt = {slug for slug, _, _, tables in COUNTRIES if tables}

    for slug, script, label, tables in COUNTRIES:
        parser, lines = transcribe(root, slug, script, label, tables, output_directory)
        rows.append((slug, label, lines, parser))
        operations.update(edit["op"] for edit in parser.edits)
        skips.update(parser.skipped)
        totals.update(
            lines=lines,
            edits=len(parser.edits),
            skipped=sum(parser.skipped.values()),
            gaps=len(parser.unhandled),
        )
        flag = f"  {len(parser.unhandled)} gaps" if parser.unhandled else ""
        click.echo(
            f"  {slug:28} {lines:>7,} lines  {len(parser.edits):>5,} edits{flag}"
        )
        if verbose:
            for line, why, sql in parser.unhandled:
                click.echo(f"      line {line}: {why}")

        if slug == REFERENCE:
            difference = check_reference(parser, output_directory / f"{slug}.yaml")
            if difference:
                raise SystemExit(
                    f"\n{slug}.yaml no longer matches the parser: {difference}"
                )
            click.echo(f"  {'':28} {slug}.yaml still matches the parser")

    write_checklist(
        rows, output_directory / "README.md", totals, operations, skips, hvt
    )
    click.echo(
        f"\n{len(rows)} scripts, {totals['lines']:,} lines -> {totals['edits']:,} edits, "
        f"{totals['skipped']:,} skipped, {totals['gaps']} not transcribed"
    )
    click.echo(f"wrote {output_directory}/README.md")


if __name__ == "__main__":
    main()
