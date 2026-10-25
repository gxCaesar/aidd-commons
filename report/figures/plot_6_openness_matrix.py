"""Openness matrix by record kind.

Source of every number: `site/public/data/openness.v1.json`, the openness
projection of the catalogue export, joined to `site/public/data/resources.v1.json`
on the record id to recover the record's kind. The join key is the id and
nothing else; the openness values are not recomputed.

What the figure shows. Each cell is one record kind against one of the seven
openness dimensions. The fill is the share of that kind's records for which the
dimension is available, counted over the records for which the dimension
applies at all, because a dimension that does not apply to a record kind is
not evidence about it. The hatch says why the rest is not available: an
unverified dimension is unknown, a dimension recorded as not available is
decided, and a dimension that does not apply to that kind is outside the
question.

What it does not show. Openness is recorded per dimension and never collapsed
into a single label, so this figure does not collapse it either. A cell that
reads available says that the resource for that dimension was seen; it does not
say that the artefact runs, that it is maintained, or that it does what its
documentation claims. The largest cell in this matrix is unverified, and that
is a statement about what has been read rather than about what exists.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from matplotlib.patches import Rectangle

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 6
STEM = "plot_6_openness_matrix"
DIMENSIONS = [
    ("inference_code", "inference\ncode"),
    ("training_code", "training\ncode"),
    ("weights", "weights"),
    ("architecture", "architecture"),
    ("data_recipe", "data\nrecipe"),
    ("training_data", "training\ndata"),
    ("evaluation_code", "evaluation\ncode"),
]
HATCH_BY_STATE = {"unverified": "//", "not_available": "xx", "not_applicable": "\\\\"}
BIN_EDGES = [0.0, 0.25, 0.5, 0.75, 1.0]
BIN_LABELS = ["none", "up to 25%", "up to 50%", "up to 75%", "all"]


def caption(record_count: int) -> str:
    """The caption fragment, with its numbers taken from the file that was read."""
    return (
        f"Openness by record kind and by the seven openness dimensions, over {record_count} "
        "catalogue records. The fill is the share of a kind's records for which a dimension is "
        "available, counted over the records for which it applies, and the hatch says why the rest "
        "is not available, unverified, recorded as not available, or not applicable to that kind. "
        "Openness is recorded per dimension and is never collapsed here into a single open or "
        "closed label."
    )


def _bin_index(proportion: float) -> int:
    for index, edge in enumerate(BIN_EDGES[1:], start=1):
        if proportion <= edge:
            return index
    return len(BIN_EDGES) - 1


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    ladder = style.ladder_colours("light")

    openness = style.load_json(style.DATA_DIR / "openness.v1.json")
    resources = style.load_json(style.DATA_DIR / "resources.v1.json")
    kind_of = {record["id"]: record["kind"] for record in resources}

    kind_counts = Counter(kind_of.values())
    kinds = [kind for kind, _ in sorted(kind_counts.items(), key=lambda item: (-item[1], item[0]))]

    fig = style.figure(style.FIGURE_WIDTH, 5.9)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.135, right=0.985, bottom=0.255, top=0.915)

    for row, kind in enumerate(kinds):
        records = [item for item in openness if kind_of[item["id"]] == kind]
        for column, (dimension, _) in enumerate(DIMENSIONS):
            states = Counter(item["openness"][dimension]["value"] for item in records)
            applicable = states["available"] + states["not_available"] + states["unverified"]
            proportion = states["available"] / applicable if applicable else 0.0
            index = _bin_index(proportion)
            if (
                states["not_applicable"] > states["unverified"]
                and states["not_applicable"] > states["not_available"]
            ):
                hatch = HATCH_BY_STATE["not_applicable"]
            elif states["not_available"] > states["unverified"]:
                hatch = HATCH_BY_STATE["not_available"]
            else:
                hatch = ""
            ax.add_patch(
                Rectangle(
                    (column, row),
                    1,
                    1,
                    facecolor=ladder[index],
                    edgecolor=tokens["ink"],
                    linewidth=0.6,
                    hatch=hatch,
                )
            )
            ax.text(
                column + 0.5,
                row + 0.5,
                f"{states['available']}/{applicable}",
                ha="center",
                va="center",
                fontsize=6.4,
                color=tokens["panel"] if index >= 3 else tokens["ink"],
            )

    ax.set_xlim(0, len(DIMENSIONS))
    ax.set_ylim(len(kinds), 0)
    ax.set_xticks([column + 0.5 for column in range(len(DIMENSIONS))])
    ax.set_xticklabels([label for _, label in DIMENSIONS], fontsize=7.4)
    ax.set_yticks([row + 0.5 for row in range(len(kinds))])
    ax.set_yticklabels(
        [f"{kind.replace('-', ' ')}  ({kind_counts[kind]})" for kind in kinds], fontsize=7.8
    )
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    style.title(ax, "Openness by record kind")

    ramp_handles = [
        Rectangle((0, 0), 1, 1, facecolor=colour, edgecolor=tokens["ink"], linewidth=0.6)
        for colour in ladder
    ]
    ramp = fig.legend(
        ramp_handles,
        BIN_LABELS,
        loc="lower left",
        ncol=5,
        fontsize=7.6,
        handlelength=1.5,
        handleheight=1.0,
        columnspacing=1.2,
        frameon=False,
        title="Share of the applicable records with the dimension available",
        title_fontsize=7.6,
        bbox_to_anchor=(0.135, 0.005),
    )
    ramp.set_in_layout(False)

    hatch_handles = [
        Rectangle(
            (0, 0),
            1,
            1,
            facecolor=ladder[0],
            edgecolor=tokens["ink"],
            linewidth=0.6,
            hatch=pattern,
        )
        for pattern in ("", HATCH_BY_STATE["not_available"], HATCH_BY_STATE["not_applicable"])
    ]
    hatch_legend = fig.legend(
        hatch_handles,
        ["unverified", "not available", "not applicable"],
        loc="lower right",
        ncol=1,
        fontsize=7.6,
        handlelength=1.5,
        handleheight=1.0,
        frameon=False,
        title="The rest of the cell",
        title_fontsize=7.6,
        bbox_to_anchor=(0.99, 0.005),
    )
    hatch_legend.set_in_layout(False)

    written = style.save(fig, STEM)
    style.register_caption(FIGURE_NUMBER, caption(len(openness)))
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
