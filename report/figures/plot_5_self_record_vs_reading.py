"""Self record against the independent reading.

Source of every number: `site/public/data/comparison.v1.json`, the frozen
comparison audit, and only its `second_readings` entry. That entry holds one
blind reading of this project's own 93 topics by a reviewer from a different
model family, the per-topic outcome counts, and the per-threshold counts the
reading gave against the counts this project recorded.

What the figure shows. The left panel counts the per-topic outcome of the
blind reading: how many topics the reading agreed with, how many it read deeper
than this project recorded, and how many it read shallower. The right panel
puts the two counts side by side at each threshold, so the reader can see which
thresholds the disagreement sits at and how large it is.

What it does not show. The reading is not an independent replication of the
material, because the reviewer had also written parts of the course. It is a
second reading by a different model family, which is a weaker instrument than a
blind replication and is reported as such. No topic was read shallower, and the
audit's validator refuses to publish a record in which one is, so that number is
a constraint on the record rather than an observation about the material. The
reading also re-read seven topics whose material changed after the first pass
and four more after later material landed, which is why the reading is a
successive instrument rather than one pass.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 5
STEM = "plot_5_self_record_vs_reading"
TOTAL_TOPICS = 93

OUTCOME_COLOUR = {"equal": "slate", "reading_deeper": "coral", "reading_shallower": "ember"}
THRESHOLD_TITLES = {
    "explained": "Explained",
    "worked": "Worked",
    "executable": "Executable",
    "executable-on-real-data": "Executable on real data",
    "assessed": "Assessed",
}

CAPTION = (
    "This project's own record against a blind second reading of the same {cells} topics by a "
    "reviewer from a different model family on {reviewed}. The reading agreed with the record on "
    "{equal} topics, read {deeper} deeper and {shallower} shallower. At the thresholds the reading "
    "gave {reading} against the recorded {recorded}. The reviewer had also written parts of the "
    "course, so this is a second reading and not a blind replication."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    hatches = style.atlas_palette.HATCH

    payload = style.load_json(style.DATA_DIR / "comparison.v1.json")
    reading = payload["second_readings"][0]

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
    outcome_ax.set_xlabel("Topics out of 93", fontsize=8.5)
    outcome_ax.set_xlim(0, 66)
    outcome_ax.set_xticks([0, 20, 40, 60])
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
    threshold_ax.set_xlabel("Topics out of 93", fontsize=8.5)
    threshold_ax.set_xlim(-3, 100)
    threshold_ax.set_xticks([0, 30, 60, 90])
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
        ["Recorded by this project", "Independent reading"],
        loc="upper left",
        fontsize=8.0,
        handletextpad=0.5,
        borderpad=0.3,
        frameon=False,
        ncol=2,
        columnspacing=1.4,
        bbox_to_anchor=(0.0, 1.02),
    )

    written = style.save(fig, STEM)
    style.register_caption(
        FIGURE_NUMBER,
        CAPTION.format(
            cells=reading["cells"],
            reviewed=reading["reviewed_on"],
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
