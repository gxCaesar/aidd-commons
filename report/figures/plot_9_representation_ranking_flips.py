"""Representation ranking flips.

Source of every number: `labs/chembl_egfr/locked-summary.json`, the reviewed
summary of a completed locked evaluation on the frozen ChEMBL 37 EGFR
contract. It holds the selected penalties, the point metrics of three
baselines on the primary test partition and on the separate assay replication,
and the Spearman correlation of each, including the case where the
correlation is undefined.

What the figure shows. The same three baselines are evaluated twice, on the
primary partition of 132 compounds and on a separate assay replication of 170
compounds, and the ranking is not the same on both. The left panel is a slope
graph of the mean absolute error on a log axis, so the reader can see the two
orderings and the gap between them. The right panel is the rank correlation of
each baseline on each partition, where the ranking correlation of the Morgan
ridge turns negative on the replication.

The flip is the point of the figure, so it is not hidden. The baseline that
wins the primary partition loses the replication by a wide margin, and both
halves of that are drawn.

What it does not show. The two evaluations are separate comparisons and
success on one does not erase failure on the other. The locked summary records
that the acquisition lab had already accessed labels shared with this
evaluation before it ran, so it is not an entirely untouched independent
confirmatory evaluation, and that the frozen split, the alpha grid and the
selected penalties were not retuned after that exposure. The descriptor
penalty sits at the upper edge of the frozen grid. No confidence intervals, no
p values and no pooled superiority claim are reported, and none is drawn here.
"""

from __future__ import annotations

import sys
from pathlib import Path

from matplotlib.ticker import NullFormatter

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 9
STEM = "plot_9_representation_ranking_flips"
SERIES = [
    ("train_mean", "Train-set mean", "slate", "o"),
    ("descriptor_ridge", "Descriptor ridge", "coral", "s"),
    ("morgan_ridge", "Morgan ridge", "teal", "^"),
]
PARTITIONS = ["primary_test", "assay_replication"]
PARTITION_TITLE = {
    "primary_test": "Primary partition, 132 compounds",
    "assay_replication": "Assay replication, 170 compounds",
}

