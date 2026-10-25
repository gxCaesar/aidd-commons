#!/usr/bin/env python3
"""Build source-derived PNG previews and vector PDFs for the figures the site places.

Each selected report generator draws its native matplotlib Figure or Canvas once. Both
files are saved from that object at its authored dimensions, before it is closed. The
preview retains the measured light palette and its non-colour encodings on a paper
surface in either site theme. No SVG is generated, transformed or removed.

Plot captions are captured from the same build and must agree with the report's caption
manifest. Schematic captions remain in their canonical authored manifest. The site
manifest binds those captions, meaningful alt text, intrinsic PNG dimensions and vector
PDF downloads to the eight actual page placements.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
FIGURE_DIR = REPO_ROOT / "report" / "figures"
DATA_DIR = REPO_ROOT / "site" / "public" / "data"
FIGURE_OUT = REPO_ROOT / "site" / "public" / "figures"
MANIFEST_PATH = REPO_ROOT / "site" / "src" / "data" / "atlas-figures.json"
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
os.environ.setdefault("MPLBACKEND", "Agg")

if str(FIGURE_DIR) not in sys.path:
    sys.path.insert(0, str(FIGURE_DIR))

from figure_sources import reading_series  # noqa: E402
from plot_5_self_record_vs_reading import READING_ID  # noqa: E402


def site_name(stem: str) -> str:
    return stem.replace("_", "-")


def save_preview(fig, stem: str, theme: str = "light") -> dict[str, Path]:
    """Save the same native drawing as a vector PDF and a 300 dpi PNG."""
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    if theme != "light":
        raise ValueError("site previews use the measured light palette on paper")
    FIGURE_OUT.mkdir(parents=True, exist_ok=True)
    pdf = FIGURE_OUT / f"{site_name(stem)}.pdf"
    png = FIGURE_OUT / f"{site_name(stem)}.png"
    with mpl.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0}):
        fig.savefig(
            pdf,
            format="pdf",
            metadata={"CreationDate": None, "Producer": "AIDD Commons report figures"},
        )
        fig.savefig(
            png,
            format="png",
            dpi=300,
            metadata={"Software": "AIDD Commons report figures"},
        )
    plt.close(fig)
    return {"pdf": pdf, "png": png}


def build_previews() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Draw only the placed figures, without writing into the report or touching SVGs."""
    import figure_style
    import matplotlib
    import schematic_style
    from PIL import Image

    written: list[dict[str, Any]] = []
    captions: dict[str, str] = {}

    def capture_caption(number: int, text: str) -> Path:
        captions[str(number)] = text
        return MANIFEST_PATH

    with (
        patch.object(figure_style, "save", save_preview),
        patch.object(figure_style, "register_caption", capture_caption),
    ):
        for row in placement_rows():
            module_name = row["stem"].replace("-", "_")
            matplotlib.rcParams.update(matplotlib.rcParamsDefault)
            if module_name.startswith("schematic_"):
                matplotlib.rcParams.update(schematic_style.house_rc())
            module = importlib.import_module(module_name)
            if site_name(module.STEM) != row["stem"]:
                raise ValueError(f"{module_name}: generator stem does not match its placement")
            if module_name.startswith("schematic_"):
                save_preview(module.build().fig, module.STEM)
            else:
                module.build()
            png = FIGURE_OUT / f"{row['stem']}.png"
            with Image.open(png) as image:
                width, height = image.size
            written.append({"stem": module.STEM, "width": width, "height": height})
    return written, captions


def comparison_payload() -> dict[str, Any]:
    """The canonical comparison projection read by the audit figures."""
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
    reading = next(row for row in comparison["second_readings"] if row["id"] == READING_ID)
    series = reading_series(comparison, reading)

    return [
        {
            "id": "artifacts",
            "stem": "schematic-01-artifacts",
            "pages": ["/"],
            "alt": (
                "Shared resource identifiers link the four artifacts and provide a route "
                "for checking how a correction affects the lesson, catalogue record, lab "
                "and report."
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
                "count at every threshold, while an external interval can remain open where "
                "depth or run basis is unverified, including in material that has been read."
            ),
        },
        {
            "id": "second-reading",
            "stem": "plot-5-self-record-vs-reading",
            "pages": ["/audit/"],
            "alt": (
                f"The retained topic readings agree with the current self record on "
                f"{reading['equal']} of {reading['cells']} topics, with "
                f"{reading['reading_deeper']} deeper and {reading['reading_shallower']} "
                f"shallower, in the comparison projection dated {series.aggregate_as_of}. "
                f"The series began on {series.initiated_on} and documents re-readings through "
                f"{series.documented_through}. These latest retained rows include reviewer "
                "authored material and constrained shallower outcomes, so they are not "
                "independent replication or evidence of reader learning."
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


def write_manifest(written: list[dict[str, Any]], emitted: dict[str, str]) -> dict[str, Any]:
    """Bind the actual products to their source captions and page placements."""
    captions = json.loads((FIGURE_DIR / "out/captions.json").read_text(encoding="utf-8"))
    schematics = json.loads(
        (FIGURE_DIR / "out/captions-schematics.json").read_text(encoding="utf-8")
    )
    for key, caption in emitted.items():
        if captions.get(key) != caption:
            raise ValueError(
                f"plot {key}: report caption is stale; run its native figure generator first"
            )
    products = {site_name(entry["stem"]): entry for entry in written}
    figures = []
    for row in placement_rows():
        product = products.get(row["stem"])
        if product is None:
            raise ValueError(f"{row['stem']}: no drawing was produced")
        figures.append(
            {
                "id": row["id"],
                "file": f"{row['stem']}.png",
                "pdf": f"{row['stem']}.pdf",
                "source_stem": product["stem"],
                "width": product["width"],
                "height": product["height"],
                "alt": row["alt"],
                "caption": caption_for(row["stem"], captions, schematics),
                "pages": row["pages"],
            }
        )
    payload = {
        "name": "atlas-figures",
        "description": (
            "Source-derived PNG previews and vector PDF downloads, drawn at their authored "
            "dimensions in the report's measured light palette on a paper surface."
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


def main() -> int:
    written, emitted = build_previews()
    payload = write_manifest(written, emitted)
    print(f"wrote {len(written)} PNG previews and vector PDFs to {FIGURE_OUT}")
    for figure in payload["figures"]:
        print(f"  {figure['id']}: {figure['width']} x {figure['height']}; {figure['pdf']}")
    print("existing SVGs were left untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
