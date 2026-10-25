"""Acquisition policy recovery.

Source of every number: `labs/pool_budget/real-summary.json`, the reviewed
summary of the completed acquisition campaign, and
`labs/pool_budget/uncertainty-summary.json`, the reviewed summary of the
uncertainty campaign that followed it. Both hold two retrospective assay
replays, the acquisition checkpoints, and for every policy the fraction of the
top-decile actives recovered, the scaffold fraction reached and the evaluation
mean absolute error.

What the figure shows. The left column of each row plots recovery against the
number of compounds acquired, and the right column plots the evaluation error
at the same checkpoints, for the two named policies and for the five random
policy instances. The two named policies are the ones the campaign is about,
so they are drawn in the categorical colours; the five random instances are a
family, drawn in one colour with a distinct marker each, because they are five
fixed seeds of the same policy and not five different methods.

What it does not show. These are retrospective replays of two assays, not
prospective experiments, so nothing here is a claim about discovery. The five
random seeds are fixed policy instances and not independent biological
replicates. The ridge penalty was informed by the earlier development work on
the same contract, so this run is not an independent corroboration of it, and
the acquisition lab had already accessed labels shared with that earlier
evaluation. No confidence intervals, no p values and no pooled inferential
comparisons are reported, and none is drawn here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 10
STEM = "plot_10_acquisition_policy_recovery"
ASSAYS = ["CHEMBL5736995", "CHEMBL3705421"]
RANDOM_MARKERS = ["o", "s", "^", "D", "v"]
NAMED = {
    "maxmin": ("teal", "o", "-"),
    "ensemble-variance-uncertainty": ("coral", "s", "--"),
}

CAPTION = (
    "Acquisition policies on two retrospective assay replays, {summary}. The two named policies "
    "are drawn in colour and the five random policy instances in one colour with a distinct marker "
    "each, because they are five fixed seeds of one policy rather than five methods. These are "
    "retrospective replays and not prospective experiments, the random seeds are not independent "
    "replicates, and no confidence intervals or p values are reported."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")

    real = style.load_json(style.REPO_ROOT / "labs" / "pool_budget" / "real-summary.json")
    uncertainty = style.load_json(
        style.REPO_ROOT / "labs" / "pool_budget" / "uncertainty-summary.json"
    )

    fig = style.figure(style.FIGURE_WIDTH, 6.0)
    axes = style.axes_grid(
        fig,
        2,
        2,
        left=0.075,
        right=0.985,
        bottom=0.145,
        top=0.905,
        wspace=0.24,
        hspace=0.46,
    )

    summary_parts = []
    for index, assay in enumerate(ASSAYS):
        recovery_ax, mae_ax = axes[2 * index], axes[2 * index + 1]
        checkpoints = real["assays"][assay]["budget"]["checkpoints"]
        policies = {policy["name"]: policy for policy in real["assays"][assay]["policies"]}
        policies["ensemble-variance-uncertainty"] = uncertainty["assays"][assay]["policy"]

        for name in ["maxmin", "ensemble-variance-uncertainty"]:
            colour_key, marker, dash = NAMED[name]
            policy = policies[name]
            recovery_ax.plot(
                checkpoints,
                policy["recovery"],
                color=colours[colour_key],
                marker=marker,
                markersize=5.0,
                markerfacecolor=colours[colour_key],
                markeredgecolor=tokens["ink"],
                markeredgewidth=0.4,
                linewidth=1.8,
                linestyle=dash,
                zorder=4,
            )
            mae_ax.plot(
                checkpoints,
                policy["evaluation_mae"],
                color=colours[colour_key],
                marker=marker,
                markersize=5.0,
                markerfacecolor=colours[colour_key],
                markeredgecolor=tokens["ink"],
                markeredgewidth=0.4,
                linewidth=1.8,
                linestyle=dash,
                zorder=4,
            )

        for seed_index, name in enumerate(
            sorted(name for name in policies if name.startswith("random"))
        ):
            policy = policies[name]
            recovery_ax.plot(
                checkpoints,
                policy["recovery"],
                color=colours["slate"],
                marker=RANDOM_MARKERS[seed_index],
                markersize=4.2,
                markerfacecolor="none",
                markeredgecolor=colours["slate"],
                markeredgewidth=1.0,
                linewidth=1.0,
                linestyle=(0, (2, 2)),
                zorder=3,
            )
            mae_ax.plot(
                checkpoints,
                policy["evaluation_mae"],
                color=colours["slate"],
                marker=RANDOM_MARKERS[seed_index],
                markersize=4.2,
                markerfacecolor="none",
                markeredgecolor=colours["slate"],
                markeredgewidth=1.0,
                linewidth=1.0,
                linestyle=(0, (2, 2)),
                zorder=3,
            )

        budget = real["assays"][assay]["budget"]
        recovery_ax.set_ylabel("Top-decile actives recovered", fontsize=8.5)
        recovery_ax.set_xlabel("Compounds acquired", fontsize=8.5)
        recovery_ax.set_xticks(checkpoints)
        recovery_ax.set_ylim(0, 0.27)
        recovery_ax.grid(axis="y", linewidth=0.6, alpha=0.7)
        recovery_ax.set_axisbelow(True)
        style.title(recovery_ax, f"{assay} recovery")

        mae_ax.set_ylabel("Evaluation MAE", fontsize=8.5)
        mae_ax.set_xlabel("Compounds acquired", fontsize=8.5)
        mae_ax.set_xticks(checkpoints)
        mae_ax.grid(axis="y", linewidth=0.6, alpha=0.7)
        mae_ax.set_axisbelow(True)
        style.title(mae_ax, f"{assay} evaluation error")

        maxmin = policies["maxmin"]
        ensemble = policies["ensemble-variance-uncertainty"]
        summary_parts.append(
            f"on {assay}, {budget['acquired_count']} compounds were acquired against a pool of "
            f"{budget['original_pool_parent_count']}, and the diversity policy recovered "
            f"{maxmin['normalized_auc']:.4f} of the top decile against "
            f"{ensemble['normalized_auc']:.4f} for the ensemble-variance policy"
        )

    handles = [
        _handle(colours["teal"], "o", "-"),
        _handle(colours["coral"], "s", "--"),
    ]
    labels = ["Maxmin diversity", "Ensemble variance"]
    for seed_index, name in enumerate(["random-0", "random-1", "random-2", "random-3", "random-4"]):
        handles.append(_handle(colours["slate"], RANDOM_MARKERS[seed_index], (0, (2, 2))))
        labels.append(name)
    figure_legend = fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        fontsize=8.0,
        handletextpad=0.5,
        columnspacing=1.6,
        frameon=False,
        bbox_to_anchor=(0.5, 0.004),
    )
    figure_legend.set_in_layout(False)

    written = style.save(fig, STEM)
    style.register_caption(FIGURE_NUMBER, CAPTION.format(summary=style.english_list(summary_parts)))
    return written


def _handle(colour: str, marker: str, dash: object):
    """A legend handle in the shape of a line mark."""
    from matplotlib.lines import Line2D

    return Line2D(
        [0],
        [0],
        color=colour,
        marker=marker,
        markersize=4.6,
        markerfacecolor=colour,
        markeredgecolor=colour,
        markeredgewidth=1.0,
        linewidth=1.6,
        linestyle=dash,
    )


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