CAPTION = (
    "The same three baselines on the primary partition of 132 compounds and on the separate assay "
    "replication of 170 compounds. {flip}. The two evaluations are separate comparisons and "
    "success on one does not erase failure on the other, the acquisition lab had accessed labels "
    "shared with this evaluation before it ran, and no confidence intervals or p values are "
    "reported."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    dashes = style.dashes("light")

    summary = style.load_json(style.REPO_ROOT / "labs" / "chembl_egfr" / "locked-summary.json")
    results = summary["results"]

    fig = style.figure(style.FIGURE_WIDTH, 4.6)
    axes = style.axes_grid(
        fig,
        1,
        2,
        left=0.075,
        right=0.985,
        bottom=0.155,
        top=0.885,
        wspace=0.26,
        width_ratios=[1.05, 1.0],
    )
    slope_ax, rho_ax = axes

    primary_order = sorted(
        SERIES, key=lambda item: results["primary_test"]["metrics"][item[0]]["mae"]
    )
    primary_offsets = {
        key: offset
        for key, offset in zip(
            [item[0] for item in primary_order],
            [-13, 0, 13],
            strict=True,
        )
    }
    for key, _label, colour_key, marker in SERIES:
        primary = results["primary_test"]["metrics"][key]
        replication = results["assay_replication"]["metrics"][key]
        slope_ax.plot(
            [0, 1],
            [primary["mae"], replication["mae"]],
            color=colours[colour_key],
            marker=marker,
            markersize=6.5,
            markerfacecolor=colours[colour_key],
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.5,
            linewidth=1.8,
            linestyle=dashes[colour_key],
            zorder=3,
        )
        slope_ax.annotate(
            f"{primary['mae']:.2f}",
            xy=(0, primary["mae"]),
            xytext=(-10, primary_offsets[key]),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=7.6,
            color=tokens["ink"],
        )
        slope_ax.annotate(
            f"{replication['mae']:.2f}",
            xy=(1, replication["mae"]),
            xytext=(10, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=7.6,
            color=tokens["ink"],
        )

    slope_ax.set_xlim(-0.42, 1.42)
    slope_ax.set_yscale("log")
    slope_ax.set_yticks([0.4, 0.5, 0.7, 1.0, 2.0, 3.0])
    slope_ax.set_yticklabels(["0.4", "0.5", "0.7", "1.0", "2.0", "3.0"])
    slope_ax.yaxis.set_minor_formatter(NullFormatter())
    slope_ax.set_xticks([0, 1])
    slope_ax.set_xticklabels(
        ["Primary partition\n132 compounds", "Assay replication\n170 compounds"], fontsize=7.8
    )
    slope_ax.set_ylabel("Mean absolute error (log scale)", fontsize=8.5)
    slope_ax.grid(axis="y", linewidth=0.6, alpha=0.7)
    slope_ax.set_axisbelow(True)
    style.title(slope_ax, "Mean absolute error on both evaluations")
    slope_handles = [
        _line_handle(colours[colour_key], marker, dashes[colour_key])
        for _, _, colour_key, marker in SERIES
    ]
    slope_ax.legend(
        slope_handles,
        [label for _, label, _, _ in SERIES],
        loc="upper left",
        fontsize=7.6,
        handletextpad=0.4,
        borderpad=0.3,
        frameon=False,
    )

    replication_order = sorted(
        SERIES, key=lambda item: results["assay_replication"]["metrics"][item[0]]["mae"]
    )
    slope_ax.annotate(
        "best on this partition",
        xy=(1, results["assay_replication"]["metrics"][replication_order[0][0]]["mae"]),
        xytext=(12, 18),
        textcoords="offset points",
        ha="left",
        fontsize=7.4,
        color=tokens["muted"],
    )

    rows = list(range(len(SERIES)))[::-1]
    for row, (key, _label, colour_key, _) in zip(rows, SERIES, strict=True):
        primary = results["primary_test"]["metrics"][key]["spearman"]
        replication = results["assay_replication"]["metrics"][key]["spearman"]
        if primary is None or replication is None:
            rho_ax.annotate(
                "undefined, constant prediction",
                xy=(0.0, row),
                xytext=(8, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=7.2,
                color=tokens["muted"],
            )
            continue
        rho_ax.plot(
            [primary, replication],
            [row, row],
            color=tokens["rule"],
            linewidth=1.4,
            zorder=2,
        )
        rho_ax.plot(
            primary,
            row,
            marker="o",
            markersize=6.5,
            markerfacecolor=colours[colour_key],
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.5,
            linestyle="none",
            zorder=3,
        )
        rho_ax.plot(
            replication,
            row,
            marker="o",
            markersize=6.5,
            markerfacecolor="none",
            markeredgecolor=colours[colour_key],
            markeredgewidth=1.5,
            linestyle="none",
            zorder=4,
        )
        rho_ax.annotate(
            f"{primary:.3f}",
            xy=(primary, row),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=7.0,
            color=tokens["ink"],
        )
        rho_ax.annotate(
            f"{replication:.3f}",
            xy=(replication, row),
            xytext=(0, -13),
            textcoords="offset points",
            ha="center",
            fontsize=7.0,
            color=tokens["ink"],
        )

    rho_ax.axvline(0, color=tokens["ink"], linewidth=0.8, zorder=2)
    rho_ax.set_xlim(-0.12, 0.62)
    rho_ax.set_ylim(-0.6, len(SERIES) - 0.4)
    rho_ax.set_yticks(rows)
    rho_ax.set_yticklabels([label for _, label, _, _ in SERIES], fontsize=8.4)
    rho_ax.tick_params(axis="y", length=0)
    rho_ax.set_xlabel("Spearman rank correlation", fontsize=8.5)
    rho_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    rho_ax.set_axisbelow(True)
    style.title(rho_ax, "Rank correlation on both evaluations")

    handles = [
        _handle(tokens["ink"], "o", filled=True),
        _handle(tokens["ink"], "o", filled=False),
    ]
    rho_ax.legend(
        handles,
        ["Primary partition", "Assay replication"],
        loc="lower left",
        fontsize=8.0,
        handletextpad=0.4,
        borderpad=0.3,
        frameon=False,
        ncol=2,
        columnspacing=1.4,
    )

    flip = (
        f"The Morgan ridge is the best of the three on the primary partition at "
        f"{results['primary_test']['metrics']['morgan_ridge']['mae']:.3f} mean absolute error, "
        f"while the descriptor ridge is the best on the replication at "
        f"{results['assay_replication']['metrics']['descriptor_ridge']['mae']:.3f}; the Morgan "
        f"ridge reaches "
        f"{results['assay_replication']['metrics']['morgan_ridge']['mae']:.3f} there and "
        f"its rank correlation falls from "
        f"{results['primary_test']['metrics']['morgan_ridge']['spearman']:.3f} to "
        f"{results['assay_replication']['metrics']['morgan_ridge']['spearman']:.3f}"
    )
    written = style.save(fig, STEM)
    style.register_caption(FIGURE_NUMBER, CAPTION.format(flip=flip))
    return written


def _line_handle(colour: str, marker: str, dash: object):
    """A legend handle in the shape of a line mark."""
    from matplotlib.lines import Line2D

    return Line2D(
        [0],
        [0],
        color=colour,
        marker=marker,
        markersize=6.0,
        markerfacecolor=colour,
        markeredgecolor=style.tokens("light")["ink"],
        markeredgewidth=0.5,
        linewidth=1.8,
        linestyle=dash,
    )


def _handle(colour: str, marker: str, *, filled: bool):
    """A legend handle in the shape of a point mark."""
    from matplotlib.lines import Line2D

    return Line2D(
        [0],
        [0],
        linestyle="none",
        marker=marker,
        markersize=6.2,
        markerfacecolor=colour if filled else "none",
        markeredgecolor=colour if not filled else style.tokens("light")["ink"],
        markeredgewidth=1.5 if not filled else 0.5,
    )


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
