"""Figure 7. The frozen evaluation lifecycle.

The report's rule is that the protocol is frozen before the held-out test result is looked at,
and that the test set is opened once (`report/aidd-commons-living-report-v0.1.md`). The freeze
binds the task, the eligible samples, the labels, the split, the preprocessing, the baseline
recipes, the hyperparameter selection, the metrics, the calibration, the seed aggregation and the
stopping rule. Before the test is opened, the protocol has to pass structural and finite-output
checks on training and validation data. After the evaluation, the observed numbers are published
without result-driven retuning.

The figure draws that order as a sequence of gates, and then draws the part a diagram of
evaluation usually leaves out. A bug found after the test has been opened is reported as a
protocol-invalidating error. It is not a rerun. The barred loop at the end of the figure is that
prohibition, and the caption says what the figure does not show, which is any measured value:
the numbers belong to a laboratory report, not to a schematic.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Arc
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
STEM = "schematic-07-frozen-lifecycle"

WIDTH_IN = 6.38
HEIGHT_IN = 3.32

COL_X = [1.5, 21.0, 40.5, 60.0, 79.5]
CARD_W = 18.5
CARD_Y = 23.0
CARD_H = 25.0
HEADER_H = 4.4

TITLES = [
    "Protocol freeze",
    "Structural pretest",
    "Finite-output pretest",
    "One-time opening",
    "Reviewed summary",
]

FREEZE_ITEMS = ["split", "metrics", "seeds", "stop rule"]

DATA_Y = 1.5
DATA_H = 12.0


# ---------------------------------------------------------------- marks
def padlock(
    canvas: Canvas,
    cx: float,
    cy: float,
    size: float,
    colour: str,
    open_shackle: bool,
) -> None:
    """A lock. Closed means the protocol or the test set is sealed."""
    body_w = size * 0.86
    body_h = size * 0.66
    r = size * 0.34
    canvas.ax.add_patch(
        plt.Rectangle(
            (cx - body_w / 2.0, cy - body_h / 2.0),
            body_w,
            body_h,
            facecolor=colour,
            edgecolor=colour,
            linewidth=0.6,
            hatch="//",
            zorder=2.2,
        )
    )
    if open_shackle:
        canvas.ax.add_patch(
            Arc(
                (cx + size * 0.20, cy + body_h / 2.0),
                r * 2.0,
                r * 2.0,
                theta1=0,
                theta2=150,
                color=colour,
                linewidth=1.4,
                zorder=2.3,
            )
        )
    else:
        canvas.ax.add_patch(
            Arc(
                (cx, cy + body_h / 2.0),
                r * 2.0,
                r * 2.0,
                theta1=0,
                theta2=180,
                color=colour,
                linewidth=1.4,
                zorder=2.3,
            )
        )
    canvas.ax.add_patch(
        plt.Circle(
            (cx, cy - body_h * 0.05),
            size * 0.09,
            facecolor=PANEL,
            edgecolor="none",
            zorder=2.4,
        )
    )


def check_badge(canvas: Canvas, cx: float, cy: float, size: float, colour: str) -> None:
    canvas.ax.add_patch(
        plt.Circle(
            (cx, cy),
            size / 2.0,
            facecolor=colour,
            edgecolor=colour,
            linewidth=0.6,
            zorder=2.4,
        )
    )
    canvas.ax.plot(
        [cx - size * 0.22, cx - size * 0.05, cx + size * 0.24],
        [cy + size * 0.02, cy - size * 0.18, cy + size * 0.20],
        color=PANEL,
        linewidth=1.2,
        solid_capstyle="round",
        zorder=2.6,
    )


def barred_loop(canvas: Canvas, cx: float, cy: float, size: float, colour: str) -> None:
    """A loop with a bar across it. The set is not opened a second time."""
    canvas.ax.add_patch(
        Arc(
            (cx, cy),
            size,
            size * 0.86,
            theta1=35,
            theta2=320,
            color=colour,
            linewidth=1.3,
            zorder=2.4,
        )
    )
    canvas.ax.plot(
        [cx + size * 0.46, cx + size * 0.62],
        [cy + size * 0.32, cy + size * 0.20],
        color=colour,
        linewidth=1.2,
        solid_capstyle="round",
        zorder=2.5,
    )
    canvas.ax.plot(
        [cx - size * 0.58, cx + size * 0.58],
        [cy - size * 0.52, cy + size * 0.52],
        color=colour,
        linewidth=1.4,
        solid_capstyle="round",
        zorder=2.5,
    )


# ---------------------------------------------------------------- cards
def card_frame(canvas: Canvas, x: float, title: str, colour: str) -> None:
    rounded_box(
        canvas,
        x,
        CARD_Y,
        CARD_W,
        CARD_H,
        face=PANEL,
        edge=CAT[colour],
        lw=0.9,
        radius=0.7,
        zorder=1.0,
    )
    header_y = CARD_Y + CARD_H - HEADER_H
    canvas.ax.add_patch(
        plt.Rectangle(
            (x + 0.35, header_y + 0.3),
            CARD_W - 0.7,
            HEADER_H - 0.6,
            facecolor=CAT[colour],
            edgecolor="none",
            zorder=1.4,
        )
    )
    label(
        canvas,
        x + CARD_W / 2.0,
        header_y + HEADER_H / 2.0 - 0.1,
        title,
        size=7.2,
        colour=PANEL,
        weight="bold",
        ha="center",
        va="center",
        zorder=2.0,
    )


def freeze_body(canvas: Canvas, x: float) -> None:
    padlock(canvas, x + CARD_W / 2.0, CARD_Y + 15.0, 6.4, CAT["teal"], open_shackle=False)
    for i, item in enumerate(FREEZE_ITEMS):
        cx = x + 4.2 + (i % 2) * 9.0
        cy = CARD_Y + 2.6 + (1 - i // 2) * 4.4
        rounded_box(
            canvas,
            cx - 4.0,
            cy,
            8.0,
            3.4,
            face=FILL["teal"],
            edge=CAT["teal"],
            lw=0.6,
            radius=0.5,
            zorder=2.0,
        )
        label(
            canvas,
            cx,
            cy + 1.7,
            item,
            size=6.0,
            colour=INK,
            ha="center",
            va="center",
            zorder=2.4,
        )


def structure_body(canvas: Canvas, x: float) -> None:
    cell = 3.0
    gap = 0.5
    ox = x + 2.2
    oy = CARD_Y + 8.0
    for r in range(3):
        for c in range(3):
            filled = (r + c) % 3 == 0
            rounded_box(
                canvas,
                ox + c * (cell + gap),
                oy + (2 - r) * (cell + gap),
                cell,
                cell,
                face=CAT["teal"] if filled else FILL["teal"],
                edge=CAT["teal"],
                lw=0.6,
                radius=0.25,
                zorder=2.0,
            )
    check_badge(canvas, x + CARD_W - 4.2, CARD_Y + 10.6, 4.0, CAT["teal"])
    for i in range(4):
        cy = CARD_Y + 5.2 - i * 1.6
        rounded_box(
            canvas,
            x + 2.2,
            cy,
            1.7,
            1.7,
            face=FILL["teal"],
            edge=CAT["teal"],
            lw=0.55,
            radius=0.2,
            zorder=2.0,
        )
        canvas.ax.plot(
            [x + 2.6, x + 2.9, x + 3.4],
            [cy + 0.72, cy + 0.28, cy + 1.05],
            color=CAT["teal"],
            linewidth=0.9,
            solid_capstyle="round",
            zorder=2.4,
        )
        canvas.ax.plot(
            [x + 4.6, x + 11.0],
            [cy + 0.7, cy + 0.7],
            color=CAT["teal"],
            linewidth=0.8,
            alpha=0.55,
            zorder=2.1,
        )


def finite_body(canvas: Canvas, x: float) -> None:
    cell = 2.9
    gap = 0.5
    ox = x + 2.2
    oy = CARD_Y + 12.0
    for i in range(5):
        rounded_box(
            canvas,
            ox + i * (cell + gap),
            oy,
            cell,
            cell,
            face=CAT["teal"],
            edge=CAT["teal"],
            lw=0.6,
            radius=0.25,
            zorder=2.0,
        )
        canvas.ax.plot(
            [ox + i * (cell + gap) + 0.55, ox + i * (cell + gap) + 1.15],
            [oy + cell * 0.55, oy + cell * 0.55],
            color=PANEL,
            linewidth=0.7,
            alpha=0.8,
            zorder=2.3,
        )
    check_badge(canvas, x + CARD_W - 4.2, CARD_Y + 13.4, 4.0, CAT["teal"])
    for i in range(3):
        cy = CARD_Y + 8.4 - i * 3.0
        canvas.ax.plot(
            [x + 2.4, x + 15.6],
            [cy, cy],
            color=CAT["teal"],
            linewidth=0.9,
            alpha=0.5,
            zorder=2.1,
        )
        canvas.ax.add_patch(
            plt.Circle(
                (x + 2.0, cy),
                0.85,
                facecolor=CAT["teal"],
                edgecolor="none",
                zorder=2.2,
            )
        )


def opening_body(canvas: Canvas, x: float) -> None:
    mid = CARD_Y + 13.0
    rounded_box(
        canvas,
        x + 8.4,
        mid - 4.6,
        8.0,
        9.2,
        face=FILL["ember"],
        edge=CAT["ember"],
        lw=0.8,
        radius=0.5,
        zorder=2.0,
    )
    padlock(canvas, x + 12.4, mid + 1.6, 4.6, CAT["ember"], open_shackle=True)
    arrow(
        canvas,
        x + 1.8,
        mid - 2.4,
        x + 8.0,
        mid - 2.4,
        colour=CAT["ember"],
        lw=1.0,
        head=2.8,
        zorder=2.4,
    )
    label(
        canvas,
        x + 4.9,
        mid - 0.9,
        "1",
        size=7.0,
        colour=CAT["ember"],
        weight="bold",
        ha="center",
        va="center",
        zorder=2.4,
    )
    canvas.ax.plot(
        [x + 2.0, x + 16.6],
        [mid - 6.4, mid - 6.4],
        color=CAT["ember"],
        linewidth=0.5,
        alpha=0.5,
        zorder=2.1,
    )
    for i in range(3):
        canvas.ax.plot(
            [x + 2.0, x + 16.6],
            [mid - 8.0 - i * 1.7, mid - 8.0 - i * 1.7],
            color=CAT["ember"],
            linewidth=0.9,
            alpha=0.45,
            zorder=2.1,
        )


def summary_body(canvas: Canvas, x: float) -> None:
    ox = x + 2.2
    oy = CARD_Y + 8.6
    for r in range(3):
        for c in range(4):
            rounded_box(
                canvas,
                ox + c * 3.5,
                oy + (2 - r) * 3.3,
                3.0,
                2.8,
                face=FILL["teal"] if c == 0 else PANEL,
                edge=CAT["teal"],
                lw=0.6,
                radius=0.25,
                zorder=2.0,
            )
    check_badge(canvas, x + CARD_W - 4.0, CARD_Y + 4.6, 4.0, CAT["teal"])
    canvas.ax.add_patch(
        plt.Circle(
            (x + 4.6, CARD_Y + 4.6),
            3.0,
            facecolor="none",
            edgecolor=CAT["teal"],
            linewidth=0.8,
            zorder=2.0,
        )
    )
    canvas.ax.plot(
        [x + 3.3, x + 4.4, x + 6.0],
        [CARD_Y + 4.6, CARD_Y + 3.4, CARD_Y + 5.8],
        color=CAT["teal"],
        linewidth=1.1,
        solid_capstyle="round",
        zorder=2.4,
    )


# ---------------------------------------------------------------- build
def build() -> Canvas:
    canvas = Canvas(WIDTH_IN, HEIGHT_IN)
    top = canvas.top

    panel_letter(canvas, 1.5, top - 2.5, "a", "Frozen evaluation")

    for i, title in enumerate(TITLES):
        card_frame(canvas, COL_X[i], title, "ember" if i == 3 else "teal")
    freeze_body(canvas, COL_X[0])
    structure_body(canvas, COL_X[1])
    finite_body(canvas, COL_X[2])
    opening_body(canvas, COL_X[3])
    summary_body(canvas, COL_X[4])

    # the lifecycle order
    for i in range(4):
        arrow(
            canvas,
            COL_X[i] + CARD_W + 0.1,
            CARD_Y + 12.5,
            COL_X[i + 1] - 0.1,
            CARD_Y + 12.5,
            colour=CAT["teal"],
            lw=1.0,
            head=2.8,
            zorder=2.4,
        )

    # the written protocol feeds the freeze
    sheet_x, sheet_y = COL_X[0] + 5.0, DATA_Y + 3.0
    rounded_box(
        canvas,
        sheet_x,
        sheet_y,
        8.0,
        8.0,
        face=PANEL,
        edge=CAT["teal"],
        lw=0.8,
        radius=0.4,
        zorder=2.0,
    )
    for i in range(4):
        canvas.ax.plot(
            [sheet_x + 1.0, sheet_x + 7.0 - i * 0.9],
            [sheet_y + 6.4 - i * 1.6, sheet_y + 6.4 - i * 1.6],
            color=CAT["teal"],
            linewidth=0.9,
            alpha=0.75,
            zorder=2.2,
        )
    label(
        canvas,
        COL_X[0] + CARD_W / 2.0,
        DATA_Y - 0.4,
        "protocol",
        size=6.2,
        colour=INK,
        ha="center",
        va="bottom",
        zorder=2.4,
    )
    arrow(
        canvas,
        COL_X[0] + CARD_W / 2.0,
        sheet_y + 8.2,
        COL_X[0] + CARD_W / 2.0,
        CARD_Y - 0.1,
        colour=CAT["teal"],
        lw=0.9,
        head=2.6,
        zorder=2.2,
    )

    # training and validation data feed the two pretests
    data_x0 = COL_X[1]
    data_x1 = COL_X[2] + CARD_W
    rounded_box(
        canvas,
        data_x0,
        DATA_Y,
        data_x1 - data_x0,
        DATA_H,
        face=FILL["teal"],
        edge=CAT["teal"],
        lw=0.8,
        radius=0.5,
        zorder=1.6,
    )
    cell_w, cell_h, gap = 2.3, 2.2, 0.4
    for r in range(3):
        for c in range(11):
            filled = (r * 11 + c) % 4 == 0
            rounded_box(
                canvas,
                data_x0 + 2.2 + c * (cell_w + gap),
                DATA_Y + 9.5 - r * (cell_h + gap),
                cell_w,
                cell_h,
                face=CAT["teal"] if filled else PANEL,
                edge=CAT["teal"],
                lw=0.45,
                radius=0.2,
                zorder=1.8,
            )
    label(
        canvas,
        data_x0 + 2.2,
        DATA_Y + 1.0,
        "training and validation",
        size=6.2,
        colour=INK,
        ha="left",
        va="bottom",
        zorder=2.4,
    )
    for i in (1, 2):
        arrow(
            canvas,
            COL_X[i] + CARD_W / 2.0,
            DATA_Y + DATA_H + 0.1,
            COL_X[i] + CARD_W / 2.0,
            CARD_Y - 0.1,
            colour=CAT["teal"],
            lw=0.9,
            head=2.6,
            zorder=2.2,
        )

    # the stop rule
    err_x0 = COL_X[3]
    err_x1 = COL_X[4] + CARD_W
    rounded_box(
        canvas,
        err_x0,
        DATA_Y,
        err_x1 - err_x0,
        DATA_H,
        face=FILL["coral"],
        edge=CAT["coral"],
        lw=0.9,
        radius=0.5,
        zorder=1.6,
    )
    barred_loop(canvas, err_x0 + 6.0, DATA_Y + DATA_H / 2.0, 6.0, CAT["coral"])
    label(
        canvas,
        err_x0 + 11.5,
        DATA_Y + DATA_H / 2.0,
        "protocol-invalidating error",
        size=6.4,
        colour=CAT["coral"],
        weight="bold",
        ha="left",
        va="center",
        zorder=2.4,
    )
    arrow(
        canvas,
        COL_X[3] + CARD_W / 2.0,
        CARD_Y - 0.1,
        COL_X[3] + CARD_W / 2.0,
        DATA_Y + DATA_H + 0.1,
        colour=CAT["coral"],
        lw=0.9,
        head=2.6,
        zorder=2.2,
    )
    return canvas


def main() -> tuple[Path, Path]:
    canvas = build()
    return canvas.save(OUT_DIR, STEM)


if __name__ == "__main__":
    main()
