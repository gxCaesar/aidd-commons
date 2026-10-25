#!/usr/bin/env python3
"""Build the site's figures from the report's own generators, themed for the site.

The living report carries twenty figures. They are products of the generators in
`report/figures/`, and every number they draw is read from a committed artefact by the
script that draws it. The site wants the same drawings, in a form that follows the site's
own theme.

How this script gets at the drawings. A data figure exists only inside its generator's
`build()`, and a schematic only inside its `build()`. There is no object on disk to
re-colour, so the generators are imported and their save step is replaced: `figure_style.save`
and `schematic_style.save_pair` are replaced with a writer that emits one SVG and nothing
else. Nothing under `report/figures/` is written, and the report's own PDF and PNG products
are left exactly as they are. The caption manifests are read, never rewritten.

How the colours are themed. Every paint in the SVG is replaced by a reference to a CSS
custom property, so the drawing is the same in both themes and the reader's manual theme
choice is what decides the colours. The properties are the ones `site/src/styles/global.css`
defines: `--atlas-ink`, `--atlas-muted`, `--atlas-rule`, `--atlas-panel`, `--atlas-bg`,
`--atlas-teal`, `--atlas-teal-deep`, `--atlas-coral` and `--atlas-focus`. The palette's
categorical set, its ordered ladder and its pale washes have no single site property, so
each of those is expressed as a `color-mix` over the properties that do exist, which keeps
the relationship between the light and the dark theme rather than freezing one of them.
Every replacement carries a fallback built from CSS system colours, so a file that is opened
on its own is still legible.

The site reads the SVG as a document rather than as a picture. A picture element is a
separate document, and a separate document does not inherit the page's custom properties,
so a figure loaded as a picture cannot follow the theme at all. The component therefore
inlines the markup, where `var(--atlas-ink)` resolves against the page and the manual
toggle is followed with no script.

The manifest this script writes, `site/src/data/atlas-figures.json`, carries the file name,
the alt text, the caption and the pages of every figure the site places. Captions are copied
from the committed caption manifests. The alt texts are written here, and every number in
one is read from the committed data file its figure reads rather than typed from memory.

Determinism. The artwork carries no clock, the ids are salted per figure, and two runs of
this script produce byte-identical files.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
FIGURE_DIR = REPO_ROOT / "report" / "figures"
DATA_DIR = REPO_ROOT / "site" / "public" / "data"
FIGURE_OUT = REPO_ROOT / "site" / "public" / "figures"
MANIFEST_PATH = REPO_ROOT / "site" / "src" / "data" / "atlas-figures.json"

#: The artwork's own epoch, and a headless backend, pinned before matplotlib is imported.
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
os.environ.setdefault("MPLBACKEND", "Agg")

if str(FIGURE_DIR) not in sys.path:
    sys.path.insert(0, str(FIGURE_DIR))

#: The selector the artwork's own rules are scoped to. The root element of every product
#: carries the matching attribute, so the scoping holds whether the file is inlined in a
#: page or opened on its own.
CSS_SCOPE = "svg[data-atlas-figure]"

#: A generator is named by its family and its index. The style modules are not figures.
PLOT_PATTERN = re.compile(r"^plot_\d+_")
SCHEMATIC_PATTERN = re.compile(r"^schematic_\d+_")

PROLOG_RE = re.compile(r"^\s*<\?xml[^>]*\?>\s*")
DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>\s*", re.DOTALL)
METADATA_RE = re.compile(r"<metadata>.*?</metadata>\s*", re.DOTALL)
STYLE_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.DOTALL)
ID_RE = re.compile(r'\bid="([^"]+)"')
ID_DROP_RE = re.compile(r'\s+id="([^"]+)"')
URL_REF_RE = re.compile(r"url\(#([^)]+)\)")
HREF_REF_RE = re.compile(r'href="#([^"]+)"')
PATH_DATA_RE = re.compile(r'\sd="([^"]*)"')


# ---------------------------------------------------------------- the colour map
def colour_map() -> dict[str, dict[str, str]]:
    """Map every colour the light palette uses to the site's own properties.

    The keys are the light-theme hexes, because the report's figures are authored in the
    light theme. The values are the CSS that replaces the hex, the role the colour plays,
    and the site property the replacement is built on.

    A colour that has no site property of its own becomes a `color-mix` of the properties
    that do exist. The pale washes are a wash of their own mark colour, and the ordered
    ladder is a ramp from the panel towards the deep teal, which is the relationship the
    palette module measured and the relationship the dark theme needs as well: pale to
    deep in the light theme and deep to pale in the dark one.
    """
    import atlas_palette

    tokens = atlas_palette.tokens("light")
    categorical = atlas_palette.categorical("light")
    ladder = atlas_palette.ladder("light")
    fills = atlas_palette.fills("light")

    mapping: dict[str, dict[str, str]] = {}

    def put(hex_value: str, css: str, role: str, variable: str) -> None:
        key = hex_value.lower()
        existing = mapping.get(key)
        if existing is not None and existing["css"] != css:
            raise ValueError(
                f"{hex_value} maps to two different expressions: {existing['css']} and {css}"
            )
        mapping[key] = {"css": css, "role": role, "variable": variable}

    put(tokens["bg"], "var(--atlas-bg, Canvas)", "page background", "--atlas-bg")
    put(tokens["panel"], "var(--atlas-panel, Canvas)", "paper background", "--atlas-panel")
    put(tokens["ink"], "var(--atlas-ink, CanvasText)", "text and key marks", "--atlas-ink")
    put(tokens["muted"], "var(--atlas-muted, GrayText)", "secondary text", "--atlas-muted")
    put(
        tokens["rule"],
        "var(--atlas-rule, color-mix(in srgb, CanvasText 22%, Canvas))",
        "hairlines and grid",
        "--atlas-rule",
    )
    put(tokens["teal"], "var(--atlas-teal, teal)", "teal mark", "--atlas-teal")
    put(tokens["teal_deep"], "var(--atlas-teal-deep, darkslategray)", "deep teal", "--atlas-teal-deep")
    put(tokens["coral"], "var(--atlas-coral, coral)", "coral mark", "--atlas-coral")
    put(tokens["focus"], "var(--atlas-focus, orangered)", "warm accent", "--atlas-focus")

    # The categorical set. Four roles, four site properties: the two teals carry the cool
    # end, the coral and the warm accent carry the warm end, and the muted token carries
    # the neutral. Every one of these keys also carries a marker, a hatch or a dash, so
    # the series are separated by a second channel and not by hue alone.
    put(categorical["teal"], "var(--atlas-teal, teal)", "categorical teal", "--atlas-teal")
    put(categorical["coral"], "var(--atlas-coral, coral)", "categorical coral", "--atlas-coral")
    put(categorical["ember"], "var(--atlas-focus, orangered)", "categorical ember", "--atlas-focus")
    put(categorical["slate"], "var(--atlas-muted, GrayText)", "categorical slate", "--atlas-muted")

    # The pale washes. A wash of the mark colour over the panel, so the wash follows the
    # theme instead of glowing white on a dark one.
    for key, variable in (
        ("teal", "--atlas-teal"),
        ("coral", "--atlas-coral"),
        ("ember", "--atlas-focus"),
        ("slate", "--atlas-muted"),
    ):
        put(
            fills[key],
            f"color-mix(in srgb, var({variable}) 16%, var(--atlas-panel, Canvas))",
            f"pale wash, {key}",
            variable,
        )

    # The ordered ladder, low to high. The wash nearest the panel is the low end of a
    # scale rather than a mark that has to be read on its own.
    for index, hex_value in enumerate(ladder):
        percent = 12 + index * 19
        put(
            hex_value,
            f"color-mix(in srgb, var(--atlas-teal-deep, darkslategray) {percent}%, "
            "var(--atlas-panel, Canvas))",
            f"ordered ladder, step {index}",
            "--atlas-teal-deep",
        )

    return mapping


# ---------------------------------------------------------------- the SVG writer
def svg_text(fig, path: Path) -> str:
    """Write one SVG and return its text.

    The text in the SVG stays text, so the file is small and the type is the reader's
    type rather than a drawing of it. The date is suppressed, so two runs of this script
    produce the same bytes.
    """
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    with mpl.rc_context(
        {
            "savefig.bbox": None,
            "savefig.pad_inches": 0,
            "svg.fonttype": "none",
            "svg.hashsalt": "aidd-commons-site-figures",
        }
    ):
        fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- the SVG surgery
def strip_document_noise(svg: str) -> str:
    """Remove the parts of an SVG document that the site has no use for.

    The XML declaration, the doctype and the RDF metadata block are all optional in an
    SVG document, and the doctype names an external DTD that a browser never fetches.
    """
    svg = PROLOG_RE.sub("", svg, count=1)
    svg = DOCTYPE_RE.sub("", svg, count=1)
    svg = METADATA_RE.sub("", svg, count=1)
    return svg


def scope_styles(svg: str) -> str:
    """Scope the artwork's own CSS rules to the artwork.

    Matplotlib writes one global rule for the whole document. Inlined in a page that rule
    would reach the page, so every selector is scoped to the figure's own root element.
    """

    def rewrite(match: re.Match[str]) -> str:
        rules = []
        for rule in match.group(2).split("}"):
            rule = rule.strip()
            if not rule:
                continue
            selector, _, body = rule.partition("{")
            selectors = []
            for part in selector.split(","):
                part = part.strip()
                if not part:
                    continue
                selectors.append(CSS_SCOPE if part == "*" else f"{CSS_SCOPE} {part}")
            if not selectors:
                continue
            rules.append(f"{', '.join(selectors)}{{{body}}}")
        return f"{match.group(1)}{''.join(rules)}{match.group(3)}"

    return STYLE_RE.sub(rewrite, svg)


def namespace_ids(svg: str, prefix: str) -> str:
    """Give every id in the file a per-figure prefix.

    Two figures inlined in one page would otherwise share the ids their generator
    produced, because the generator numbers its objects from one in every run.
    """
    svg = URL_REF_RE.sub(lambda m: f"url(#{prefix}{m.group(1)})", svg)
    svg = HREF_REF_RE.sub(lambda m: f'href="#{prefix}{m.group(1)}"', svg)
    return ID_RE.sub(lambda m: f'id="{prefix}{m.group(1)}"', svg)


def tag_root(svg: str, figure_id: str) -> str:
    """Mark the root element, so the scoped rules match it."""
    return re.sub(
        r"<svg\b",
        f'<svg data-atlas-figure="{figure_id}"',
        svg,
        count=1,
    )


def minify(svg: str) -> str:
    """Remove what carries no information.

    The whitespace between two elements is not content. The whitespace inside a path's
    `d` attribute separates its commands and is collapsed to a single space, which the
    path grammar reads the same way. A coordinate is written to two decimals, which is a
    hundredth of a point on a figure that is seven inches wide and therefore far below
    what a reader can see. The ids nothing refers to are dropped, which is most of them:
    a generator numbers its objects for its own bookkeeping and the site never asks for
    them by name.
    """
    referenced = set(URL_REF_RE.findall(svg)) | set(HREF_REF_RE.findall(svg))

    def drop_unused_id(match: re.Match[str]) -> str:
        return "" if match.group(1) not in referenced else match.group(0)

    def squeeze_path(match: re.Match[str]) -> str:
        data = re.sub(r"\s+", " ", match.group(1)).strip()
        return f' d="{data}"'

    def round_number(match: re.Match[str]) -> str:
        return f"{float(match.group(0)):.2f}"

    svg = ID_DROP_RE.sub(drop_unused_id, svg)
    svg = PATH_DATA_RE.sub(squeeze_path, svg)
    svg = re.sub(r"-?\d+\.\d{3,}", round_number, svg)
    svg = re.sub(r">\s+<", "><", svg)
    return svg.strip()


def theme_svg(svg: str, figure_id: str, mapping: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    """Replace every colour in the file with a property reference.

    Returns the themed file and the list of colours that were left behind, which is empty
    unless a figure draws a colour the palette does not define.
    """
    leftover: list[str] = []

    def replace(match: re.Match[str]) -> str:
        hex_value = match.group(0).lower()
        entry = mapping.get(hex_value)
        if entry is None:
            leftover.append(hex_value)
            return match.group(0)
        return entry["css"]

    svg = re.sub(r"#[0-9a-fA-F]{6}\b", replace, svg)
    svg = strip_document_noise(svg)
    svg = scope_styles(svg)
    svg = namespace_ids(svg, f"{figure_id}-")
    svg = tag_root(svg, figure_id)
    svg = minify(svg)
    return svg, sorted(set(leftover))


# ---------------------------------------------------------------- the generators
def generator_names(pattern: re.Pattern[str]) -> list[str]:
    """The module names of the generators that match `pattern`, in name order."""
    return sorted(path.stem for path in FIGURE_DIR.glob("*.py") if pattern.match(path.stem))


def reset_style() -> None:
    """Put matplotlib's rcParams back to their defaults.

    The two families of figure do not share a style, and the order the generators run in
    must not reach the artwork.
    """
    import matplotlib

    matplotlib.rcParams.update(matplotlib.rcParamsDefault)


def site_name(stem: str) -> str:
    """The site's file name for one figure.

    The generators name a data figure with underscores and a schematic with a hyphen. The
    site uses one spelling, so the file name is the stem with hyphens throughout, which
    also keeps the report's own product names untouched.
    """
    return stem.replace("_", "-")


def build_svgs() -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Draw every figure and write its themed SVG.

    The report's own save step is replaced for the length of the run, so that nothing
    under `report/figures/` is written and the caption manifests are left alone. The
    figures directory holds exactly what this run produced: a file left there by an
    earlier run under a name this run does not use is a stale product, and it is removed
    rather than shipped beside its replacement.
    """
    import figure_style
    import matplotlib.pyplot as plt
    import schematic_style

    written: list[dict[str, Any]] = []
    leftovers: dict[str, list[str]] = {}

    def site_save(fig, stem: str, *args: Any, **kwargs: Any) -> dict[str, Path]:
        path = FIGURE_OUT / f"{site_name(stem)}.svg"
        svg_text(fig, path)
        return {"svg": path}

    def site_save_pair(fig, out_dir: Path, stem: str) -> tuple[Path, Path]:
        path = FIGURE_OUT / f"{site_name(stem)}.svg"
        svg_text(fig, path)
        return path, path

    figure_style.save = site_save  # type: ignore[assignment]
    figure_style.register_caption = lambda number, text: FIGURE_OUT  # type: ignore[assignment]
    schematic_style.save_pair = site_save_pair  # type: ignore[assignment]

    mapping = colour_map()

    for name in generator_names(PLOT_PATTERN):
        reset_style()
        module = importlib.import_module(name)
        module.build()
        stem = module.STEM
        path = FIGURE_OUT / f"{site_name(stem)}.svg"
        svg, leftover = theme_svg(path.read_text(encoding="utf-8"), site_name(stem), mapping)
        path.write_text(svg, encoding="utf-8")
        leftovers[stem] = leftover
        written.append({"stem": stem, "path": path, "family": "plot"})
        plt.close("all")

    for name in generator_names(SCHEMATIC_PATTERN):
        reset_style()
        import matplotlib

        matplotlib.rcParams.update(schematic_style.house_rc())
        module = importlib.import_module(name)
        module.main()
        stem = module.STEM
        path = FIGURE_OUT / f"{site_name(stem)}.svg"
        svg, leftover = theme_svg(path.read_text(encoding="utf-8"), site_name(stem), mapping)
        path.write_text(svg, encoding="utf-8")
        leftovers[stem] = leftover
        written.append({"stem": stem, "path": path, "family": "schematic"})
        plt.close("all")

    return written, leftovers


