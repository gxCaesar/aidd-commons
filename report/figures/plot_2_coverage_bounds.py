"""Coverage bounds across the thirteen providers.

Source of every number: `site/public/data/comparison.v1.json`, the frozen
comparison audit, and only its `summaries` array and the provider records that
array is built from. No number here is re-derived by hand and no evaluation was
re-run to produce it.

What the bounds are, in the audit's own terms. Every provider is crossed with
every taxonomy topic, so a provider-topic cell is either a direct observation
or an explicit `coverage_default: unverified`. An unverified cell adds nothing
to the lower bound and one to the upper bound. An absent cell adds nothing to
either. A directly observed cell whose depth reaches the threshold counts in
both bounds. A cell that was observed but sits below the threshold counts in
neither, and it lowers that provider's ceiling.

That is why this project's own row is a set of exact counts and every other
row is an interval. All 93 of this project's cells are direct observations, so
its lower and upper bounds are equal at every threshold. The twelve external
providers are crossed with 93 topics as well, but their cells were classified
only from what each cell's own note and evidence state, and no external
provider was re-read to classify it, so their rows carry a genuine interval.

What the figure does not show. The external survey has not been re-run since
the date the audit froze, so an external bound is a statement about what was
known at that date and not about what a provider holds now. The intervals are
not confidence intervals and no probability attaches to them. A wide interval
says the evidence is thin, not that the provider is weak, and a narrow one
says the opposite. The audit itself records that the evidence does not support
a "most comprehensive" or a "most detailed" claim, and this figure does not
assert one.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 2
STEM = "plot_2_coverage_bounds"
SELF_ID = "aidd-commons"
TOTAL_TOPICS = 93

CAPTION = (
    "Coverage bounds for thirteen providers across five thresholds, each bound a lower and an "
    "upper count out of 93 topics. AIDD Commons is the first row and its bounds are equal at "
    "every threshold, {own}, because all 93 of its cells are direct observations. Every external "
    "row is an interval, because unobserved cells contribute to an upper bound and nothing to a "
    "lower one. The bounds are not confidence intervals and no probability attaches to them."
)

#: Short forms of the provider names for the row labels, one line each. They
#: are the audit's own provider ids, spelled out where the id is a handle.
DISPLAY = {
    "aidd-commons": "AIDD Commons",
    "agil": "AGIL",
    "build-ai-drug-discovery-pipelines": "Build AI pipelines",
    "chembl-training": "ChEMBL Quick Tour",
    "deepchem-tutorials": "DeepChem tutorials",
    "european-aidd-network": "EU AIDD network",
    "ml4drug-book": "ML4Drug book",
    "o3dc": "O3DC index",
    "openmm-cookbook": "OpenMM cookbook",
    "practical-cheminformatics": "Practical cheminformatics",
    "rdkit-cookbook": "RDKit cookbook",
    "teachopencadd": "TeachOpenCADD",
    "therapeutics-data-commons": "Therapeutics Data Commons",
}

THRESHOLD_TITLES = {
    "explained": "Explained",
    "worked": "Worked",
    "executable": "Executable",
    "executable-on-real-data": "Executable on real data",
    "assessed": "Assessed",
}


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    payload = style.load_json(style.DATA_DIR / "comparison.v1.json")

    names = {provider["id"]: provider["name"] for provider in payload["providers"]}
    classes = {provider["id"]: provider["provider_class"] for provider in payload["providers"]}
    thresholds = list(payload["thresholds"])

    bounds: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)
    for summary in payload["summaries"]:
        bounds[summary["provider_id"]][summary["threshold"]] = (summary["lower"], summary["upper"])

    order = [SELF_ID] + sorted(
        (provider for provider in bounds if provider != SELF_ID), key=lambda pid: names[pid]
    )
    class_order = ["curriculum", "tutorial-collection", "benchmark-hub", "specialist-reference"]
    class_colour = {
        "curriculum": colours["teal"],
        "tutorial-collection": colours["coral"],
        "benchmark-hub": colours["ember"],
        "specialist-reference": colours["slate"],
    }
    class_marker = {
        "curriculum": "o",
        "tutorial-collection": "s",
        "benchmark-hub": "^",
        "specialist-reference": "D",
    }

    rows = list(range(len(order)))[::-1]
    row_position = {provider: position for provider, position in zip(order, rows, strict=True)}

    fig = style.figure(style.FIGURE_WIDTH, 6.9)
    axes = style.axes_grid(
        fig,
        2,
        3,
        left=0.225,
        right=0.985,
        bottom=0.135,
        top=0.905,
        wspace=0.30,
        hspace=0.28,
    )

    panel_titles = [
        THRESHOLD_TITLES["explained"],
        THRESHOLD_TITLES["worked"],
        THRESHOLD_TITLES["executable"],
        THRESHOLD_TITLES["executable-on-real-data"],
        THRESHOLD_TITLES["assessed"],
    ]

    for index, (ax, panel) in enumerate(zip(axes[:5], panel_titles, strict=True)):
        threshold = thresholds[index]
        ax.axhspan(
            row_position[SELF_ID] - 0.5,
            row_position[SELF_ID] + 0.5,
            color=tokens["rule"],
            alpha=0.35,
            zorder=0,
        )
        for provider in order:
            lower, upper = bounds[provider][threshold]
            position = row_position[provider]
            ax.plot(
                [lower, upper],
                [position, position],
                color=class_colour[classes[provider]],
                marker=class_marker[classes[provider]],
                markersize=4.2,
                markeredgecolor=tokens["ink"],
                markeredgewidth=0.5,
                linewidth=1.7,
                solid_capstyle="butt",
                zorder=3,
            )
        ax.set_xlim(-2, 104)
        ax.set_ylim(-0.7, len(order) - 0.3)
        ax.set_xticks([0, 30, 60, 90])
        ax.set_yticks(rows)
        ax.set_yticklabels(
            [DISPLAY.get(provider, names[provider]) for provider in order],
            fontsize=7.8,
        )
        if index not in (0, 3):
            ax.set_yticklabels([])
        else:
            ax.get_yticklabels()[0].set_fontweight("bold")
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", linewidth=0.6, alpha=0.7)
        ax.set_axisbelow(True)
        style.title(ax, panel)
        value = bounds[SELF_ID][threshold][0]
        ax.annotate(
            str(value),
            xy=(value, row_position[SELF_ID]),
            xytext=(-5, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=7.6,
            color=tokens["ink"],
            fontweight="bold",
        )

    axes[3].set_xlabel("Topics out of 93", fontsize=8.5)
    axes[4].set_xlabel("Topics out of 93", fontsize=8.5)

    # The sixth panel answers the question the five panels raise: where this
    # project's exact count sits against the strongest bound any external
    # provider reaches on the same threshold.
    summary_ax = axes[5]
    threshold_rows = list(range(len(thresholds)))[::-1]
    for provider in order:
        if provider == SELF_ID:
            continue
        for threshold, position in zip(thresholds, threshold_rows, strict=True):
            lower, upper = bounds[provider][threshold]
            summary_ax.plot(
                [lower, upper],
                [position, position],
                color=tokens["rule"],
                linewidth=1.0,
                alpha=0.9,
                zorder=1,
            )
    for threshold, position in zip(thresholds, threshold_rows, strict=True):
        external_lower = max(
            bounds[provider][threshold][0] for provider in order if provider != SELF_ID
        )
        external_upper = max(
            bounds[provider][threshold][1] for provider in order if provider != SELF_ID
        )
        own = bounds[SELF_ID][threshold][0]
        summary_ax.plot(
            external_lower,
            position,
            marker="o",
            markersize=5.0,
            markerfacecolor="none",
            markeredgecolor=colours["coral"],
            markeredgewidth=1.1,
            linestyle="none",
            zorder=3,
        )
        summary_ax.plot(
            external_upper,
            position,
            marker="o",
            markersize=5.0,
            markerfacecolor=colours["coral"],
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.4,
            linestyle="none",
            zorder=3,
        )
        summary_ax.plot(
            own,
            position,
            marker="D",
            markersize=5.4,
            markerfacecolor=colours["teal"],
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.4,
            linestyle="none",
            zorder=4,
        )
    summary_ax.set_xlim(-2, 104)
    summary_ax.set_ylim(-0.7, len(thresholds) - 0.3)
    summary_ax.set_xticks([0, 30, 60, 90])
    summary_ax.set_yticks(threshold_rows)
    summary_ax.set_yticklabels(
        ["Explained", "Worked", "Executable", "On real data", "Assessed"], fontsize=7.8
    )
    summary_ax.tick_params(axis="y", length=0)
    summary_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    summary_ax.set_axisbelow(True)
    style.title(summary_ax, "External bounds")
    summary_ax.set_xlabel("Topics out of 93", fontsize=8.5)
    for threshold, position in zip(thresholds, threshold_rows, strict=True):
        own = bounds[SELF_ID][threshold][0]
        summary_ax.annotate(
            str(own),
            xy=(own, position),
            xytext=(-5, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=7.4,
            color=tokens["ink"],
            fontweight="bold",
        )

    summary_handles = [
        _point_handle(colours["teal"], "D", filled=True),
        _point_handle(colours["coral"], "o", filled=False),
        _point_handle(colours["coral"], "o", filled=True),
    ]
    summary_legend = fig.legend(
        summary_handles,
        [
            "AIDD Commons, exact count",
            "Largest external lower bound",
            "Largest external upper bound",
        ],
        loc="lower right",
        ncol=1,
        fontsize=7.6,
        handletextpad=0.5,
        borderpad=0.2,
        frameon=False,
        bbox_to_anchor=(0.995, 0.004),
        alignment="left",
    )
    summary_legend.set_in_layout(False)

    handles = [_legend_handle(class_colour[key], class_marker[key]) for key in class_order]
    labels = [
        "Curriculum",
        "Tutorial collection",
        "Benchmark hub",
        "Specialist reference",
    ]
    figure_legend = fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        fontsize=8.0,
        handletextpad=0.5,
        columnspacing=1.6,
        frameon=False,
        bbox_to_anchor=(0.36, 0.004),
    )
    figure_legend.set_in_layout(False)

    written = style.save(fig, STEM)
    own = style.english_list(
        f"{bounds[SELF_ID][threshold][0]} {THRESHOLD_TITLES[threshold].lower()}"
        for threshold in thresholds
    )
    style.register_caption(FIGURE_NUMBER, CAPTION.format(own=own))
    return written


def _legend_handle(colour: str, marker: str):
    """A legend handle in the shape of an interval mark."""
    from matplotlib.lines import Line2D

    return Line2D(
        [0],
        [0],
        color=colour,
        marker=marker,
        markersize=4.2,
        markeredgecolor=style.tokens("light")["ink"],
        markeredgewidth=0.5,
        linewidth=1.7,
    )


def _point_handle(colour: str, marker: str, *, filled: bool):
    """A legend handle in the shape of a point mark."""
    from matplotlib.lines import Line2D

    return Line2D(
        [0],
        [0],
        linestyle="none",
        marker=marker,
        markersize=5.2,
        markerfacecolor=colour if filled else "none",
        markeredgecolor=colour if not filled else style.tokens("light")["ink"],
        markeredgewidth=1.1 if not filled else 0.4,
    )


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
