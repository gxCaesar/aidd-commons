"""Figure 4. Stage evidence contracts.

The living report's stage table gives each of the nine stages a minimum evidence contract: the
records a stage cannot be argued without (`report/aidd-commons-living-report-v0.1.md`). The
contracts differ from stage to stage, and that difference is the point. Target validation
demands an intervention, a dose, a model system and a rescue or an orthogonal assay. Lead
optimisation demands multi-parameter objectives, uncertainty, constraints and a synthesis cycle.
A stage that borrows another stage's contract has quietly changed what the stage means.

The figure draws each contract as a form. Every cell is one stage, the header names the stage,
and the fields below it are the records that stage demands, in the wording of the table. The
filled square at the head of each field marks it as required rather than optional. The nine
stages sit in the same order and the same route as the decision pipeline, so a reader can put
the two figures beside each other.

The figure shows the evidence contract only. It does not show the strong cheap baseline the
table also records for each stage, and it does not show the failure modes, which the decision
pipeline carries.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from schematic_style import (
    CAT,
    FILL,
    INK,
    PANEL,
    Canvas,
    arrow,
    label,
    panel_letter,
    rounded_box,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
STEM = "schematic-04-stage-contracts"

WIDTH_IN = 6.38
HEIGHT_IN = 3.19

COL_X = [1.5, 21.0, 40.5, 60.0, 79.5]
CELL_W = 18.5
CELL_H = 21.0
ROW1_Y = 27.0
ROW2_Y = 1.4
HEADER_H = 4.2

# stage name, then the minimum evidence contract exactly as the table words it
CONTRACTS = [
    (
        "Disease and\nmechanism",
        ["cohort", "tissue", "perturbation", "time", "phenotype", "confounders"],
    ),
    (
        "Target\nidentification",
        ["stable IDs", "isoform/state", "direction", "disease context"],
    ),
    (
        "Target validation",
        ["intervention", "dose", "model system", "rescue or\northogonal evidence"],
    ),
    (
        "Assay and data\nstrategy",
        ["protocol", "units", "censoring", "controls", "batch", "provenance"],
    ),
    ("Hit discovery", ["search space", "target state", "selection budget", "prospective test"]),
    (
        "Hit confirmation",
        ["orthogonal assay", "purity", "interference checks", "concentration\nresponse"],
    ),
    (
        "Hit-to-lead",
        ["series identity", "potency", "selectivity", "exposure", "synthesis"],
    ),
    (
        "Lead optimisation",
        ["multi-parameter\nobjectives", "uncertainty", "constraints", "synthesis cycle"],
    ),
    (
        "Candidate\nnomination",
        ["integrated efficacy", "safety", "DMPK", "CMC", "translational\nrationale"],
    ),
]

STAGE_COLOUR = "teal"


# ---------------------------------------------------------------- one field
def field(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    zorder: float = 2.0,
) -> None:
    """A required record. The filled square at its head says the field is not optional."""
    rounded_box(
        canvas,
        x,
        y,
        w,
        h,
        face=FILL[STAGE_COLOUR],
        edge=CAT[STAGE_COLOUR],
        lw=0.55,
        radius=0.3,
        zorder=zorder,
    )
    canvas.ax.add_patch(
        plt.Rectangle(
            (x + 0.55, y + h / 2.0 - 0.42),
            0.84,
            0.84,
            facecolor=CAT[STAGE_COLOUR],
            edgecolor="none",
            zorder=zorder + 0.1,
        )
    )
    label(
        canvas,
        x + 2.2,
        y + h / 2.0,
        text,
        size=5.4,
        colour=INK,
        ha="left",
        va="center",
        zorder=zorder + 0.2,
        linespacing=1.12,
    )


# ---------------------------------------------------------------- one stage
def stage_cell(canvas: Canvas, x: float, y: float, name: str, items: list[str]) -> None:
    rounded_box(
        canvas,
        x,
        y,
        CELL_W,
        CELL_H,
        face=PANEL,
        edge=CAT[STAGE_COLOUR],
        lw=0.8,
        radius=0.7,
        zorder=1.0,
    )
    header_y = y + CELL_H - HEADER_H
    canvas.ax.add_patch(
        plt.Rectangle(
            (x + 0.35, header_y + 0.35),
            CELL_W - 0.7,
            HEADER_H - 0.7,
            facecolor=CAT[STAGE_COLOUR],
            edgecolor="none",
            zorder=1.4,
        )
    )
    label(
        canvas,
        x + CELL_W / 2.0,
        header_y + HEADER_H / 2.0 - 0.1,
        name,
        size=6.9,
        colour=PANEL,
        weight="bold",
        ha="center",
        va="center",
        zorder=2.0,
        linespacing=1.15,
    )
    chip_x = x + 0.9
    chip_w = CELL_W - 1.8
    chip_y = y + CELL_H - HEADER_H - 1.1
    for item in items:
        lines = item.count("\n") + 1
        h = 1.95 if lines == 1 else 3.15
        field(canvas, chip_x, chip_y - h, chip_w, h, item)
        chip_y -= h + 0.3


# ---------------------------------------------------------------- build
def build() -> Canvas:
    canvas = Canvas(WIDTH_IN, HEIGHT_IN)
    top = canvas.top

    panel_letter(canvas, 1.5, top - 1.9, "a", "Stage evidence")

    positions = [(COL_X[i], ROW1_Y) for i in range(5)]
    positions += [(COL_X[i], ROW2_Y) for i in range(4)]

    for (x, y), (name, items) in zip(positions, CONTRACTS, strict=True):
        stage_cell(canvas, x, y, name, items)

    # the order of the stages
    for row, last in ((ROW1_Y, 4), (ROW2_Y, 3)):
        for i in range(last):
            arrow(
                canvas,
                COL_X[i] + CELL_W + 0.1,
                row + CELL_H - HEADER_H / 2.0 - 0.1,
                COL_X[i + 1] - 0.1,
                row + CELL_H - HEADER_H / 2.0 - 0.1,
                colour=CAT[STAGE_COLOUR],
                lw=0.9,
                head=2.8,
                zorder=2.0,
            )
    route_y = ROW2_Y + CELL_H + 2.3
    canvas.ax.plot(
        [COL_X[4] + CELL_W / 2.0, COL_X[4] + CELL_W / 2.0],
        [ROW1_Y - 0.1, route_y],
        color=CAT[STAGE_COLOUR],
        linewidth=0.9,
        zorder=2.0,
    )
    canvas.ax.plot(
        [COL_X[0] + CELL_W / 2.0, COL_X[4] + CELL_W / 2.0],
        [route_y, route_y],
        color=CAT[STAGE_COLOUR],
        linewidth=0.9,
        zorder=2.0,
    )
    arrow(
        canvas,
        COL_X[0] + CELL_W / 2.0,
        route_y,
        COL_X[0] + CELL_W / 2.0,
        ROW2_Y + CELL_H + 0.1,
        colour=CAT[STAGE_COLOUR],
        lw=0.9,
        head=2.8,
        zorder=2.0,
    )
    return canvas


def main() -> tuple[Path, Path]:
    canvas = build()
    return canvas.save(OUT_DIR, STEM)


if __name__ == "__main__":
    main()