def remove_stale(written: list[dict[str, Any]]) -> list[str]:
    """Remove the figures this run did not write.

    The directory is this script's output, and a file in it that no generator produced
    is a leftover from an earlier run under a name that no longer exists. It is removed
    so that the release does not ship two copies of the same drawing.
    """
    keep = {entry["path"].name for entry in written}
    removed: list[str] = []
    for path in sorted(FIGURE_OUT.glob("*.svg")):
        if path.name not in keep:
            path.unlink()
            removed.append(path.name)
    return removed


# ---------------------------------------------------------------- the manifest
def comparison_payload() -> dict[str, Any]:
    """The frozen comparison audit, the file two of the placed figures read."""
    return json.loads((DATA_DIR / "comparison.v1.json").read_text(encoding="utf-8"))


def placement_rows() -> list[dict[str, Any]]:
    """The figures the site places, with the alt text of each.

    The alt text states what a reader should take from the figure. It is not the caption
    again: the caption says what the figure is, the alt says what it settles. Every
    number in an alt text is read from the committed file its figure reads, and is
    formatted in here rather than typed.
    """
    comparison = comparison_payload()
    topics = comparison["taxonomy"]["topics"]
    reading = comparison["second_readings"][0]

    return [
        {
            "id": "artifacts",
            "stem": "schematic-01-artifacts",
            "pages": ["/"],
            "alt": (
                "The four artifacts are coupled by shared resource identifiers rather than by "
                "proximity: a correction recorded once on the identifier rail reaches the "
                "lesson, the catalogue record, the lab and the report, so the four surfaces "
                "cannot drift apart without the drift being visible."
            ),
        },
        {
            "id": "decision-pipeline",
            "stem": "schematic-03-decision-pipeline",
            "pages": ["/"],
            "alt": (
                "Nine decision stages narrow a candidate set, and every stage draws the branch "
                "that leaves the funnel for the failure mode the stage table records, so the "
                "attrition and the way out of it are both visible."
            ),
        },
        {
            "id": "prerequisite-graph",
            "stem": "schematic-05-prerequisite-graph",
            "pages": ["/"],
            "alt": (
                "The specialist routes are not independent: a small set of lessons is a "
                "prerequisite for several routes at once, and the badge on each lesson counts "
                "how many routes require it, so the shared core of the curriculum can be seen "
                "without reading the edges."
            ),
        },
        {
            "id": "coverage-bounds",
            "stem": "plot-2-coverage-bounds",
            "pages": ["/audit/"],
            "alt": (
                f"The audit reports an interval rather than a leaderboard: all {topics} AIDD "
                "Commons cells are direct observations, so this project's own row is an exact "
                "count at every threshold, while every external row is a range that only the "
                "cells nobody has read can widen."
            ),
        },
        {
            "id": "second-reading",
            "stem": "plot-5-self-record-vs-reading",
            "pages": ["/audit/"],
            "alt": (
                f"A second reading by a reviewer from a different model family agreed with this "
                f"project's own record on {reading['equal']} of the {reading['cells']} topics and "
                f"read {reading['reading_deeper']} deeper and {reading['reading_shallower']} "
                "shallower, so the depth this project claims for itself is the part of the "
                "record a reader has to treat as unsettled."
            ),
        },
        {
            "id": "representation-flips",
            "stem": "plot-9-representation-ranking-flips",
            "pages": ["/labs/"],
            "alt": (
                "The baseline that wins the primary partition loses the separate assay "
                "replication by a wide margin, so a frozen evaluation fixes a protocol and a "
                "result, not a ranking that holds on the next evaluation."
            ),
        },
        {
            "id": "frozen-lifecycle",
            "stem": "schematic-07-frozen-lifecycle",
            "pages": ["/labs/"],
            "alt": (
                "A frozen lab writes the protocol before the held-out result is seen, runs its "
                "pretests on training and validation data, opens the test set once, and treats "
                "a bug found after the opening as an error that invalidates the protocol rather "
                "than a result to be reported."
            ),
        },
        {
            "id": "statement-classes",
            "stem": "schematic-02-statement-classes",
            "pages": ["/report/"],
            "alt": (
                "Every statement in the report belongs to one of four classes, and the two "
                "classes that assert something are drawn apart from the two that do not, so a "
                "reader can tell an observed fact from a decision, an open question or a plan."
            ),
        },
    ]


