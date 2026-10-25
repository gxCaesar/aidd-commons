"""Shared drawing vocabulary for the AIDD Commons schematics.

Every schematic in `report/figures/schematic_*.py` draws through this module so that the
whole figure set speaks one visual language. The module owns four things and nothing else.

**Colour.** The palette is not chosen here. It is read from `report/figures/atlas_palette.py`,
which is the project's measured source of truth and is the only place the site's teal and coral
identity is turned into a categorical set, an ordered ladder and a pale wash. This module does
no colour science of its own, imports no plotting theme library, and never invents a hex value.
The measured distances live in `report/figures/out/palette-cvd.json`.

**Shape.** The house reference teaches a vocabulary by repetition: the same shapes recur in every
panel so that a reader learns them once. The vocabulary is deliberately small. A *card* is a
rounded rectangle and stands for one unit of content. A *sheet* is a rectangle with ruled lines
and stands for a document. A *grid* is a field of small cells and stands for a table or a
registry. A *node* is a rounded rectangle in a graph and stands for one lesson or one path. A
*funnel* is a symmetric taper and stands for a narrowing decision. A *chip* is a small pill and
stands for an identifier or a label. A *gate* is a chevron and stands for a check that either
passes or stops.

**Text.** Panel letters, two-to-four-word labels and axis names, and nothing else. The argument
belongs in the caption, where a reader looks for it. `check_ink.py` reports the word count of
every figure this module draws, and a figure that has to explain itself in prose has failed to
get a physical form.

**Geometry.** Every figure is authored at its final size in inches, with no `bbox_inches="tight"`
and no rescaling afterwards, so the source point size is the rendered point size. The canvas is
laid out in *units*, where one unit is one hundredth of the figure width in both directions, so a
shape measures the same on the page whichever direction it is drawn along.

Output is deterministic. `SOURCE_DATE_EPOCH` is pinned so the PDF carries no wall-clock date, the
SVG carries no creation date, and the SVG element ids are salted, so two runs of the same script
produce byte-identical files.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

import matplotlib

matplotlib.use("Agg")

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from atlas_palette import palette as _palette  # noqa: E402

__all__ = [
    "CAT",
    "FILL",
    "HATCH",
    "INK",
    "LADDER",
    "MUTED",
    "PANEL",
    "RULE",
    "Canvas",
    "arrow",
    "card",
    "chip",
    "funnel",
    "grid_cells",
    "house_rc",
    "label",
    "node_box",
    "panel_letter",
    "rounded_box",
    "save_pair",
    "sheet",
    "text_width",
]


# ---------------------------------------------------------------- palette access
# Read once, from the project's own measured module. Nothing here re-implements colour science.
_PALETTE = _palette("light")
TOKENS: dict[str, str] = _PALETTE["tokens"]  # type: ignore[assignment]
CAT: dict[str, str] = _PALETTE["categorical"]  # type: ignore[assignment]
FILL: dict[str, str] = _PALETTE["fills"]  # type: ignore[assignment]
LADDER: list[str] = _PALETTE["ladder"]  # type: ignore[assignment]
HATCH: dict[str, str] = _PALETTE["second_channel"]["hatch"]  # type: ignore[index]
MARKER: dict[str, str] = _PALETTE["second_channel"]["marker"]  # type: ignore[index]
DASH: dict[str, object] = _PALETTE["second_channel"]["dash"]  # type: ignore[index]

PANEL: str = TOKENS["panel"]
INK: str = TOKENS["ink"]
MUTED: str = TOKENS["muted"]
RULE: str = TOKENS["rule"]


# ---------------------------------------------------------------- typography
FONT_STACK = ["Arial", "Helvetica", "DejaVu Sans"]

LABEL_PT = 7.6
TINY_PT = 6.6
TITLE_PT = 8.6
PANEL_PT = 9.0


def house_rc() -> dict[str, object]:
    """The rcParams every schematic is drawn under.

    Arial is the first entry of the stack and the documented fallbacks follow it. Mathtext gets
    its own custom Arial set, because mathtext ignores `font.sans-serif` entirely and would
    otherwise render any formula in DejaVu.
    """
    return {
        "font.family": "sans-serif",
        "font.sans-serif": FONT_STACK,
        "font.size": LABEL_PT,
        "mathtext.fontset": "custom",
        "mathtext.rm": "Arial",
        "mathtext.it": "Arial:italic",
        "mathtext.bf": "Arial:bold",
        "mathtext.sf": "Arial",
        "axes.linewidth": 0.6,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "svg.hashsalt": "aidd-commons-schematics",
        "pdf.fonttype": 42,
        "pdf.compression": 6,
        "savefig.bbox": None,
        "savefig.pad_inches": 0.0,
        "figure.facecolor": PANEL,
        "savefig.facecolor": PANEL,
        "path.simplify": False,
        "hatch.linewidth": 0.5,
        "agg.path.chunksize": 0,
    }


# The house style applies to everything this module draws, so it is installed once at import.
matplotlib.rcParams.update(house_rc())


# ---------------------------------------------------------------- canvas
class Canvas:
    """A figure authored at its final size.

    `width_in` and `height_in` are the printed inches. The axes cover the whole figure, and the
    data limits run from 0 to 100 across the width and 0 to `100 * height_in / width_in` up the
    height, so one data unit is one hundredth of the figure width in both directions.
    """

    def __init__(self, width_in: float, height_in: float) -> None:
        self.width_in = width_in
        self.height_in = height_in
        self.fig = plt.figure(figsize=(width_in, height_in), dpi=200)
        self.ax = self.fig.add_axes([0.0, 0.0, 1.0, 1.0])
        self.ax.set_xlim(0.0, 100.0)
        self.ax.set_ylim(0.0, 100.0 * height_in / width_in)
        self.ax.set_axis_off()
        self.ax.set_facecolor(PANEL)
        self.ax.set_rasterization_zorder(0)

    @property
    def top(self) -> float:
        return self.ax.get_ylim()[1]

    @property
    def unit_in(self) -> float:
        return self.width_in / 100.0

    def px(self, value: float) -> float:
        """Convert data units to points."""
        return value * self.unit_in * 72.0

    def draw(self) -> None:
        self.fig.canvas.draw()

    def save(self, out_dir: Path, stem: str) -> tuple[Path, Path]:
        return save_pair(self.fig, out_dir, stem)


def text_width(canvas: Canvas, content: str, size: float, weight: str = "normal") -> float:
    """The rendered width of a string, in data units."""
    renderer = canvas.fig.canvas.get_renderer()
    prop = font_manager.FontProperties(family=FONT_STACK, size=size, weight=weight)
    width_px, _, _ = renderer.get_text_width_height_descent(content, prop, ismath=False)
    bbox = canvas.ax.get_window_extent(renderer=renderer)
    return width_px / bbox.width * 100.0


# ---------------------------------------------------------------- primitives
def rounded_box(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    face: str = "none",
    edge: str = INK,
    lw: float = 0.7,
    hatch: str | None = None,
    radius: float = 0.9,
    zorder: float = 1.0,
    linestyle: str = "solid",
    alpha: float = 1.0,
) -> FancyBboxPatch:
    """A card. The workhorse shape of the whole figure set."""
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=face,
        edgecolor=edge,
        linewidth=lw,
        linestyle=linestyle,
        hatch=hatch,
        zorder=zorder,
        alpha=alpha,
        mutation_aspect=1.0,
    )
    canvas.ax.add_patch(patch)
    return patch


def card(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    colour: str,
    filled: bool = False,
    hatch: str | None = None,
    lw: float = 0.7,
    zorder: float = 1.0,
    linestyle: str = "solid",
    radius: float = 0.9,
) -> FancyBboxPatch:
    """A card carrying one categorical colour, with the palette's own second channel."""
    return rounded_box(
        canvas,
        x,
        y,
        w,
        h,
        face=CAT[colour] if filled else FILL[colour],
        edge=CAT[colour],
        lw=lw,
        hatch=hatch if hatch is not None else HATCH[colour],
        radius=radius,
        zorder=zorder,
        linestyle=linestyle,
    )


