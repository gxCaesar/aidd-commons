"""Registry composition by kind.

Source of every number: `site/public/data/resources.v1.json`, the catalogue
export that `scripts/catalog/export.ts` generates from `catalog/resources/*.yaml`.
This is a live projection, not a frozen release snapshot. Its caption identifies
the projection schema and the range of record verification dates. Nothing in
this script is estimated or carried over from an earlier export.

What the figure shows: how many records of each kind the registry holds.

What it does not show: whether a record is any good. A count of kinds is not a
count of working resources. The registry records a lifecycle status, an access
level and seven openness dimensions per record, and none of those is folded into
this figure, because most records are still unverified and the interesting
question about the registry is not how many records it has but how much of it
has been read.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)
from figure_sources import catalogue_projection  # noqa: E402

FIGURE_NUMBER = 1
STEM = "plot_1_registry_composition"


def caption(resources: list[dict], ordered: list[tuple[str, int]]) -> str:
    """The caption fragment, with its numbers taken from the file that was read."""
    kinds = ", ".join(f"{count} {name.replace('-', ' ')}" for name, count in ordered)
    snapshot = catalogue_projection(resources)
    return (
        f"Registry composition by kind. {snapshot.records} catalogue records: {kinds}. "
        f"{snapshot.source_note()} "
        "A count of records says nothing about whether a record has been verified, and the figure "
        "carries no status, access or openness information."
    )


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    resources = style.load_json(style.DATA_DIR / "resources.v1.json")

    counts = Counter(record["kind"] for record in resources)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    names = [name for name, _ in ordered]
    values = [count for _, count in ordered]

    fig = style.figure(style.FIGURE_WIDTH, 4.2)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.16, right=0.97, bottom=0.13, top=0.90)

    positions = list(range(len(names)))[::-1]
    container = ax.barh(
        positions,
        values,
        height=0.68,
        color=style.categorical()["teal"],
        edgecolor=tokens["ink"],
        linewidth=0.6,
    )
    for bar, index in zip(container, range(len(names)), strict=True):
        bar.set_hatch(style.hatch_for_index(index))

    ax.set_yticks(positions)
    ax.set_yticklabels([name.replace("-", " ") for name in names])
    ax.set_xlabel("Records in the catalogue")
    ax.set_xlim(0, max(values) * 1.14)
    ax.xaxis.grid(True, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["left"].set_color(tokens["rule"])
    style.title(ax, "Registry composition by kind")
    style.bar_labels(ax, container, values, orientation="horizontal", pad=4)

    ax.text(
        0.995,
        1.02,
        f"{sum(values)} records",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.5,
        color=tokens["muted"],
    )

    written = style.save(fig, STEM)
    style.register_caption(FIGURE_NUMBER, caption(resources, ordered))
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
