"""Write out every file the workflow's rules name, as a tree.

A developer utility rather than a workflow step, which is why it is here and
not in ``scripts`` - everything there is run by a rule.

The paths come from snakemake's own parse of the workflow, not from reading
the rule files as text, so ``expand()`` and ``multiext()`` are already
resolved. Where a wildcard rule and the concrete paths it stands for both
appear, the concrete ones are folded back into the wildcard: the 54 per
country HeiGIT GeoPackages become one ``heigit_{iso3}_...`` line, and the
pinned OSM snapshot becomes one ``planet-{snapshot}...`` line rather than two
entries that look like a mismatch.

    python tools/workflow_tree.py --output docs/workflow_tree.txt

Defaults to ``config.template.json`` so the tree reads with the generic
``incoming_data``, ``processed_data``, ``results`` and ``figures`` names
rather than whichever local directories a working ``config.json`` points at.
"""

import collections
import re
from pathlib import Path

import click
from snakemake.api import ConfigSettings, ResourceSettings, SnakemakeApi

# Snakemake has no public accessor for a parsed workflow's rules, so this
# reaches for the one the API holds. If a snakemake upgrade breaks it, the
# rules are also in `WorkflowApi._get_workflow()`.
WORKFLOW_ATTRIBUTE = "_workflow"


def read_declarations(snakefile, configfile):
    """Every (path, "in"/"out", rule) the workflow declares, and its config."""
    with SnakemakeApi() as api:
        workflow_api = api.workflow(
            resource_settings=ResourceSettings(),
            config_settings=ConfigSettings(configfiles=[configfile]),
            snakefile=snakefile,
        )
        workflow = getattr(workflow_api, WORKFLOW_ATTRIBUTE)
        declarations = [
            (str(item), kind, rule.name)
            for rule in workflow.rules
            for kind, io in (("in", rule.input), ("out", rule.output))
            for item in io
        ]
        return declarations, workflow.config, len(workflow.rules)


def wildcard_matcher(path):
    """A regex for the concrete paths one wildcard path stands for."""
    parts = re.split(r"(\{[^{}]*\})", path)
    pattern = "".join(
        "[^/]+" if part.startswith("{") else re.escape(part) for part in parts
    )
    return re.compile(pattern + "$")


def fold_onto_wildcards(declarations):
    """Collect declarations by path, folding concrete paths into wildcards.

    Returns each path mapped to the rules that read it, the rules that write
    it, and how many concrete paths it stands for.
    """
    paths = {path for path, _, _ in declarations}
    matchers = [(path, wildcard_matcher(path)) for path in sorted(paths) if "{" in path]

    def target(path):
        if "{" in path:
            return path
        for wildcard, matcher in matchers:
            if matcher.match(path):
                return wildcard
        return path

    files = collections.defaultdict(
        lambda: {"in": set(), "out": set(), "concrete": set()}
    )
    for path, kind, rule in declarations:
        entry = files[target(path)]
        entry[kind].add(rule)
        if "{" not in path:
            entry["concrete"].add(path)
    return files


def build_tree(paths, root):
    """Nest the paths under one root by directory. Leaves are empty dicts."""

    def node():
        return collections.defaultdict(node)

    tree = node()
    for path in paths:
        if path == root or not path.startswith(root + "/"):
            continue
        branch = tree
        for part in path[len(root) + 1 :].split("/"):
            branch = branch[part]
    return tree


def describe(entry):
    """The annotation for one file: who reads it, who writes it, how many."""
    if entry["out"] and entry["in"]:
        note = "in out  <- " + ", ".join(sorted(entry["out"]))
    elif entry["out"]:
        note = "    out  <- " + ", ".join(sorted(entry["out"]))
    else:
        note = "in"
    if len(entry["concrete"]) > 1:
        note += f"  ({len(entry['concrete'])} files)"
    return note


def render(tree, files, prefix="", trail=()):
    """Tree lines as (text, annotation) pairs, directories before files."""
    lines = []
    items = sorted(tree.items(), key=lambda kv: (not kv[1], kv[0].lower()))
    for index, (name, child) in enumerate(items):
        last = index == len(items) - 1
        path = "/".join(trail + (name,))
        lines.append(
            (
                prefix + ("└── " if last else "├── ") + name,
                describe(files[path]) if path in files else None,
            )
        )
        lines += render(
            child, files, prefix + ("    " if last else "│   "), trail + (name,)
        )
    return lines


def roots_in_order(config, paths):
    """The config directories, in config order, then whatever else appears.

    Grouping by the configured directory rather than by the first path segment
    keeps the tree readable when config.json points at absolute paths.
    """
    ordered = []
    for value in config.get("paths", {}).values():
        root = str(Path(value))
        if root not in ordered:
            ordered.append(root)

    covered = [path for path in paths if any(path.startswith(r + "/") for r in ordered)]
    ordered += sorted(
        {path.split("/")[0] for path in set(paths) - set(covered)} - set(ordered)
    )
    return [
        root for root in ordered if any(path.startswith(root + "/") for path in paths)
    ]


HEADER = """\
Files named by the rules in {snakefile}, from snakemake's own parse of the
workflow. Paths are as {configfile} sets them.

    in            read by a rule
    out <- rule   written by that rule
    ({{n}} files)    a wildcard rule, and the {{n}} concrete paths folded into it

Regenerate with: python tools/workflow_tree.py
"""


@click.command()
@click.option("--snakefile", default="Snakefile", type=click.Path(exists=True))
@click.option(
    "--configfile", default="config.template.json", type=click.Path(exists=True)
)
@click.option("--output", required=True, type=click.Path())
def main(snakefile, configfile, output):
    """Write the workflow's input and output files out as a tree"""
    declarations, config, rule_count = read_declarations(
        Path(snakefile), Path(configfile)
    )
    files = fold_onto_wildcards(declarations)

    lines = []
    for root in roots_in_order(config, files):
        lines.append((root, describe(files[root]) if root in files else None))
        lines += render(build_tree(files, root), files, trail=(root,))
        lines.append(("", None))

    width = max(len(text) for text, note in lines if note)
    read = sum(1 for f in files.values() if f["in"] and not f["out"])
    written = sum(1 for f in files.values() if f["out"] and not f["in"])
    both = sum(1 for f in files.values() if f["in"] and f["out"])
    summary = (
        f"{len(files)} paths across {rule_count} rules: {read} only read, "
        f"{written} only written, {both} both written and read"
    )

    body = [
        f"{text.ljust(width + 2)}{note}".rstrip() if note else text
        for text, note in lines
    ]
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(
        HEADER.format(snakefile=snakefile, configfile=configfile)
        + "\n"
        + "\n".join(body + [summary])
        + "\n"
    )

    click.echo(f"{output}: {summary}")


if __name__ == "__main__":
    main()