def sheet(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    colour: str,
    lines: int = 5,
    lw: float = 0.7,
    zorder: float = 1.0,
) -> None:
    """A document. Ruled lines stand for text that the figure does not need to quote."""
    rounded_box(
        canvas, x, y, w, h, face=PANEL, edge=CAT[colour], lw=lw, radius=0.5, zorder=zorder
    )
    pad = min(1.0, w * 0.12)
    top = y + h - pad * 1.4
    step = (h - pad * 2.6) / max(1, lines)
    for i in range(lines):
        thickness = step * 0.30
        inset = 0.0 if i % 3 else w * 0.22
        canvas.ax.add_patch(
            Rectangle(
                (x + pad + inset, top - (i + 1) * step),
                w - 2 * pad - inset,
                thickness,
                facecolor=CAT[colour],
                edgecolor="none",
                alpha=0.85,
                zorder=zorder + 0.1,
            )
        )


def grid_cells(
    canvas: Canvas,
    x: float,
    y: float,
    cols: int,
    rows: int,
    *,
    cw: float,
    ch: float,
    gap: float,
    colour: str,
    highlight: tuple[int, int] | None = None,
    filled: bool = False,
    lw: float = 0.55,
    zorder: float = 1.0,
) -> None:
    """A registry. A grid of coloured cells with a highlighted member."""
    for r in range(rows):
        for c in range(cols):
            is_highlight = highlight == (r, c)
            rounded_box(
                canvas,
                x + c * (cw + gap),
                y + r * (ch + gap),
                cw,
                ch,
                face=CAT[colour] if (is_highlight or filled) else FILL[colour],
                edge=CAT[colour],
                lw=lw,
                hatch=HATCH[colour] if (is_highlight or filled) else None,
                radius=0.35,
                zorder=zorder + (0.05 if is_highlight else 0.0),
            )


