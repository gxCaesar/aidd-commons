"""FreeSolv split and calibration.

Source of every number: `labs/freesolv/reviewed-results.json`, the reviewed
aggregate of a completed lab run. It holds the counts of both splits, the
point metrics of two fixed teaching baselines and of the training-set mean, and
the interval metrics of the two models that carry intervals.

What the figure shows. The scaffold split is the predeclared primary result
and the random split is the easier contrast, so the scaffold split is drawn
first in every panel. In each panel the training-set mean comes first, because
it is the cheap baseline and a baseline that is not shown first is a baseline
that gets read as a comparison. The last two panels are the interval metrics:
the empirical marginal coverage of the intervals and their mean width. The
training-set mean carries no interval, so it has no bar in those two panels.

What it does not show. The coverage is marginal coverage over the test set,
not conditional coverage, so a model can hold its marginal coverage and still
be badly calibrated on the part of the space a reader cares about. The
intervals are the intervals this lab built, and their nominal level is not
stated in the reviewed results, so no reference line for a nominal level is
drawn here; inventing one would be a number that no file supports. These
fixed teaching baselines do not establish a state of the art, and they say
nothing about prospective drug-discovery utility.
"""

from __future__ import annotations

import sys
from pathlib import Path

from matplotlib.patches import Rectangle

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 8
STEM = "plot_8_freesolv_split_calibration"
SPLITS = ["scaffold", "random"]
SPLIT_TITLE = {"scaffold": "Scaffold split (primary)", "random": "Random split (contrast)"}
SERIES = [
    ("train_mean", "Train-set mean", "slate"),
    ("morgan_ridge", "Morgan ridge", "teal"),
    ("morgan_random_forest", "Morgan random forest", "coral"),
]
GROUP_GAP = 0.8

CAPTION = (
    "FreeSolv point and interval metrics for two fixed teaching baselines, on the predeclared "
    "scaffold split and the easier random split. {point}. {interval}. The coverage is marginal "
    "coverage and not conditional calibration, the nominal level of the intervals is not stated in "
    "the reviewed results, and these teaching baselines establish no state of the art."
)


def _group_centre(split_index: int) -> float:
    """The x position of the middle of a split group."""
    return split_index * (len(SERIES) + GROUP_GAP) + (len(SERIES) - 1) / 2


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    hatches = style.atlas_palette.HATCH

    results = style.load_json(style.REPO_ROOT / "labs" / "freesolv" / "reviewed-results.json")
    splits = results["splits"]

    fig = style.figure(style.FIGURE_WIDTH, 5.6)
    axes = style.axes_grid(
        fig,
        2,
        2,
        left=0.085,
        right=0.985,
        bottom=0.145,
        top=0.905,
        wspace=0.24,
        hspace=0.62,
    )
    mae_ax, rmse_ax, coverage_ax, width_ax = axes

    def draw(ax, source: str, metric: str, unit: str, title: str, fmt: str) -> None:
        positions: list[float] = []
        values: list[float] = []
        bar_colours: list[str] = []
        bar_hatches: list[str] = []
        missing: list[tuple[float, str]] = []
        missing_flags: list[bool] = []
        position = 0.0
        for split in SPLITS:
            for key, _, colour_key in SERIES:
                positions.append(position)
                if source == "point_metrics":
                    values.append(splits[split][source][key][metric])
                    missing_flags.append(False)
                elif key == "train_mean":
                    values.append(0.0)
                    missing_flags.append(True)
                    missing.append((position, "no interval"))
                else:
                    values.append(splits[split]["interval_metrics"][key][metric])
                    missing_flags.append(False)
                bar_colours.append(colours[colour_key])
                bar_hatches.append(hatches[colour_key])
                position += 1.0
            position += GROUP_GAP

        container = ax.bar(
            positions,
            values,
            width=0.84,
            color=bar_colours,
            edgecolor=tokens["ink"],
            linewidth=0.5,
            zorder=3,
        )
        for bar, hatch in zip(container, bar_hatches, strict=True):
            bar.set_hatch(hatch)
        for bar, value, is_missing in zip(container, values, missing_flags, strict=True):
            if is_missing:
                continue
            style.bar_labels(ax, [bar], [value], fmt=fmt, pad=2, fontsize=6.2)

        ax.set_xticks(positions)
        ax.set_xticklabels([""] * len(positions))
        ax.tick_params(axis="x", length=0)
        for split_index, split in enumerate(SPLITS):
            ax.annotate(
                SPLIT_TITLE[split],
                xy=(_group_centre(split_index), 0),
                xytext=(0, -30),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=8.0,
                color=tokens["ink"],
            )
        for x, note in missing:
            ax.annotate(
                note,
                xy=(x, 0),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=6.0,
                color=tokens["muted"],
                rotation=90,
            )
        ax.set_ylabel(unit, fontsize=8.5)
        ax.grid(axis="y", linewidth=0.6, alpha=0.7)
        ax.set_axisbelow(True)
        style.title(ax, title)

    draw(
        mae_ax,
        "point_metrics",
        "mae",
        "Mean absolute error (kcal/mol)",
        "Mean absolute error",
        "{:.2f}",
    )
    draw(
        rmse_ax,
        "point_metrics",
        "rmse",
        "Root mean squared error (kcal/mol)",
        "Root mean squared error",
        "{:.2f}",
    )
    draw(
        coverage_ax,
        "interval_metrics",
        "coverage",
        "Empirical marginal coverage",
        "Interval coverage",
        "{:.3f}",
    )
    draw(
        width_ax,
        "interval_metrics",
        "mean_width",
        "Mean interval width (kcal/mol)",
        "Interval width",
        "{:.2f}",
    )

    handles = [
        Rectangle(
            (0, 0),
            1,
            1,
            facecolor=colours[colour_key],
            edgecolor=tokens["ink"],
            linewidth=0.5,
            hatch=hatches[colour_key],
        )
        for _, _, colour_key in SERIES
    ]
    figure_legend = fig.legend(
        handles,
        [label for _, label, _ in SERIES],
        loc="lower center",
        ncol=3,
        fontsize=8.2,
        handlelength=1.5,
        handleheight=1.0,
        columnspacing=1.8,
        frameon=False,
        bbox_to_anchor=(0.5, 0.004),
    )
    figure_legend.set_in_layout(False)

    point = (
        f"The ridge reaches "
        f"{splits['scaffold']['point_metrics']['morgan_ridge']['mae']:.2f} kcal/mol mean "
        f"absolute error on the scaffold split against "
        f"{splits['scaffold']['point_metrics']['train_mean']['mae']:.2f} for the training-set "
        f"mean, "
        f"and {splits['random']['point_metrics']['morgan_ridge']['mae']:.2f} against "
        f"{splits['random']['point_metrics']['train_mean']['mae']:.2f} on the random split"
    )
    interval = (
        f"On the scaffold split the intervals reach an empirical coverage of "
        f"{splits['scaffold']['interval_metrics']['morgan_ridge']['coverage']:.3f} for the "
        f"ridge and "
        f"{splits['scaffold']['interval_metrics']['morgan_random_forest']['coverage']:.5f} for "
        f"the forest, at mean widths of "
        f"{splits['scaffold']['interval_metrics']['morgan_ridge']['mean_width']:.2f} and "
        f"{splits['scaffold']['interval_metrics']['morgan_random_forest']['mean_width']:.2f} "
        f"kcal/mol"
    )
    written = style.save(fig, STEM)
    style.register_caption(FIGURE_NUMBER, CAPTION.format(point=point, interval=interval))
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
