"""Current self record against retained automated readings.

Source of every number: the current `second_readings` aggregate in
`site/public/data/comparison.v1.json`. The retained per-topic readings belong
to a series initiated on the record's `reviewed_on` date, with later batches
documented in its reviewer description. The projection's `as_of` date names
the current aggregate, not the date of a single reading.

What the figure shows. The upper panel counts the per-topic outcome of the
retained readings against the current self record: how many topic scores agree,
how many read deeper, and how many read shallower. The lower panel
puts the two counts side by side at each threshold, so the reader can see which
thresholds the disagreement sits at and how large it is.

What it does not show. The reading is not an independent replication of the
material, because the reviewer had also written parts of the course. It is a
second reading by a different model family, which is a weaker instrument than a
blind replication and is reported as such. No topic was read shallower, and the
audit's validator refuses to publish a record in which one is, so that number is
a constraint on the record rather than an observation about the material. The
retained scores include successive re-readings after material changed, so their
agreement with an updated self record is not the original pass's outcome.
"""

from __future__ import annotations

import sys
from pathlib import Path

from matplotlib.ticker import MaxNLocator

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)
from figure_sources import reading_series, validate_count_bounds  # noqa: E402

FIGURE_NUMBER = 5
STEM = "plot_5_self_record_vs_reading"
READING_ID = "aidd-commons-blind-2026-09-11"

OUTCOME_COLOUR = {"equal": "slate", "reading_deeper": "coral", "reading_shallower": "ember"}
THRESHOLD_TITLES = {
    "explained": "Explained",
    "worked": "Worked",
    "executable": "Executable",
    "executable-on-real-data": "Executable on real data",
    "assessed": "Assessed",
}