def chip(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    content: str = "",
    *,
    face: str = PANEL,
    edge: str = INK,
    lw: float = 0.6,
    size: float = TINY_PT,
    colour: str = INK,
    weight: str = "normal",
    zorder: float = 2.0,
    hatch: str | None = None,
    pad: float = 0.0,
) -> None:
    """A pill. Carries an identifier or a short label."""
    rounded_box(
        canvas,
        x,
        y,
        w,
        h,
        face=face,
        edge=edge,
        lw=lw,
        radius=h / 2.0,
        zorder=zorder,
        hatch=hatch,
    )
    if content:
        label(
            canvas,
            x + w / 2.0 + pad,
            y + h / 2.0,
            content,
            size=size,
            colour=colour,
            weight=weight,
            ha="center",
            va="center",
            zorder=zorder + 0.2,
        )


def label(
    canvas: Canvas,
    x: float,
    y: float,
    content: str,
    *,
    size: float = LABEL_PT,
    colour: str = INK,
    weight: str = "normal",
    ha: str = "left",
    va: str = "bottom",
    zorder: float = 3.0,
    linespacing: float = 1.15,
    rotation: float = 0.0,
    style: str = "normal",
) -> None:
    canvas.ax.text(
        x,
        y,
        content,
        fontsize=size,
        color=colour,
        fontweight=weight,
        fontstyle=style,
        ha=ha,
        va=va,
        zorder=zorder,
        linespacing=linespacing,
        rotation=rotation,
    )


def panel_letter(
    canvas: Canvas,
    x: float,
    y: float,
    letter: str,
    title: str = "",
    *,
    size: float = PANEL_PT,
    title_size: float = TITLE_PT,
    colour: str = INK,
    title_colour: str = INK,
    rule: bool = True,
    rule_to: float = 98.5,
) -> None:
    """A panel letter with an optional short title, above the subfigure, left aligned.

    A hairline rule runs from the end of the title to the right margin. It is not decoration. A
    row that carries nothing but the title would otherwise be a fully blank band once the words
    are masked out, and the rule keeps the figure free of one.
    """
    label(canvas, x, y, f"({letter})", size=size, colour=colour, weight="bold", va="baseline")
    offset = text_width(canvas, f"({letter})", size, "bold") + 1.5
    title_w = 0.0
    if title:
        label(canvas, x + offset, y, title, size=title_size, colour=title_colour, va="baseline")
        title_w = text_width(canvas, title, title_size, "normal")
    if rule:
        y_rule = y + title_size * 100.0 / (canvas.width_in * 72.0) * 0.32
        canvas.ax.plot(
            [x + offset + title_w + 1.2, rule_to],
            [y_rule, y_rule],
            color=RULE,
            linewidth=0.5,
            solid_capstyle="butt",
            zorder=0.8,
        )


