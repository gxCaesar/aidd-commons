"""Figure 6. Seven-dimensional openness.

The Atlas does not carry one open or closed label. It records seven dimensions separately, each
with its own state, and the report is explicit about why: code, weights, data and documentation
can carry different licences, and `available` is not the same as unrestricted
(`report/aidd-commons-living-report-v0.1.md`, `docs/RESOURCE_SCHEMA.md`). The seven dimensions
are inference code, training code, weights, architecture, data recipe, training data and
evaluation code. Each carries one of four states: available, not available, not applicable, or
unverified, where unverified records that no claim is made.

Panels (a) and (b) are two records from the catalogue, drawn as the forms they are. The model
and the dataset are close to opposites: where the model has inference code and weights, the
dataset has nothing to open there, and the dataset's one available dimension is the data recipe.
Panel (c) is the vocabulary of the four states. Panel (d) is the other two axes the record keeps,
lifecycle status and access level, which the schema holds separate from openness.

The two records are a dated snapshot. Their names and states come from the catalogue, and the
caption carries the review date. A later re-review can change the states.
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
    label,
    panel_letter,
    rounded_box,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
STEM = "schematic-06-openness-dimensions"

WIDTH_IN = 6.38
HEIGHT_IN = 4.21

OPEN_COLOUR = "teal"
AXIS_COLOUR = "slate"

FORM_X = [1.5, 51.0]
FORM_W = 47.5
FORM_Y = 24.0
FORM_H = 38.0
HEADER_H = 4.4
ROW_H = 4.8
CELL = 3.6
CELL_GAP = 1.2

KEY_X = 1.5
AXIS_X = 27.0
AXIS_CHIP_X = 36.5
ROW_Y = [18.5, 13.0, 7.5, 2.0]

DIMENSIONS = [
    "Inference code",
    "Training code",
    "Weights",
    "Architecture",
    "Data recipe",
    "Training data",
    "Evaluation code",
]

STATES = ["available", "not_available", "not_applicable", "unverified"]
STATE_LABELS = {
    "available": "available",
    "not_available": "not available",
    "not_applicable": "not applicable",
    "unverified": "unverified",
}

RECORDS = [
    ("Img2Mol", "model", [
        "available", "not_available", "available", "available",
        "unverified", "unverified", "not_available",
    ]),
    ("ADME-Fang-v1", "dataset", [
        "not_applicable", "not_applicable", "not_applicable", "not_applicable",
        "available", "unverified", "not_applicable",
    ]),
]

LIFECYCLE = ["active", "legacy", "superseded", "unmaintained", "withdrawn", "unverified"]
ACCESS_ROWS = [
    ["open source", "open weights", "source available"],
    ["research only", "gated", "api only"],
    ["closed", "unverified"],
]


# ---------------------------------------------------------------- the state mark
def state_cell(canvas: Canvas, x: float, y: float, size: float, state: str) -> None:
    """One openness state, drawn so that it survives the loss of colour."""
    colour = CAT[OPEN_COLOUR]
    if state == "available":
        rounded_box(
            canvas,
            x,
            y,
            size,
            size,
            face=colour,
            edge=colour,
            lw=0.6,
            radius=0.25,
            zorder=2.0,
        )
    elif state == "not_available":
        rounded_box(
            canvas,
            x,
            y,
            size,
            size,
            face=FILL[OPEN_COLOUR],
            edge=colour,
            lw=0.7,
            hatch="xx",
            radius=0.25,
            zorder=2.0,
        )
    elif state == "not_applicable":
        rounded_box(
            canvas,
            x,
            y,
            size,
            size,
            face=FILL[OPEN_COLOUR],
            edge=colour,
            lw=0.7,
            radius=0.25,
            zorder=2.0,
        )
        canvas.ax.plot(
            [x + size * 0.20, x + size * 0.80],
            [y + size * 0.20, y + size * 0.80],
            color=colour,
            linewidth=1.2,
            zorder=2.2,
        )
    elif state == "void":
        rounded_box(
            canvas,
            x,
            y,
            size,
            size,
            face="none",
            edge=colour,
            lw=0.45,
            radius=0.25,
            zorder=2.0,
        )
    else:
        rounded_box(
            canvas,
            x,
            y,
            size,
            size,
            face="none",
            edge=colour,
            lw=0.7,
            radius=0.25,
            zorder=2.0,
            linestyle=(0, (1.8, 1.6)),
        )


# ---------------------------------------------------------------- one record form
def record_form(
    canvas: Canvas,
    x: float,
    y: float,
    name: str,
    kind: str,
    states: list[str],
) -> None:
    rounded_box(
        canvas,
        x,
        y,
        FORM_W,
        FORM_H,
        face=FILL[OPEN_COLOUR],
        edge=CAT[OPEN_COLOUR],
        lw=0.9,
        radius=0.7,
        zorder=1.0,
    )
    header_y = y + FORM_H - HEADER_H
    canvas.ax.add_patch(
        plt.Rectangle(
            (x + 0.35, header_y + 0.3),
            FORM_W - 0.7,
            HEADER_H - 0.6,
            facecolor=CAT[OPEN_COLOUR],
            edgecolor="none",
            zorder=1.4,
        )
    )
    label(
        canvas,
        x + 1.8,
        header_y + HEADER_H / 2.0 - 0.1,
        name,
        size=8.2,
        colour=PANEL,
        weight="bold",
        ha="left",
        va="center",
        zorder=2.0,
    )
    label(
        canvas,
        x + FORM_W - 1.8,
        header_y + HEADER_H / 2.0 - 0.1,
        kind,
        size=6.2,
        colour=PANEL,
        ha="right",
        va="center",
        zorder=2.0,
    )
    cell_x0 = x + FORM_W - 2.0 - (4 * CELL + 3 * CELL_GAP)
    for i, dim in enumerate(DIMENSIONS):
        row_y = header_y - (i + 1) * ROW_H
        label(
            canvas,
            x + 1.8,
            row_y + ROW_H / 2.0,
            dim,
            size=6.4,
            colour=INK,
            ha="left",
            va="center",
            zorder=2.0,
        )
        for j, state in enumerate(STATES):
            state_cell(
                canvas,
                cell_x0 + j * (CELL + CELL_GAP),
                row_y + (ROW_H - CELL) / 2.0,
                CELL,
                state if state == states[i] else "void",
            )
        canvas.ax.plot(
            [x + 1.1, x + FORM_W - 1.1],
            [row_y + 0.2, row_y + 0.2],
            color=CAT[OPEN_COLOUR],
            linewidth=0.35,
            alpha=0.5,
            zorder=1.2,
        )


# ---------------------------------------------------------------- build
def build() -> Canvas:
    canvas = Canvas(WIDTH_IN, HEIGHT_IN)
    top = canvas.top

    panel_letter(canvas, FORM_X[0], top - 2.5, "a", "Model record")
    panel_letter(canvas, FORM_X[1], top - 2.5, "b", "Dataset record")

    for x, (name, kind, states) in zip(FORM_X, RECORDS, strict=True):
        record_form(canvas, x, FORM_Y, name, kind, states)

    # (c) the vocabulary of the four states
    panel_letter(canvas, KEY_X, 22.0, "c", "Four states")
    for i, state in enumerate(STATES):
        y = ROW_Y[i]
        state_cell(canvas, KEY_X, y, 3.4, state)
        label(
            canvas,
            KEY_X + 5.0,
            y + 1.7,
            STATE_LABELS[state],
            size=6.4,
            colour=INK,
            ha="left",
            va="center",
            zorder=2.4,
        )

    # (d) the two axes the record keeps separate
    panel_letter(canvas, AXIS_X, 22.0, "d", "Separate axes")
    ax_colour = CAT[AXIS_COLOUR]

    def chip_row(y: float, values: list[str]) -> None:
        x = AXIS_CHIP_X
        for value in values:
            w = 4.0 + len(value) * 0.46
            rounded_box(
                canvas,
                x,
                y,
                w,
                3.4,
                face=FILL[AXIS_COLOUR],
                edge=ax_colour,
                lw=0.6,
                radius=0.5,
                zorder=2.0,
            )
            label(
                canvas,
                x + w / 2.0,
                y + 1.7,
                value,
                size=5.8,
                colour=INK,
                ha="center",
                va="center",
                zorder=2.4,
            )
            x += w + 1.0

    label(
        canvas,
        AXIS_X,
        ROW_Y[0] + 1.7,
        "lifecycle",
        size=6.4,
        colour=ax_colour,
        weight="bold",
        ha="left",
        va="center",
        zorder=2.4,
    )
    chip_row(ROW_Y[0], LIFECYCLE)
    label(
        canvas,
        AXIS_X,
        ROW_Y[1] + 1.7,
        "access",
        size=6.4,
        colour=ax_colour,
        weight="bold",
        ha="left",
        va="center",
        zorder=2.4,
    )
    for i, values in enumerate(ACCESS_ROWS):
        chip_row(ROW_Y[i + 1], values)
    return canvas


def main() -> tuple[Path, Path]:
    canvas = build()
    return canvas.save(OUT_DIR, STEM)


if __name__ == "__main__":
    main()
