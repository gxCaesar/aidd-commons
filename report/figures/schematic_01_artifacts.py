"""Figure 1. Four artifacts, one system.

The repository holds four reader-facing artifacts, and the report says what binds them: they
share identifiers and editorial rules, so that a lesson can point to a resource record, a lab can
implement a lesson's protocol, and a correction can propagate to every surface that repeated the
claim (`report/aidd-commons-living-report-v0.1.md`). This figure draws that binding rather than
listing the four names.

Panel (a) gives each artifact a physical form, so that the reader learns four shapes once and
recognises them wherever they recur. Learn is a staircase of lesson tiles, because the curriculum
is ordered. Atlas is a field of record cells, because the catalogue is a registry that gets
filtered. Labs is a console with a run control, because a lab is something that executes. Report
is a ruled page carrying a figure, because the report is prose and drawing, both reviewed. The
four also carry four different colours, and the four shapes are what survive when the colour
does not.

Panel (b) draws the mechanism. A rail runs under the four artifacts and carries the shared
resource identifier. On the rail sits one token, a correction. Dashed branches carry it to four
identifier chips, and each chip is tied to the artifact above it. The shared identifiers are
therefore not a claim about the artifacts but the route a correction takes, which is the property
the report actually asserts.

Nothing in the artwork asserts a count, a coverage claim, or a measured outcome. The figure is a
map of the coupling, and the caption carries the argument.
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
    card,
    label,
    panel_letter,
    rounded_box,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
STEM = "schematic-01-artifacts"

WIDTH_IN = 6.38
HEIGHT_IN = 2.68

# Column geometry. Four artifacts across the page, each in a card that carries its own shape.
COL_X = [11.5, 33.5, 55.5, 77.5]
CARD_W = 21.0
CARD_Y = 19.4
CARD_H = 18.8
STRIP_H = 4.2

# Sparse hatches. The card is a container, so its texture stays light enough that the shape
# inside it still reads as the thing.
CARD_HATCH = {"teal": "/", "coral": "/", "ember": "\\", "slate": "x"}

ARTIFACTS = [
    ("Learn", "teal"),
    ("Atlas", "coral"),
    ("Labs", "ember"),
    ("Report", "slate"),
]


# ---------------------------------------------------------------- drawn forms
def learn_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """A staircase of lesson tiles. The curriculum is ordered, so the form climbs."""
    steps = 5
    tile_w = w * 0.185
    tile_h = h * 0.175
    gap = w * 0.03
    base = y + h * 0.06
    for i in range(steps):
        tx = x + w * 0.03 + i * (tile_w + gap)
        ty = base + i * (h * 0.155)
        top = i == steps - 1
        rounded_box(
            canvas,
            tx,
            ty,
            tile_w,
            tile_h,
            face=CAT["teal"] if top else FILL["teal"],
            edge=CAT["teal"],
            lw=0.7,
            hatch="//" if top else None,
            radius=0.25,
            zorder=2.0,
        )


def atlas_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """A field of record cells. One cell is selected, which is what filtering is."""
    cols, rows = 4, 3
    cw = w * 0.185
    ch = h * 0.215
    gap = w * 0.04
    ox = x + w * 0.05
    oy = y + h * 0.17
    for r in range(rows):
        for c in range(cols):
            picked = (r, c) == (1, 2)
            rounded_box(
                canvas,
                ox + c * (cw + gap),
                oy + r * (ch + gap),
                cw,
                ch,
                face=CAT["coral"] if picked else FILL["coral"],
                edge=CAT["coral"],
                lw=0.6,
                hatch="//" if picked else None,
                radius=0.25,
                zorder=2.0 + (0.05 if picked else 0.0),
            )


def labs_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """A console with a run control. A lab is something that executes."""
    body_x, body_y = x + w * 0.04, y + h * 0.16
    body_w, body_h = w * 0.72, h * 0.72
    rounded_box(
        canvas,
        body_x,
        body_y,
        body_w,
        body_h,
        face=FILL["ember"],
        edge=CAT["ember"],
        lw=0.7,
        radius=0.3,
        zorder=2.0,
    )
    canvas.ax.add_patch(
        plt.Rectangle(
            (body_x, body_y + body_h * 0.68),
            body_w,
            body_h * 0.32,
            facecolor=CAT["ember"],
            edgecolor="none",
            zorder=2.1,
        )
    )
    for i, frac in enumerate((0.52, 0.40, 0.46)):
        canvas.ax.add_patch(
            plt.Rectangle(
                (body_x + body_w * 0.10, body_y + body_h * (0.50 - i * 0.17)),
                body_w * frac,
                body_h * 0.085,
                facecolor=CAT["ember"],
                edgecolor="none",
                alpha=0.95,
                zorder=2.2,
            )
        )
    btn = h * 0.15
    bx, by = body_x + body_w * 0.74, body_y + body_h * 0.16
    canvas.ax.add_patch(
        plt.Polygon(
            [(bx, by), (bx + btn * 0.80, by + btn * 0.60), (bx, by + btn * 1.20)],
            closed=True,
            facecolor=CAT["ember"],
            edgecolor=CAT["ember"],
            linewidth=0.5,
            hatch="\\\\",
            zorder=2.3,
        )
    )


def report_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """A ruled page with a framed figure. The report is prose plus a drawing, both reviewed."""
    px, py = x + w * 0.10, y + h * 0.10
    pw, ph = w * 0.80, h * 0.78
    rounded_box(
        canvas, px, py, pw, ph, face=PANEL, edge=CAT["slate"], lw=0.7, radius=0.3, zorder=2.0
    )
    for i, frac in enumerate((0.70, 0.58, 0.64)):
        canvas.ax.add_patch(
            plt.Rectangle(
                (px + pw * 0.09, py + ph * (0.79 - i * 0.115)),
                pw * frac,
                ph * 0.05,
                facecolor=CAT["slate"],
                edgecolor="none",
                alpha=0.9,
                zorder=2.1,
            )
        )
    box_x, box_y = px + pw * 0.09, py + ph * 0.08
    box_w, box_h = pw * 0.82, ph * 0.34
    rounded_box(
        canvas,
        box_x,
        box_y,
        box_w,
        box_h,
        face=FILL["slate"],
        edge=CAT["slate"],
        lw=0.6,
        radius=0.2,
        zorder=2.1,
    )
    for i, (frac, tint) in enumerate(((0.55, 1.0), (0.80, 0.72), (0.66, 0.86))):
        canvas.ax.add_patch(
            plt.Rectangle(
                (box_x + box_w * (0.08 + i * 0.30), box_y + box_h * 0.22),
                box_w * frac * 0.22,
                box_h * 0.56,
                facecolor=CAT["slate"],
                edgecolor="none",
                alpha=tint,
                zorder=2.2,
            )
        )


FORMS = {
    "teal": learn_form,
    "coral": atlas_form,
    "ember": labs_form,
    "slate": report_form,
}


# ---------------------------------------------------------------- the identifier chip
def id_chip(canvas: Canvas, cx: float, y: float, w: float, h: float) -> None:
    """An identifier chip. The hash glyph is drawn, not spelled out."""
    rounded_box(
        canvas,
        cx - w / 2.0,
        y,
        w,
        h,
        face=FILL["slate"],
        edge=INK,
        lw=0.7,
        radius=h / 2.0,
        zorder=2.0,
    )
    gx, gy = cx - w * 0.30, y + h / 2.0
    for i, (dx, dh) in enumerate(((-1.35, 0.95), (-0.45, 1.45), (0.45, 1.15), (1.35, 1.60))):
        canvas.ax.plot(
            [gx + dx, gx + dx],
            [gy - dh, gy + dh],
            color=INK,
            linewidth=0.8 if i % 2 else 1.1,
            solid_capstyle="butt",
            zorder=3.0,
        )


# ---------------------------------------------------------------- build
def build() -> Canvas:
    canvas = Canvas(WIDTH_IN, HEIGHT_IN)
    top = canvas.top

    panel_letter(canvas, 1.5, top - 2.4, "a", "Four artifacts")
    panel_letter(canvas, 1.5, 17.4, "b", "Shared identifiers")

    # (a) the four cards
    for cx, (name, colour) in zip(COL_X, ARTIFACTS, strict=True):
        card(
            canvas,
            cx - CARD_W / 2.0,
            CARD_Y,
            CARD_W,
            CARD_H,
            colour=colour,
            filled=False,
            lw=0.8,
            radius=0.7,
            hatch="",
        )
        canvas.ax.add_patch(
            plt.Rectangle(
                (cx - CARD_W / 2.0 + 0.35, CARD_Y + 0.35),
                CARD_W - 0.7,
                STRIP_H - 0.7,
                facecolor=FILL[colour],
                edgecolor=CAT[colour],
                hatch=CARD_HATCH[colour],
                linewidth=0.5,
                zorder=1.2,
            )
        )
        label(
            canvas,
            cx,
            CARD_Y + STRIP_H / 2.0,
            name,
            size=8.8,
            colour=CAT[colour],
            weight="bold",
            ha="center",
            va="center",
            zorder=2.0,
        )
        FORMS[colour](
            canvas,
            cx - CARD_W / 2.0 + 0.8,
            CARD_Y + STRIP_H + 0.6,
            CARD_W - 1.6,
            CARD_H - STRIP_H - 1.2,
        )

    # (b) the shared rail and the correction token
    rail_y = 1.2
    rail_h = 3.0
    rail_x0 = 6.3
    rail_x1 = 97.0
    rounded_box(
        canvas,
        rail_x0,
        rail_y,
        rail_x1 - rail_x0,
        rail_h,
        face=CAT["slate"],
        edge=CAT["slate"],
        lw=0.9,
        radius=0.4,
        zorder=1.5,
    )

    # the rail's own name, and the one token that travels on it
    tag_x = rail_x0
    tag_w = 11.0
    rounded_box(
        canvas,
        tag_x,
        1.2,
        tag_w,
        4.6,
        face=PANEL,
        edge=CAT["slate"],
        lw=0.9,
        radius=0.5,
        zorder=2.0,
    )
    label(
        canvas,
        tag_x + tag_w / 2.0,
        3.5,
        "resource id",
        size=6.8,
        colour=CAT["slate"],
        weight="bold",
        ha="center",
        va="center",
        zorder=2.4,
    )

    token_x = 44.5
    token_w = 13.0
    rounded_box(
        canvas,
        token_x - token_w / 2.0,
        1.2,
        token_w,
        4.6,
        face=CAT["coral"],
        edge=CAT["coral"],
        lw=0.9,
        hatch="//",
        radius=0.5,
        zorder=2.0,
    )
    label(
        canvas,
        token_x,
        3.5,
        "correction",
        size=6.8,
        colour=PANEL,
        weight="bold",
        ha="center",
        va="center",
        zorder=2.4,
    )

    # the correction reaches each identifier chip, and each chip belongs to one artifact
    chip_y = 13.4
    chip_h = 3.6
    chip_w = 9.0
    for cx in COL_X:
        arrow(
            canvas,
            token_x,
            5.8,
            cx,
            chip_y + chip_h / 2.0,
            colour=CAT["coral"],
            lw=0.75,
            head=2.4,
            style="-|>",
            zorder=2.0,
        )
        id_chip(canvas, cx, chip_y, chip_w, chip_h)
        arrow(
            canvas,
            cx,
            chip_y + chip_h,
            cx,
            CARD_Y,
            colour=CAT["slate"],
            lw=0.75,
            head=2.6,
            zorder=2.0,
        )
    return canvas


def main() -> tuple[Path, Path]:
    canvas = build()
    return canvas.save(OUT_DIR, STEM)


if __name__ == "__main__":
    main()