def arrow(
    canvas: Canvas,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    colour: str = MUTED,
    lw: float = 0.8,
    style: str = "-|>",
    head: float = 3.0,
    zorder: float = 2.0,
    connectionstyle: str = "arc3",
    rad: float = 0.0,
    zorder_arrow: float | None = None,
) -> FancyArrowPatch:
    patch = FancyArrowPatch(
        (x0, y0),
        (x1, y1),
        arrowstyle=style,
        mutation_scale=canvas.px(head) * 0.9,
        linewidth=lw,
        color=colour,
        zorder=zorder_arrow if zorder_arrow is not None else zorder,
        connectionstyle=connectionstyle,
        shrinkA=0.0,
        shrinkB=0.0,
        joinstyle="miter",
        capstyle="butt",
    )
    if rad:
        patch.set_connectionstyle(connectionstyle, rad=rad)
    canvas.ax.add_patch(patch)
    return patch


def node_box(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    content: str,
    *,
    colour: str,
    filled: bool = False,
    size: float = TINY_PT,
    zorder: float = 2.0,
    lw: float = 0.7,
    radius: float = 0.9,
    weight: str = "normal",
    edge: str | None = None,
    linestyle: str = "solid",
    hatch: str | None = None,
) -> None:
    """A graph node with its label inside."""
    rounded_box(
        canvas,
        x,
        y,
        w,
        h,
        face=CAT[colour] if filled else FILL[colour],
        edge=edge if edge is not None else CAT[colour],
        lw=lw,
        radius=radius,
        zorder=zorder,
        linestyle=linestyle,
        hatch=hatch if hatch is not None else (HATCH[colour] if filled else None),
    )
    label(
        canvas,
        x + w / 2.0,
        y + h / 2.0,
        content,
        size=size,
        colour=PANEL if filled else INK,
        weight=weight,
        ha="center",
        va="center",
        zorder=zorder + 0.2,
        linespacing=1.1,
    )


def funnel(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    colour: str,
    lw: float = 0.7,
    zorder: float = 1.5,
    taper: float = 0.42,
) -> None:
    """A narrowing step. The waist is the attrition."""
    half_top = w / 2.0
    half_bot = w * taper / 2.0
    verts = [
        (x - half_top, y + h),
        (x + half_top, y + h),
        (x + half_bot, y),
        (x - half_bot, y),
    ]
    patch = Polygon(
        verts,
        closed=True,
        facecolor=FILL[colour],
        edgecolor=CAT[colour],
        linewidth=lw,
        hatch=HATCH[colour],
        zorder=zorder,
        joinstyle="miter",
    )
    canvas.ax.add_patch(patch)


def save_pair(fig, out_dir: Path, stem: str) -> tuple[Path, Path]:
    """Write the vector pair. Deterministic: no clock, no salted ids."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"{stem}.pdf"
    svg_path = out_dir / f"{stem}.svg"
    with plt.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0.0}):
        fig.savefig(pdf_path, format="pdf")
        fig.savefig(svg_path, format="svg", metadata={"Date": None})
    return pdf_path, svg_path


def separator(canvas: Canvas, y: float, x0: float = 1.5, x1: float = 98.5) -> None:
    """A dashed rule between panels. It also breaks any long blank band."""
    canvas.ax.plot(
        [x0, x1],
        [y, y],
        color=RULE,
        linewidth=0.7,
        linestyle=(0, (2.4, 2.0)),
        zorder=0.6,
    )