def caption_for(stem: str, captions: dict[str, str], schematics: dict[str, str]) -> str:
    """The committed caption of one figure, by the figure's site name."""
    schematic = re.match(r"schematic-(\d+)-", stem)
    if schematic:
        return schematics[f"S{int(schematic.group(1))}"]
    plot = re.match(r"plot-(\d+)-", stem)
    if not plot:
        raise SystemExit(f"{stem} is not a figure name")
    return captions[plot.group(1)]


def write_manifest(written: list[dict[str, Any]]) -> dict[str, Any]:
    """Write the manifest the site reads.

    Captions come from the committed caption manifests. The file names come from the
    figures that were drawn. The pages and the alt texts are the editorial decisions, and
    they live in this script so that the manifest cannot drift from the figures.
    """
    captions = json.loads(
        (FIGURE_DIR / "out" / "captions.json").read_text(encoding="utf-8")
    )
    schematics = json.loads(
        (FIGURE_DIR / "out" / "captions-schematics.json").read_text(encoding="utf-8")
    )
    stems = {site_name(entry["stem"]) for entry in written}

    figures = []
    for row in placement_rows():
        if row["stem"] not in stems:
            raise SystemExit(f"the figure {row['stem']} was not drawn; the manifest is incomplete")
        figures.append(
            {
                "id": row["id"],
                "file": f"{row['stem']}.svg",
                "alt": row["alt"],
                "caption": caption_for(row["stem"], captions, schematics),
                "pages": row["pages"],
            }
        )

    payload = {
        "name": "atlas-figures",
        "description": (
            "The figures the site publishes, drawn by the report's own generators and "
            "themed with the site's own properties."
        ),
        "generated_by": "site/scripts/make-site-figures.py",
        "drawings_from": "report/figures/",
        "captions_from": [
            "report/figures/out/captions.json",
            "report/figures/out/captions-schematics.json",
        ],
        "figures": figures,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload


# ---------------------------------------------------------------- the report
def main() -> int:
    FIGURE_OUT.mkdir(parents=True, exist_ok=True)
    written, leftovers = build_svgs()
    stale = remove_stale(written)
    payload = write_manifest(written)

    mapping = colour_map()
    print(f"wrote {len(written)} figures to {FIGURE_OUT}")
    for name in stale:
        print(f"  removed the stale product {name}")
    for entry in written:
        size = entry["path"].stat().st_size
        print(f"  {entry['path'].name}  {size:>7} bytes")
        if leftovers.get(entry["stem"]):
            print(f"    colours left as literals: {', '.join(leftovers[entry['stem']])}")

    print()
    print("colour map")
    for hex_value, entry in sorted(mapping.items()):
        print(f"  {hex_value}  {entry['role']:<28} {entry['variable']}")
        print(f"      {entry['css']}")

    print()
    print(f"manifest {MANIFEST_PATH}")
    for figure in payload["figures"]:
        print(f"  {figure['id']:<22} {figure['file']:<40} {', '.join(figure['pages'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
