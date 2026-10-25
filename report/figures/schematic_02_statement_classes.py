"""Figure 2. Four classes of statement.

`docs/EDITORIAL_GUIDE.md` opens with the rule that makes the project's prose checkable. Wording
has to make each statement's authority visible, and it names four classes. An observed source
fact is what an opened paper, repository, licence, dataset page, standard or measured artifact
directly establishes, and it is cited at the sentence or table row. A project decision is an
AIDD Commons choice, given with its rationale and version. An open question identifies missing,
conflicting or inaccessible evidence, and the correct state stays `unverified` rather than being
completed by inference. Future work describes an intended contribution that has not been
implemented, reviewed or measured.

The classes differ in kind, not in degree, and a degree scale would misdescribe them. So the
figure gives each one a form instead of a position on a scale. The first two assert something,
and they are drawn solid. The last two assert nothing yet, and they are drawn dashed. The band
underneath names the distinction and the four panels are grouped by it, which is the only
grouping the guide supports.

Each class carries its own evidence in the drawing rather than in a sentence. An observed fact
shows the opened document and the link that ties it to a claim. A project decision shows
several inputs meeting at one node. An open question shows an undefined object, ringed and
spoked. Future work shows tiles that are planned and not yet built.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
from schematic_style import (
    CAT,
    FILL,
    PANEL,
    Canvas,
    arrow,
    label,
    panel_letter,
    rounded_box,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
STEM = "schematic-02-statement-classes"

WIDTH_IN = 6.38
HEIGHT_IN = 2.49

CARD_X = [1.5, 25.75, 50.0, 74.25]
CARD_W = 23.5
CARD_Y = 18.0
CARD_H = 18.2
STRIP_H = 4.2

CLASSES = [
    ("a", "Observed source fact", "teal"),
    ("b", "Project decision", "coral"),
    ("c", "Open question", "ember"),
    ("d", "Future work", "slate"),
]


# ---------------------------------------------------------------- drawn forms
def fact_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """An opened document with the link that ties it to a claim."""
    sheet_x, sheet_y = x + w * 0.08, y + h * 0.10
    sheet_w, sheet_h = w * 0.58, h * 0.80
    rounded_box(
        canvas,
        sheet_x,
        sheet_y,
        sheet_w,
        sheet_h,
        face=PANEL,
        edge=CAT["teal"],
        lw=0.8,
        radius=0.35,
        zorder=2.0,
    )
    for i, frac in enumerate((0.74, 0.60, 0.68, 0.46)):
        canvas.ax.add_patch(
            plt.Rectangle(
                (sheet_x + sheet_w * 0.11, sheet_y + sheet_h * (0.76 - i * 0.17)),
                sheet_w * frac,
                sheet_h * 0.055,
                facecolor=CAT["teal"],
                edgecolor="none",
                alpha=0.9,
                zorder=2.1,
            )
        )
    badge = min(w, h) * 0.30
    bx, by = x + w * 0.60, y + h * 0.30
    rounded_box(
        canvas,
        bx,
        by,
        badge,
        badge,
        face=CAT["teal"],
        edge=CAT["teal"],
        lw=0.6,
        hatch="//",
        radius=0.3,
        zorder=2.3,
    )
    r = badge * 0.20
    canvas.ax.add_patch(
        plt.Circle(
            (bx + badge * 0.40, by + badge * 0.5),
            r,
            facecolor="none",
            edgecolor=PANEL,
            linewidth=1.0,
            zorder=2.6,
        )
    )
    canvas.ax.add_patch(
        plt.Circle(
            (bx + badge * 0.60, by + badge * 0.5),
            r,
            facecolor="none",
            edgecolor=PANEL,
            linewidth=1.0,
            zorder=2.6,
        )
    )


def decision_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Several inputs meeting at one node. The decision is where they land."""
    chip = min(w, h) * 0.20
    cx0 = x + w * 0.06
    for i in range(3):
        cy = y + h * 0.74 - i * (h * 0.30)
        rounded_box(
            canvas,
            cx0,
            cy - chip / 2.0,
            chip * 1.5,
            chip * 0.62,
            face=FILL["coral"],
            edge=CAT["coral"],
            lw=0.7,
            radius=0.25,
            zorder=2.0,
        )
        arrow(
            canvas,
            cx0 + chip * 1.6,
            cy,
            x + w * 0.66,
            y + h * 0.50,
            colour=CAT["coral"],
            lw=0.7,
            head=2.2,
            zorder=2.1,
        )
    hex_r = min(w, h) * 0.20
    hx, hy = x + w * 0.78, y + h * 0.50
    canvas.ax.add_patch(
        plt.Polygon(
            [
                (hx, hy + hex_r),
                (hx + hex_r * 0.87, hy + hex_r * 0.5),
                (hx + hex_r * 0.87, hy - hex_r * 0.5),
                (hx, hy - hex_r),
                (hx - hex_r * 0.87, hy - hex_r * 0.5),
                (hx - hex_r * 0.87, hy + hex_r * 0.5),
            ],
            closed=True,
            facecolor=CAT["coral"],
            edgecolor=CAT["coral"],
            linewidth=0.7,
            hatch="//",
            zorder=2.3,
        )
    )
    canvas.ax.add_patch(
        plt.Circle((hx, hy), hex_r * 0.26, facecolor=PANEL, edgecolor="none", zorder=2.5)
    )


