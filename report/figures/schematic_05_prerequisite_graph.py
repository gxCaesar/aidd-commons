"""Figure 5. Prerequisite graph over the six learning paths.

`catalog/curriculum/tracks.yaml` defines six ordered learning paths and, for each of them, the
lessons a reader is expected to have met first. The catalogue's own data is the only source for
this figure. Ten distinct lessons are named as a prerequisite somewhere, and twenty-one
prerequisite relations connect them to the five specialist routes. The core route names no
prerequisite at all, but eight of the ten shared lessons appear in its own lesson list, which is
why it is drawn as the spine rather than as a sixth leaf.

The drawing is a bipartite node-link graph. The ten lessons sit on the left, each carrying a
badge with the number of routes that require it, so the hub is visible without reading the
edges. The six routes sit on the right, each carrying a badge with the number of lessons the
route lists. A solid edge is a prerequisite the catalogue states. A dashed edge is a lesson that
the core route also lists, which is a different relation and is drawn as a different relation.

The badge numbers are counts taken directly from the catalogue. They are not rates, not
difficulty and not coverage.
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
STEM = "schematic-05-prerequisite-graph"

WIDTH_IN = 6.38
HEIGHT_IN = 4.10

# Lesson nodes, ordered so that routes which share a lesson sit next to each other.
# (title, number of routes that require it, routes that require it, listed in the core route)
LESSONS = [
    ("Evidence claim boundaries", 5, ["sm", "sp", "bi", "tc", "af"], True),
    ("Therapeutic decision framing", 3, ["sm", "bi", "tc"], True),
    ("Biological representations", 3, ["sp", "bi", "tc"], True),
    ("Licence and permitted use", 2, ["sp", "bi"], True),
    ("Docking score and rescoring", 1, ["bi"], True),
    ("Model table construction", 2, ["sm", "af"], True),
    ("Ridge fitting and validation", 2, ["sm", "af"], True),
    ("Metric estimand and uncertainty", 1, ["sm"], False),
    ("Regression and classification errors", 1, ["sp"], True),
    ("Ranking and decision thresholds", 1, ["af"], False),
]

# Route nodes, in the order that keeps the crossings down.
ROUTES = [
    ("core", "Core route", 25),
    ("sm", "Small molecules", 29),
    ("tc", "Targets and cells", 16),
    ("bi", "Biologics", 15),
    ("sp", "Structure and physics", 12),
    ("af", "Agents and feedback", 12),
]

LESSON_X = 1.5
LESSON_W = 32.0
LESSON_H = 4.4
LESSON_TOP = 60.8
LESSON_PITCH = 5.4

ROUTE_X = 62.0
ROUTE_W = 27.0
ROUTE_H = 5.2
ROUTE_TOP = 51.4
ROUTE_PITCH = 8.6

EDGE_COLOUR = CAT["teal"]
SPINE_COLOUR = CAT["slate"]


def badge(canvas: Canvas, cx: float, cy: float, value: int, colour: str) -> None:
    r = 1.55
    canvas.ax.add_patch(
        plt.Circle((cx, cy), r, facecolor=colour, edgecolor=colour, linewidth=0.6, zorder=3.0)
    )
    label(
        canvas,
        cx,
        cy,
        str(value),
        size=6.0,
        colour=PANEL,
        weight="bold",
        ha="center",
        va="center",
        zorder=3.2,
    )


def build() -> Canvas:
    canvas = Canvas(WIDTH_IN, HEIGHT_IN)
    top = canvas.top

    panel_letter(canvas, 1.5, top - 2.4, "a", "Prerequisite graph")

    lesson_y: dict[str, tuple[float, float]] = {}
    for i, (title, count, _routes, _in_core) in enumerate(LESSONS):
        y = LESSON_TOP - LESSON_H - i * LESSON_PITCH
        cy = y + LESSON_H / 2.0
        lesson_y[title] = (y, cy)
        rounded_box(
            canvas,
            LESSON_X,
            y,
            LESSON_W,
            LESSON_H,
            face=FILL["teal"],
            edge=CAT["teal"],
            lw=0.7,
            radius=0.5,
            zorder=2.0,
        )
        label(
            canvas,
            LESSON_X + 4.3,
            cy,
            title,
            size=6.2,
            colour=INK,
            ha="left",
            va="center",
            zorder=2.4,
            linespacing=1.1,
        )
        badge(canvas, LESSON_X + 1.9, cy, count, EDGE_COLOUR)

    route_y: dict[str, tuple[float, float]] = {}
    for i, (key, name, count) in enumerate(ROUTES):
        y = ROUTE_TOP - ROUTE_H - i * ROUTE_PITCH
        cy = y + ROUTE_H / 2.0
        route_y[key] = (y, cy)
        is_core = key == "core"
        rounded_box(
            canvas,
            ROUTE_X,
            y,
            ROUTE_W,
            ROUTE_H,
            face=FILL["slate"] if is_core else FILL["ember"],
            edge=CAT["slate"] if is_core else CAT["ember"],
            lw=0.9 if is_core else 0.8,
            radius=0.6,
            zorder=2.0,
            hatch="xx" if is_core else None,
        )
        label(
            canvas,
            ROUTE_X + 2.0,
            cy,
            name,
            size=6.8,
            colour=INK,
            weight="bold" if is_core else "normal",
            ha="left",
            va="center",
            zorder=2.4,
        )
        badge(canvas, ROUTE_X + ROUTE_W - 1.6, cy, count, CAT["slate"] if is_core else CAT["ember"])

    # prerequisite relations
    for title, _count, routes, _in_core in LESSONS:
        y, cy = lesson_y[title]
        for key in routes:
            ry, rcy = route_y[key]
            canvas.ax.plot(
                [LESSON_X + LESSON_W, ROUTE_X],
                [cy, rcy],
                color=EDGE_COLOUR,
                linewidth=0.55,
                alpha=0.75,
                zorder=1.0,
                solid_capstyle="round",
            )

    # the core route also lists eight of the shared lessons
    ry, rcy = route_y["core"]
    for title, _count, _routes, in_core in LESSONS:
        if not in_core:
            continue
        y, cy = lesson_y[title]
        canvas.ax.plot(
            [ROUTE_X, LESSON_X + LESSON_W],
            [rcy, cy],
            color=SPINE_COLOUR,
            linewidth=0.5,
            alpha=0.42,
            linestyle=(0, (2.2, 2.0)),
            zorder=0.8,
        )

    # the key
    key_y = 1.6
    canvas.ax.plot(
        [1.5, 8.0],
        [key_y, key_y],
        color=EDGE_COLOUR,
        linewidth=0.8,
        zorder=2.0,
    )
    label(
        canvas,
        9.2,
        key_y,
        "prerequisite",
        size=6.2,
        colour=INK,
        ha="left",
        va="center",
        zorder=2.2,
    )
    canvas.ax.plot(
        [26.0, 32.5],
        [key_y, key_y],
        color=SPINE_COLOUR,
        linewidth=0.7,
        alpha=0.6,
        linestyle=(0, (2.2, 2.0)),
        zorder=2.0,
    )
    label(
        canvas,
        33.7,
        key_y,
        "listed in core route",
        size=6.2,
        colour=INK,
        ha="left",
        va="center",
        zorder=2.2,
    )
    return canvas


def main() -> tuple[Path, Path]:
    canvas = build()
    return canvas.save(OUT_DIR, STEM)


if __name__ == "__main__":
    main()
