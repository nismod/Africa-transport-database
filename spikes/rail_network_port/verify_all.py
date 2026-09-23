"""Replay every country's edits onto one network and check the result.

``apply_country_edits.py`` replays one file and compares the lines it names.
This replays all of them onto the same database - which is what the original
build does, since every script edits the one ``africa_osm_edges`` table - and
then compares the whole tagged network against the published one.

The four scripts that came through the HVT pipeline are skipped: their ids are
in a different space and their output is a shipped input rather than something
to replay. See ``edits/README.md``.

An edit that fails is counted and the replay carries on, so that one bad id
early in a file does not hide what the rest of the corpus does. The summary at
the end is the thing to read.

    python verify_all.py --database rail.duckdb \\
        --published <trg-rail>/network/africa_rail_network.geojson

Derived from the build in trg-rail/africa_rail_network, adapted with the
author's permission. This is spike code - see README.md. It is not part of the
workflow.
"""

import collections
import json
import time
from pathlib import Path

import click
import yaml
from apply_country_edits import Network
from primitives import connect
from transcribe_all import COUNTRIES

# The four whose edits run on their own tables, not the continental ones.
HVT = {slug for slug, _, _, tables in COUNTRIES if tables}


def replay(network, path, echo):
    """Apply one edits file. Returns how many worked and what failed."""
    document = yaml.safe_load(path.read_text())
    failures = collections.Counter()
    examples = {}
    applied = 0
    for index, edit in enumerate(document["edits"]):
        try:
            network.apply(edit, echo=False)
            applied += 1
        except Exception as error:  # noqa: BLE001 - the point is to keep going
            reason = f"{edit['op']}: {str(error).splitlines()[0][:70]}"
            failures[reason] += 1
            examples.setdefault(reason, index)
    if echo and failures:
        for reason, count in failures.most_common(5):
            click.echo(
                f"      {count:>4} x {reason}  (first at edit {examples[reason]})"
            )
    return applied, failures


def published_lines(path, skip_countries):
    """Edge count and length per line in the published network."""
    with open(path) as fh:
        features = json.load(fh)["features"]
    lines = collections.defaultdict(lambda: [0, 0.0])
    for feature in features:
        properties = feature["properties"]
        if properties["country"] in skip_countries:
            continue
        entry = lines[properties["line"]]
        entry[0] += 1
        entry[1] += properties["length"] / 1000
    return {line: tuple(value) for line, value in lines.items()}


def replayed_lines(con):
    return {
        line: (count, float(km))
        for line, count, km in con.execute(
            "select line, count(*), sum(length) / 1000 from edges"
            " where line is not null group by line"
        ).fetchall()
    }


# The countries the HVT branch supplies, which these edits do not produce.
HVT_COUNTRIES = {"Kenya", "Tanzania", "Uganda", "Zambia"}


@click.command()
@click.option("--database", required=True, type=click.Path(exists=True))
@click.option("--edits", default="edits", type=click.Path(exists=True, file_okay=False))
@click.option("--published", required=True, type=click.Path(exists=True))
@click.option("--report", type=click.Path(), help="Write the per-line comparison here.")
def main(database, edits, published, report):
    """Replay every country's edits and compare against the published network"""
    con = connect(database)
    network = Network(con)
    directory = Path(edits)

    total_applied = 0
    total_failed = 0
    started = time.time()
    click.echo(
        f"{'script':30} {'edits':>7} {'applied':>8} {'failed':>7} {'seconds':>8}"
    )
    for slug, _, _, tables in COUNTRIES:
        if tables:
            continue
        path = directory / f"{slug}.yaml"
        if not path.exists():
            click.echo(f"{slug:30} (no edits file)")
            continue
        count = len(yaml.safe_load(path.read_text())["edits"])
        clock = time.time()
        applied, failures = replay(network, path, echo=True)
        failed = sum(failures.values())
        total_applied += applied
        total_failed += failed
        click.echo(
            f"{slug:30} {count:>7,} {applied:>8,} {failed:>7,} {time.time() - clock:>8.1f}"
        )

    click.echo(
        f"\n{total_applied:,} edits applied, {total_failed:,} failed, "
        f"in {time.time() - started:.0f}s"
    )

    theirs = published_lines(published, HVT_COUNTRIES)
    ours = replayed_lines(con)
    # An untagged edge carries no line, in either network.
    theirs.pop(None, None)
    ours.pop(None, None)
    both = sorted(set(theirs) | set(ours))

    matched = sum(
        1
        for line in both
        if line in theirs
        and line in ours
        and theirs[line][0] == ours[line][0]
        and abs(theirs[line][1] - ours[line][1]) < 0.05
    )
    only_theirs = [line for line in both if line not in ours]
    only_ours = [line for line in both if line not in theirs]

    click.echo(
        f"\nlines: {len(theirs):,} published (excluding the HVT four), "
        f"{len(ours):,} replayed"
    )
    click.echo(f"  {matched:,} match on both edge count and length")
    click.echo(f"  {len(only_theirs):,} in the published network only")
    click.echo(f"  {len(only_ours):,} in the replay only")

    published_km = sum(km for _, km in theirs.values())
    replayed_km = sum(km for _, km in ours.values())
    click.echo(f"  {published_km:,.0f} km published, {replayed_km:,.0f} km replayed")

    if report:
        rows = ["line\tpublished_edges\tpublished_km\treplayed_edges\treplayed_km"]
        for line in both:
            their_count, their_km = theirs.get(line, (0, 0.0))
            our_count, our_km = ours.get(line, (0, 0.0))
            rows.append(
                f"{line}\t{their_count}\t{their_km:.2f}\t{our_count}\t{our_km:.2f}"
            )
        Path(report).write_text("\n".join(rows) + "\n")
        click.echo(f"\nwrote {report}")


if __name__ == "__main__":
    main()