def question_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """An object that is not yet defined. Nothing is asserted inside it."""
    cx, cy = x + w / 2.0, y + h * 0.50
    r = min(w, h) * 0.30
    canvas.ax.add_patch(
        plt.Circle(
            (cx, cy),
            r,
            facecolor="none",
            edgecolor=CAT["ember"],
            linewidth=0.9,
            linestyle=(0, (2.4, 2.0)),
            zorder=2.0,
        )
    )
    for a in (0, 90, 180, 270):
        rad = math.radians(a)
        canvas.ax.plot(
            [cx + math.cos(rad) * r * 1.22, cx + math.cos(rad) * r * 1.60],
            [cy + math.sin(rad) * r * 1.22, cy + math.sin(rad) * r * 1.60],
            color=CAT["ember"],
            linewidth=0.8,
            linestyle=(0, (2.0, 1.6)),
            zorder=2.0,
        )
    d = r * 0.52
    canvas.ax.add_patch(
        plt.Polygon(
            [(cx, cy + d), (cx + d, cy), (cx, cy - d), (cx - d, cy)],
            closed=True,
            facecolor="none",
            edgecolor=CAT["ember"],
            linewidth=1.2,
            zorder=2.3,
        )
    )


def future_form(canvas: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Tiles that are planned and not yet built."""
    tile = min(w, h) * 0.22
    ox = x + w * 0.06
    oy = y + h * 0.50 - tile * 0.5
    for i in range(3):
        rounded_box(
            canvas,
            ox + i * (tile * 1.35),
            oy,
            tile,
            tile,
            face="none",
            edge=CAT["slate"],
            lw=0.7,
            linestyle=(0, (1.8, 1.6)),
            radius=0.25,
            zorder=2.0,
        )
    arrow(
        canvas,
        ox + 3 * (tile * 1.35) - tile * 0.2,
        oy + tile / 2.0,
        ox + 3 * (tile * 1.35) + tile * 0.55,
        oy + tile / 2.0,
        colour=CAT["slate"],
        lw=0.8,
        head=2.4,
        zorder=2.1,
    )
    rounded_box(
        canvas,
        ox + 3 * (tile * 1.35) + tile * 0.75,
        oy,
        tile * 1.25,
        tile,
        face="none",
        edge=CAT["slate"],
        lw=0.7,
        linestyle=(0, (1.8, 1.6)),
        radius=0.25,
        zorder=2.0,
    )


FORMS = {
    "teal": fact_form,
    "coral": decision_form,
    "ember": question_form,
    "slate": future_form,
}


# ---------------------------------------------------------------- build
def build() -> Canvas:
    canvas = Canvas(WIDTH_IN, HEIGHT_IN)
    top = canvas.top

    for (letter, name, colour), cx in zip(CLASSES, CARD_X, strict=True):
        panel_letter(canvas, cx, top - 1.8, letter, rule_to=cx + CARD_W - 0.5)
        settled = colour in ("teal", "coral")
        rounded_box(
            canvas,
            cx,
            CARD_Y,
            CARD_W,
            CARD_H,
            face=FILL[colour],
            edge=CAT[colour],
            lw=0.9,
            radius=0.7,
            zorder=1.0,
            linestyle="solid" if settled else (0, (2.6, 2.2)),
        )
        canvas.ax.add_patch(
            plt.Rectangle(
                (cx + 0.4, CARD_Y + CARD_H - STRIP_H),
                CARD_W - 0.8,
                STRIP_H - 0.4,
                facecolor=CAT[colour],
                edgecolor="none",
                zorder=1.4,
            )
        )
        label(
            canvas,
            cx + CARD_W / 2.0,
            CARD_Y + CARD_H - STRIP_H / 2.0 - 0.2,
            name,
            size=8.4,
            colour=PANEL,
            weight="bold",
            ha="center",
            va="center",
            zorder=2.0,
        )
        FORMS[colour](
            canvas,
            cx + 0.9,
            CARD_Y + 0.6,
            CARD_W - 1.8,
            CARD_H - STRIP_H - 1.2,
        )

    # the band that groups them
    band_y = 1.5
    band_h = 6.0
    for x0, x1, text, dashed in (
        (CARD_X[0], CARD_X[1] + CARD_W, "asserted", False),
        (CARD_X[2], CARD_X[3] + CARD_W, "not asserted", True),
    ):
        rounded_box(
            canvas,
            x0,
            band_y,
            x1 - x0,
            band_h,
            face=CAT["slate"] if not dashed else "none",
            edge=CAT["slate"],
            lw=0.9,
            radius=0.5,
            zorder=1.0,
            linestyle="solid" if not dashed else (0, (2.6, 2.2)),
        )
        label(
            canvas,
            (x0 + x1) / 2.0,
            band_y + band_h / 2.0,
            text,
            size=8.0,
            colour=PANEL if not dashed else CAT["slate"],
            weight="bold",
            ha="center",
            va="center",
            zorder=2.0,
        )
        for cx in (x0, x1 - CARD_W):
            arrow(
                canvas,
                cx + CARD_W / 2.0,
                CARD_Y,
                cx + CARD_W / 2.0,
                band_y + band_h,
                colour=CAT["slate"],
                lw=0.7,
                head=2.4,
                zorder=1.8,
            )
    return canvas


def main() -> tuple[Path, Path]:
    canvas = build()
    return canvas.save(OUT_DIR, STEM)


if __name__ == "__main__":
    main()
