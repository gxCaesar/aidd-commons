"""Correlated frames and honest error bars.

Source of every number: `site/src/content/docs/labs/rmd17-dynamics-observable.mdx`,
the published lab page for the rMD17 trajectory observable.

There is no `labs/rmd17_system_state/observable-summary.json` in this
repository, so the reviewed artefact for this lab is the page itself. The
numbers are parsed out of that page rather than transcribed into this script,
so the figure cannot drift away from the page it cites, and the parser raises
if a number it expects is not on the page.

What the figure shows. The left panel puts the naive standard error next to
the block-averaged standard error for each of the two molecules. The middle
panel shows the ratio between them, which is the number the page reports and
the one a reader needs: treating the frames as independent understates the
uncertainty of the estimate by a factor of 3.30 for ethanol and 6.26 for
malonaldehyde. The right panel shows that the corrected estimate still carries
a choice inside it, because the block count changes the answer.

What it does not show. There is exactly one ab initio trajectory per molecule
here, so nothing in this figure speaks to replicate dependence between
independent runs, and there is exactly one level of theory, so nothing speaks
to force-field sensitivity. A radius of gyration is one scalar for a
nine-atom molecule and its dynamic range is inherently small. Which side of
one the ratio lands on is a property of the trajectory and not a mathematical
guarantee. None of these numbers is a binding affinity, a free energy, or a
claim about any system this repository has not directly loaded.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 11
STEM = "plot_11_correlated_frames_error_bars"
PAGE = Path("site/src/content/docs/labs/rmd17-dynamics-observable.mdx")
SYSTEMS = ["Ethanol", "Malonaldehyde"]

CAPTION = (
    "The uncertainty of a trajectory observable, from the rMD17 lab page. {values}. The middle "
    "panel is the ratio between the two estimates, which is the number the page reports. The right "
    "is ethanol's block-averaged standard error against the block count, because a corrected "
    "estimate still carries a choice inside it. There is one trajectory per molecule and one level "
    "of theory, so nothing here speaks to replicate dependence or force-field sensitivity."
)


def read_observable_page() -> dict:
    """Read the numbers of the rMD17 observable lab page.

    The page carries two markdown tables and one sentence with the block
    sweep. All three are parsed rather than transcribed, and a missing number
    raises instead of being silently dropped.
    """
    path = style.REPO_ROOT / PAGE
    text = path.read_text(encoding="utf-8").replace("−", "-")

    sem: dict[str, dict[str, float]] = {}
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] in SYSTEMS and len(cells) == 5:
            sem[cells[0]] = {
                "mean_rg": float(cells[1]),
                "naive_sem": float(cells[2]),
                "block_sem": float(cells[3]),
                "ratio": float(cells[4]),
            }
    missing = [system for system in SYSTEMS if system not in sem]
    if missing:
        raise ValueError(f"the observable page has no standard error row for {missing}")

    convergence: list[dict[str, float]] = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0].replace(",", "").isdigit():
            convergence.append(
                {
                    "frames": int(cells[0].replace(",", "")),
                    "ethanol": float(cells[1]),
                    "malonaldehyde": float(cells[2]),
                }
            )
    if not convergence:
        raise ValueError("the observable page has no convergence table")

    sweep = [
        {"blocks": int(blocks.replace(",", "")), "sem": float(value)}
        for blocks, value in re.findall(
            r"(?:block SEM )?at ([\d,]+) blocks \([^)]*\)\s+(?:is|it is)\s+([0-9.]+)",
            re.sub(r"\s+", " ", text),
        )
    ]
    if len(sweep) < 2:
        raise ValueError("the observable page has no block-count sweep")

    # The page reports the hundred-block estimate in the table and the other
    # block counts in the sentence, so the sweep is completed from the table.
    if not any(entry["blocks"] == 100 for entry in sweep):
        sweep.append({"blocks": 100, "sem": sem["Ethanol"]["block_sem"]})

    return {"sem": sem, "convergence": convergence, "sweep": sweep}


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    hatches = style.atlas_palette.HATCH

    page = read_observable_page()

    fig = style.figure(style.FIGURE_WIDTH, 3.6)
    axes = style.axes_grid(
        fig,
        1,
        3,
        left=0.115,
        right=0.985,
        bottom=0.185,
        top=0.855,
        wspace=0.40,
        width_ratios=[1.2, 0.8, 1.05],
    )
    sem_ax, ratio_ax, sweep_ax = axes

    positions = [0.0, 1.0]
    naive = [page["sem"][system]["naive_sem"] for system in SYSTEMS]
    block = [page["sem"][system]["block_sem"] for system in SYSTEMS]
    width = 0.34
    naive_container = sem_ax.bar(
        [position - width / 2 for position in positions],
        naive,
        width=width,
        color=colours["slate"],
        edgecolor=tokens["ink"],
        linewidth=0.6,
        label="Naive standard error",
        zorder=3,
    )
    block_container = sem_ax.bar(
        [position + width / 2 for position in positions],
        block,
        width=width,
        color=colours["teal"],
        edgecolor=tokens["ink"],
        linewidth=0.6,
        label="Block standard error, 100 blocks",
        zorder=3,
    )
    for bar in naive_container:
        bar.set_hatch(hatches["slate"])
    for bar in block_container:
        bar.set_hatch(hatches["teal"])
    style.bar_labels(sem_ax, naive_container, naive, fmt="{:.6f}", pad=2, fontsize=6.2)
    style.bar_labels(sem_ax, block_container, block, fmt="{:.6f}", pad=2, fontsize=6.2)
    sem_ax.set_xticks(positions)
    sem_ax.set_xticklabels(SYSTEMS, fontsize=8.2)
    sem_ax.set_ylabel("Standard error of the mean (Å)", fontsize=8.5)
    sem_ax.set_ylim(0, max(block) * 1.28)
    sem_ax.grid(axis="y", linewidth=0.6, alpha=0.7)
    sem_ax.set_axisbelow(True)
    style.title(sem_ax, "Two estimates of the same error")
    sem_ax.legend(
        loc="upper left",
        fontsize=7.4,
        handlelength=1.2,
        handleheight=1.0,
        borderpad=0.3,
        frameon=False,
    )

    ratios = [page["sem"][system]["ratio"] for system in SYSTEMS]
    container = ratio_ax.bar(
        positions,
        ratios,
        width=0.6,
        color=colours["teal"],
        edgecolor=tokens["ink"],
        linewidth=0.6,
        zorder=3,
    )
    for bar in container:
        bar.set_hatch(hatches["teal"])
    ratio_ax.axhline(1.0, color=tokens["ink"], linewidth=1.0, linestyle="--", zorder=4)
    ratio_ax.annotate(
        "the naive estimate",
        xy=(1.42, 1.0),
        xytext=(0, 4),
        textcoords="offset points",
        ha="right",
        fontsize=7.0,
        color=tokens["muted"],
    )
    style.bar_labels(ratio_ax, container, ratios, fmt="{:.2f}", pad=2, fontsize=7.6)
    ratio_ax.set_xticks(positions)
    ratio_ax.set_xticklabels(SYSTEMS, fontsize=8.2)
    ratio_ax.set_ylabel("Block error over naive error", fontsize=8.5)
    ratio_ax.set_ylim(0, max(ratios) * 1.22)
    ratio_ax.grid(axis="y", linewidth=0.6, alpha=0.7)
    ratio_ax.set_axisbelow(True)
    style.title(ratio_ax, "Understatement")

    sweep = sorted(page["sweep"], key=lambda entry: entry["blocks"])
    blocks = [entry["blocks"] for entry in sweep]
    values = [entry["sem"] for entry in sweep]
    naive_level = page["sem"]["Ethanol"]["naive_sem"]
    sweep_ax.axhline(
        naive_level,
        color=colours["slate"],
        linewidth=1.2,
        linestyle="--",
        zorder=2,
    )
    sweep_ax.annotate(
        "the naive estimate",
        xy=(blocks[-1], naive_level),
        xytext=(-2, 5),
        textcoords="offset points",
        ha="right",
        fontsize=7.0,
        color=tokens["muted"],
    )
    sweep_ax.plot(
        blocks,
        values,
        color=colours["teal"],
        marker="o",
        markersize=6.0,
        markerfacecolor=colours["teal"],
        markeredgecolor=tokens["ink"],
        markeredgewidth=0.5,
        linewidth=1.8,
        zorder=3,
    )
    for block_count, value in zip(blocks, values, strict=True):
        sweep_ax.annotate(
            f"{value:.6f}",
            xy=(block_count, value),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=6.6,
            color=tokens["ink"],
        )
    sweep_ax.set_xscale("log")
    sweep_ax.set_xticks(blocks)
    sweep_ax.set_xticklabels([str(block) for block in blocks], fontsize=8.2)
    sweep_ax.set_yscale("log")
    sweep_ax.set_ylim(0.00007, 0.00037)
    sweep_ax.set_yticks([0.00008, 0.0001, 0.0002, 0.0003])
    sweep_ax.set_yticklabels(["0.00008", "0.0001", "0.0002", "0.0003"], fontsize=7.6)
    sweep_ax.set_xlabel("Blocks used", fontsize=8.5)
    sweep_ax.set_ylabel("Block standard error (Å)", fontsize=8.5)
    sweep_ax.grid(axis="y", linewidth=0.6, alpha=0.7)
    sweep_ax.set_axisbelow(True)
    style.title(sweep_ax, "Ethanol, by block count")

    written = style.save(fig, STEM)
    values_text = style.english_list(
        f"{system} has a naive standard error of {page['sem'][system]['naive_sem']:.6f} Å "
        f"against a block-averaged standard error of {page['sem'][system]['block_sem']:.6f} Å "
        f"at 100 blocks"
        for system in SYSTEMS
    )
    style.register_caption(FIGURE_NUMBER, CAPTION.format(values=values_text))
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