CAPTION = (
    "The current self record against the retained automated readings of {cells} topics in the "
    "comparison.v1 projection dated {as_of}. The series began on {reviewed}, and its description "
    "documents re-readings through {documented_through}. These totals aggregate the latest "
    "retained topic scores rather than a single pass. The current aggregate agrees on {equal} "
    "topics, reads {deeper} deeper and {shallower} shallower. At the thresholds "
    "the retained readings give {reading} against the current record's {recorded}. "
    "The reviewer also authored parts of the "
    "course, so this is not an independent replication or evidence of reader learning. The "
    "shallower count is constrained by the audit's rule against inflated self scores."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    hatches = style.atlas_palette.HATCH

    payload = style.load_json(style.DATA_DIR / "comparison.v1.json")
    reading = next(item for item in payload["second_readings"] if item["id"] == READING_ID)
    series = reading_series(payload, reading)

    fig = style.figure(style.FIGURE_WIDTH, 5.0)
    axes = style.axes_grid(
        fig,
        2,
        1,
        left=0.205,
        right=0.985,
        bottom=0.085,
        top=0.935,
        hspace=0.50,
        height_ratios=[0.72, 1.4],
    )
    outcome_ax, threshold_ax = axes

    outcomes = [
        ("Equal", reading["equal"]),
        ("Reading deeper", reading["reading_deeper"]),
        ("Reading shallower", reading["reading_shallower"]),
    ]
    positions = list(range(len(outcomes)))[::-1]
    keys = ["equal", "reading_deeper", "reading_shallower"]
    values = [count for _, count in outcomes]
    container = outcome_ax.barh(
        positions,
        values,
        height=0.55,
        color=[colours[OUTCOME_COLOUR[key]] for key in keys],
        edgecolor=tokens["ink"],
        linewidth=0.6,
        zorder=3,
    )
    for bar, key in zip(container, keys, strict=True):
        bar.set_hatch(hatches[OUTCOME_COLOUR[key]])

    outcome_ax.set_yticks(positions)
    outcome_ax.set_yticklabels([label for label, _ in outcomes], fontsize=8.4)
    outcome_ax.tick_params(axis="y", length=0)
    outcome_ax.set_xlabel(f"Topics out of {series.topics}", fontsize=8.5)
    outcome_ax.set_xlim(0, series.topics * 1.14)
    outcome_ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    outcome_ax.set_ylim(-0.6, len(outcomes) - 0.4)
    outcome_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    outcome_ax.set_axisbelow(True)
    style.title(outcome_ax, "Per-topic outcome")
    style.bar_labels(outcome_ax, container, values, orientation="horizontal", pad=4, fontsize=8.0)

    rows = list(reading["thresholds"])
    row_positions = list(range(len(rows)))[::-1]
    for entry, position in zip(rows, row_positions, strict=True):
        recorded = entry["recorded"]
        observed = entry["reading"]
        threshold_ax.plot(
            [recorded, observed],
            [position, position],
            color=tokens["rule"],
            linewidth=1.4,
            zorder=2,
        )
        threshold_ax.plot(
            observed,
            position,
            marker="s",
            markersize=6.0,
            markerfacecolor="none",
            markeredgecolor=colours["coral"],
            markeredgewidth=1.3,
            linestyle="none",
            zorder=3,
        )
        threshold_ax.plot(
            recorded,
            position,
            marker="o",
            markersize=6.0,
            markerfacecolor=colours["teal"],
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.5,
            linestyle="none",
            zorder=4,
        )
        gap = observed - recorded
        threshold_ax.annotate(
            f"+{gap}" if gap else "same",
            xy=((recorded + observed) / 2, position),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.8,
            color=tokens["ink"],
        )

    threshold_ax.set_yticks(row_positions)
    threshold_ax.set_yticklabels(
        [THRESHOLD_TITLES[entry["threshold"]] for entry in rows], fontsize=8.4
    )
    threshold_ax.tick_params(axis="y", length=0)
    threshold_ax.set_xlabel(f"Topics out of {series.topics}", fontsize=8.5)
    threshold_ax.set_xlim(-0.03 * series.topics, series.topics * 1.14)
    threshold_ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    threshold_ax.set_ylim(-0.7, len(rows) - 0.3)
    threshold_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    threshold_ax.set_axisbelow(True)
    style.title(threshold_ax, "Recorded count against the reading")

    handles = [
        _handle(colours["teal"], "o", filled=True),
        _handle(colours["coral"], "s", filled=False),
    ]
    threshold_ax.legend(
        handles,
        ["Current self record", "Retained topic readings"],
        loc="upper left",
        fontsize=8.0,
        handletextpad=0.5,
        borderpad=0.3,
        frameon=False,
        ncol=2,
        columnspacing=1.4,
        bbox_to_anchor=(0.0, 1.02),
    )

    validate_count_bounds(values, outcome_ax.get_xlim())
    validate_count_bounds(
        [entry[key] for entry in rows for key in ("recorded", "reading")],
        threshold_ax.get_xlim(),
    )
    written = style.save(fig, STEM)
    style.register_caption(
        FIGURE_NUMBER,
        CAPTION.format(
            cells=reading["cells"],
            reviewed=series.initiated_on,
            as_of=series.aggregate_as_of,
            documented_through=series.documented_through,
            equal=reading["equal"],
            deeper=reading["reading_deeper"],
            shallower=reading["reading_shallower"],
            reading=style.english_list(
                f"{entry['reading']} {THRESHOLD_TITLES[entry['threshold']].lower()}"
                for entry in reading["thresholds"]
            ),
            recorded=style.english_list(
                f"{entry['recorded']} {THRESHOLD_TITLES[entry['threshold']].lower()}"
                for entry in reading["thresholds"]
            ),
        ),
    )
    return written


def _handle(colour: str, marker: str, *, filled: bool):
    """A legend handle in the shape of a point mark."""
    from matplotlib.lines import Line2D

    return Line2D(
        [0],
        [0],
        linestyle="none",
        marker=marker,
        markersize=6.0,
        markerfacecolor=colour if filled else "none",
        markeredgecolor=colour if not filled else style.tokens("light")["ink"],
        markeredgewidth=1.3 if not filled else 0.5,
    )


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
