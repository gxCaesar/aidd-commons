"""Two assay systems disagree.

Source of every number: `labs/cyp_assay_system/summary.json` and
`labs/az_clearance_system/summary.json`, the reviewed summaries of two
completed assay-system labs. The first holds the correlation between the
CYP2D6 and CYP3A4 assay systems and the molecules on which they disagree
most; the second holds the correlation between three clearance assay systems
and the molecules on which they disagree most.

What the figure shows. The left panel puts the two correlations of every
system pair side by side, with the number of shared molecules on each row, so
that the size of the overlap is visible next to the size of the correlation.
The right panel takes the six molecules the CYP lab names as its largest
disagreements and draws both systems' pChEMBL values for each, which is the
form the disagreement takes at the level of one molecule: three molecules the
first system rates far above the second, and three the second rates far above
the first.

What it does not show. A correlation near 0.3 between two assay systems means
that a measurement in one system carries little information about the
measurement in the other, which is not the same as saying that either system
is wrong. The divergence examples are the extremes the review found and they
are not a sample of the distribution. The clearance pairs differ in species,
in matrix or in both, which is recorded on each row in the summary and is the
reason those rows are not interchangeable with the CYP rows. The p values in
the summaries are not drawn here, because with a correlation this low they say
only that the sample is not zero.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 13
STEM = "plot_13_two_assay_systems_disagree"

CAPTION = (
    "Two pairs of assay systems that disagree. {correlation}. The six largest disagreements "
    "between the two CYP systems span {spread} pChEMBL in both directions, with the first "
    "system higher on three molecules and the second on three. A correlation near "
    "0.3 means a measurement in one system carries little information about the other, which is "
    "not the same as saying either system is wrong, and the six molecules are the extremes the "
    "review found rather than a sample of the distribution."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")

    cyp = style.load_json(style.REPO_ROOT / "labs" / "cyp_assay_system" / "summary.json")
    clearance = style.load_json(
        style.REPO_ROOT / "labs" / "az_clearance_system" / "summary.json"
    )

    fig = style.figure(style.FIGURE_WIDTH, 4.6)
    axes = style.axes_grid(
        fig,
        1,
        2,
        left=0.285,
        right=0.985,
        bottom=0.145,
        top=0.90,
        wspace=0.44,
        width_ratios=[1.0, 1.05],
    )
    correlation_ax, divergence_ax = axes

    rows = [
        (
            "CYP2D6 against CYP3A4, all pairs",
            cyp["correlation"]["full"]["count"],
            cyp["correlation"]["full"]["pearson_r"],
            cyp["correlation"]["full"]["spearman_rho"],
        ),
        (
            "CYP2D6 against CYP3A4, clean pairs",
            cyp["correlation"]["clean_pairs_only"]["count"],
            cyp["correlation"]["clean_pairs_only"]["pearson_r"],
            cyp["correlation"]["clean_pairs_only"]["spearman_rho"],
        ),
    ]
    for pair in clearance["pairs"].values():
        short = {
            "CHEMBL3301370": "microsome",
            "CHEMBL3301371": "rat hepatocyte",
            "CHEMBL3301372": "human hepatocyte",
        }
        rows.append(
            (
                f"{short[pair['primary_system']]} against {short[pair['secondary_system']]}",
                pair["clean_pair_count"],
                pair["correlation"]["pearson_r"],
                pair["correlation"]["spearman_rho"],
            )
        )

    positions = list(range(len(rows)))[::-1]
    for position, (_label, count, pearson, spearman) in zip(positions, rows, strict=True):
        correlation_ax.plot(
            [pearson, spearman],
            [position, position],
            color=tokens["rule"],
            linewidth=1.4,
            zorder=2,
        )
        correlation_ax.plot(
            pearson,
            position,
            marker="o",
            markersize=6.0,
            markerfacecolor=colours["slate"],
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.5,
            linestyle="none",
            zorder=3,
        )
        correlation_ax.plot(
            spearman,
            position,
            marker="s",
            markersize=6.0,
            markerfacecolor="none",
            markeredgecolor=colours["coral"],
            markeredgewidth=1.4,
            linestyle="none",
            zorder=4,
        )
        correlation_ax.annotate(
            f"n = {count}",
            xy=(0.53, position),
            xytext=(0, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=7.2,
            color=tokens["muted"],
        )

    correlation_ax.set_xlim(-0.02, 0.72)
    correlation_ax.set_ylim(-0.6, len(rows) - 0.4)
    correlation_ax.set_yticks(positions)
    correlation_ax.set_yticklabels([label for label, _, _, _ in rows], fontsize=6.9)
    correlation_ax.tick_params(axis="y", length=0)
    correlation_ax.set_xticks([0.0, 0.2, 0.4, 0.6])
    correlation_ax.set_xlabel("Correlation between the two systems", fontsize=8.5)
    correlation_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    correlation_ax.set_axisbelow(True)
    style.title(correlation_ax, "Correlation by system pair")
    correlation_ax.plot(
        [],
        [],
        marker="o",
        markersize=6.0,
        markerfacecolor=colours["slate"],
        markeredgecolor=tokens["ink"],
        markeredgewidth=0.5,
        linestyle="none",
        label="Pearson r",
    )
    correlation_ax.plot(
        [],
        [],
        marker="s",
        markersize=6.0,
        markerfacecolor="none",
        markeredgecolor=colours["coral"],
        markeredgewidth=1.4,
        linestyle="none",
        label="Spearman rho",
    )
    correlation_ax.legend(
        loc="upper left",
        fontsize=8.0,
        handletextpad=0.4,
        borderpad=0.3,
        frameon=False,
        ncol=2,
        columnspacing=1.4,
    )

    examples = [
        (
            record["parent_molecule_chembl_id"],
            record["primary_pchembl"],
            record["secondary_pchembl"],
        )
        for record in cyp["divergent_examples"]["primary_selective"]
    ] + [
        (
            record["parent_molecule_chembl_id"],
            record["primary_pchembl"],
            record["secondary_pchembl"],
        )
        for record in cyp["divergent_examples"]["secondary_selective"]
    ]
    examples.sort(key=lambda entry: entry[1] - entry[2], reverse=True)
    example_positions = list(range(len(examples)))[::-1]
    for position, (_identifier, primary, secondary) in zip(
        example_positions, examples, strict=True
    ):
        divergence_ax.plot(
            [primary, secondary],
            [position, position],
            color=tokens["rule"],
            linewidth=1.4,
            zorder=2,
        )
        divergence_ax.plot(
            primary,
            position,
            marker="o",
            markersize=6.0,
            markerfacecolor=colours["teal"],
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.5,
            linestyle="none",
            zorder=3,
        )
        divergence_ax.plot(
            secondary,
            position,
            marker="s",
            markersize=6.0,
            markerfacecolor="none",
            markeredgecolor=colours["coral"],
            markeredgewidth=1.4,
            linestyle="none",
            zorder=4,
        )
        divergence_ax.annotate(
            f"{primary - secondary:+.2f}",
            xy=((primary + secondary) / 2, position),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=7.2,
            color=tokens["ink"],
        )

    divergence_ax.set_xlim(0, 8.6)
    divergence_ax.set_ylim(-0.6, len(examples) - 0.4)
    divergence_ax.set_yticks(example_positions)
    divergence_ax.set_yticklabels([identifier for identifier, _, _ in examples], fontsize=7.6)
    divergence_ax.tick_params(axis="y", length=0)
    divergence_ax.set_xlabel("pChEMBL in each system", fontsize=8.5)
    divergence_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    divergence_ax.set_axisbelow(True)
    style.title(divergence_ax, "The largest disagreements")
    divergence_ax.plot(
        [],
        [],
        marker="o",
        markersize=6.0,
        markerfacecolor=colours["teal"],
        markeredgecolor=tokens["ink"],
        markeredgewidth=0.5,
        linestyle="none",
        label="CYP2D6 system",
    )
    divergence_ax.plot(
        [],
        [],
        marker="s",
        markersize=6.0,
        markerfacecolor="none",
        markeredgecolor=colours["coral"],
        markeredgewidth=1.4,
        linestyle="none",
        label="CYP3A4 system",
    )
    divergence_ax.legend(
        loc="upper left",
        fontsize=7.8,
        handletextpad=0.4,
        borderpad=0.3,
        frameon=False,
        ncol=1,
    )

    correlation_text = style.english_list(
        f"{label} reaches a Pearson r of {pearson:.4f} and a Spearman rho of {spearman:.4f} over "
        f"{count} shared molecules"
        for label, count, pearson, spearman in rows
    )
    divergence_text = style.english_list(
        f"{identifier} at {primary:.2f} against {secondary:.2f}"
        for identifier, primary, secondary in examples
    )
    spread = f"{min(abs(primary - secondary) for _, primary, secondary in examples):.2f} to "
    spread += f"{max(abs(primary - secondary) for _, primary, secondary in examples):.2f}"
    written = style.save(fig, STEM)
    style.register_caption(
        FIGURE_NUMBER,
        CAPTION.format(correlation=correlation_text, divergence=divergence_text, spread=spread),
    )
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
