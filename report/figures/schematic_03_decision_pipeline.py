"""Figure 3. The target-to-candidate decision pipeline.

The living report's stage table (`report/aidd-commons-living-report-v0.1.md`) is a table of nine
stages. For each stage it names a decision, a minimum evidence contract, a strong cheap baseline
and a frequent failure. The report also says why a bare funnel is not enough: the picture is
useful only if each narrowing step states what evidence entered, what was rejected, and what
decision followed.

So the figure draws a funnel and then draws the three things a funnel normally hides. Each
stage cell carries the stage name, the decision in question form, a narrowing drawn as a taper
with candidates in it, and a branch leaving the taper to the failure mode that the table records
for that stage. The route between the two rows makes the order explicit, and the key at the end
names the marks.

Nothing here is a count, a rate or a probability. The dots in a taper are candidates in a
schematic sense, and the number of dots is a drawing convention, not a measurement.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from schematic_style import (
    CAT,
    FILL,
    INK,
    MUTED,
    Canvas,
    arrow,
    label,
    panel_letter,
    rounded_box,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
STEM = "schematic-03-decision-pipeline"

WIDTH_IN = 6.38
HEIGHT_IN = 3.13

COL_X = [1.5, 21.0, 40.5, 60.0, 79.5]
CELL_W = 18.5
ROW1_Y = 26.5
ROW2_Y = 1.2
CELL_H = 20.0

# name lines, decision lines, failure-mode lines
STAGES = [
    (["Disease and", "mechanism"], ["Causal relevance"], ["Correlation as", "mechanism"]),
    (["Target", "identification"], ["Actionable entity"], ["Identity collapse"]),
    (["Target validation"], ["Phenotype change"], ["Evidence reuse"]),
    (["Assay and data", "strategy"], ["Optimisation quantity"], ["Pooled endpoints"]),
    (["Hit discovery"], ["Confirmation worth"], ["Retrospective as", "prospective"]),
    (["Hit confirmation"], ["Attributable activity"], ["Artefact as", "binding"]),
    (["Hit-to-lead"], ["Series headroom"], ["Endpoint loss"]),
    (["Lead optimisation"], ["Trade-off worth"], ["Scalar hides", "liability"]),
    (["Candidate", "nomination"], ["Package coherence"], ["Confidence as", "experiment"]),
]

STAGE_COLOUR = "teal"
FAIL_COLOUR = "coral"


# ---------------------------------------------------------------- marks
def mini_funnel(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    colour: str,
    zorder: float = 2.0,
) -> None:
    """A taper with candidates in it. The wide end is the pool, the narrow end is what moves on."""
    mid = y + h / 2.0
    narrow = h * 0.42
    canvas.ax.add_patch(
        plt.Polygon(
            [
                (x, y),
                (x + w, mid - narrow / 2.0),
                (x + w, mid + narrow / 2.0),
                (x, y + h),
            ],
            closed=True,
            facecolor=FILL[colour],
            edgecolor=CAT[colour],
            linewidth=0.7,
            hatch="//",
            zorder=zorder,
            joinstyle="miter",
        )
    )
    for dx, dy in ((0.12, 0.74), (0.12, 0.26), (0.26, 0.50), (0.26, 0.74), (0.40, 0.26)):
        canvas.ax.add_patch(
            plt.Circle(
                (x + w * dx, y + h * dy),
                h * 0.085,
                facecolor=CAT[colour],
                edgecolor="none",
                zorder=zorder + 0.2,
            )
        )
    canvas.ax.add_patch(
        plt.Circle(
            (x + w * 0.90, mid),
            h * 0.10,
            facecolor=CAT[colour],
            edgecolor="none",
            zorder=zorder + 0.3,
        )
    )


def stage_cell(
    canvas: Canvas,
    x: float,
    y: float,
    stage: tuple[list[str], list[str], list[str]],
) -> None:
    """One stage: the name, the decision, the narrowing, and the branch that leaves it."""
    name_lines, decision_lines, failure_lines = stage
    rounded_box(
        canvas,
        x,
        y,
        CELL_W,
        CELL_H,
        face=FILL[STAGE_COLOUR],
        edge=CAT[STAGE_COLOUR],
        lw=0.8,
        radius=0.7,
        zorder=1.0,
    )
    top = y + CELL_H
    label(
        canvas,
        x + 1.2,
        top - 2.3,
        "\n".join(name_lines),
        size=7.4,
        colour=INK,
        weight="bold",
        ha="left",
        va="top",
        zorder=2.0,
        linespacing=1.18,
    )
    label(
        canvas,
        x + 1.2,
        top - 6.0,
        "\n".join(decision_lines),
        size=6.2,
        colour=MUTED,
        ha="left",
        va="top",
        zorder=2.0,
        linespacing=1.18,
    )
    fx, fy, fw, fh = x + 1.2, y + 8.6, 11.4, 3.6
    mini_funnel(canvas, fx, fy, fw, fh, colour=STAGE_COLOUR)
    # the branch that leaves the taper
    canvas.ax.add_patch(
        plt.Circle(
            (fx + fw * 0.22, fy - 1.25),
            0.72,
            facecolor=CAT[FAIL_COLOUR],
            edgecolor=CAT[FAIL_COLOUR],
            linewidth=0.5,
            hatch="//",
            zorder=2.3,
        )
    )
    arrow(
        canvas,
        fx + fw * 0.22,
        fy + 0.20,
        fx + fw * 0.22,
        fy - 0.45,
        colour=CAT[FAIL_COLOUR],
        lw=0.7,
        head=2.0,
        zorder=2.2,
    )
    chip_x, chip_y, chip_w, chip_h = x + 1.2, y + 1.8, 13.6, 4.4
    rounded_box(
        canvas,
        chip_x,
        chip_y,
        chip_w,
        chip_h,
        face="none",
        edge=CAT[FAIL_COLOUR],
        lw=0.7,
        radius=0.4,
        zorder=2.0,
    )
    label(
        canvas,
        chip_x + chip_w / 2.0,
        chip_y + chip_h / 2.0,
        "\n".join(failure_lines),
        size=6.0,
        colour=CAT[FAIL_COLOUR],
        ha="center",
        va="center",
        zorder=2.2,
        linespacing=1.15,
    )


def key_cell(canvas: Canvas, x: float, y: float) -> None:
    """The key. It names the marks, so the drawing carries the argument on its own."""
    rounded_box(
        canvas,
        x,
        y,
        CELL_W,
        CELL_H,
        face="none",
        edge=MUTED,
        lw=0.8,
        radius=0.7,
        linestyle=(0, (2.6, 2.2)),
        zorder=1.0,
    )
    rows = [
        ("narrowing", "funnel"),
        ("candidates", "dots"),
        ("rejected branch", "exit"),
        ("failure mode", "chip"),
    ]
    for i, (word, kind) in enumerate(rows):
        ry = y + CELL_H - 3.4 - i * 4.2
        if kind == "funnel":
            mini_funnel(canvas, x + 1.4, ry - 1.5, 6.6, 2.6, colour=STAGE_COLOUR, zorder=2.0)
        elif kind == "dots":
            for j in range(4):
                canvas.ax.add_patch(
                    plt.Circle(
                        (x + 2.4 + (j % 2) * 1.8, ry - 0.6 - (j // 2) * 1.5),
                        0.55,
                        facecolor=CAT[STAGE_COLOUR],
                        edgecolor="none",
                        zorder=2.2,
                    )
                )
        elif kind == "exit":
            canvas.ax.add_patch(
                plt.Circle(
                    (x + 3.0, ry - 0.9),
                    0.72,
                    facecolor=CAT[FAIL_COLOUR],
                    edgecolor=CAT[FAIL_COLOUR],
                    linewidth=0.5,
                    hatch="//",
                    zorder=2.2,
                )
            )
            arrow(
                canvas,
                x + 3.0,
                ry + 0.9,
                x + 3.0,
                ry + 0.1,
                colour=CAT[FAIL_COLOUR],
                lw=0.7,
                head=2.0,
                zorder=2.1,
            )
        else:
            rounded_box(
                canvas,
                x + 1.4,
                ry - 1.6,
                6.4,
                2.6,
                face="none",
                edge=CAT[FAIL_COLOUR],
                lw=0.7,
                radius=0.4,
                zorder=2.0,
            )
        label(
            canvas,
            x + 9.2,
            ry - 0.4,
            word,
            size=6.4,
            colour=INK,
            ha="left",
            va="center",
            zorder=2.2,
        )


# ---------------------------------------------------------------- build
def build() -> Canvas:
    canvas = Canvas(WIDTH_IN, HEIGHT_IN)
    top = canvas.top

    panel_letter(canvas, 1.5, top - 1.9, "a", "Target to candidate")

    positions = [
        (COL_X[i], ROW1_Y) for i in range(5)
    ] + [(COL_X[i], ROW2_Y) for i in range(4)]

    for i, (x, y) in enumerate(positions):
        stage_cell(canvas, x, y, STAGES[i])

    key_cell(canvas, COL_X[4], ROW2_Y)

    # the flow along each row
    for row, last in ((ROW1_Y, 4), (ROW2_Y, 3)):
        for i in range(last):
            x0 = COL_X[i] + CELL_W
            arrow(
                canvas,
                x0 + 0.1,
                row + 10.4,
                COL_X[i + 1] - 0.1,
                row + 10.4,
                colour=CAT[STAGE_COLOUR],
                lw=0.9,
                head=2.8,
                zorder=2.0,
            )

    # the route from the end of the first row to the start of the second
    route_y = ROW2_Y + CELL_H + 2.6
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
