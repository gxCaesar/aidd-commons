"""Shared drawing rules for the AIDD Commons report figures.

Every data plot in this directory is drawn through this module so that the set
reads as one system. The rules it enforces are the project's own figure
standard, not a personal preference.

Colour comes from `atlas_palette`, which is the single Python source of truth
for the palette and which was measured against the house colour-vision gates by
`report/figures/measure_palette.py`. Nothing here re-implements colour science
and nothing here re-derives a colour: this module only decides which measured
colour carries which category and which second channel travels with it.

The second channel is mandatory. A category is never carried by colour alone.
Bars, stacked bars, filled areas and heatmap cells carry a hatch drawn in the
edge colour, so `edgecolor` is always passed; lines and scatter carry a marker
plus a distinct linestyle. The hatch cycle below is longer than the palette's
four-entry categorical hatch map because some figures carry more categories
than the palette has colours; when a chart has more categories than colours,
the colour is cycled and the hatch advances, so no two categories ever share
both channels at once.

Geometry is authored, never repaired. Every figure is created at its final size
with explicit margins, and nothing is saved with `bbox_inches="tight"`, because
a tight bounding box couples canvas size to font size and cancels any change
made to the type. The saved canvas is exactly the authored canvas.

Type is Arial everywhere, including inside math. `mathtext` carries its own
font stack and ignores `font.sans-serif`, so `mathtext.fontset` is set to
`custom` with the four math faces pointed at Arial explicitly. PDF output uses
`pdf.fonttype: 42`, which embeds real TrueType outlines so the Arial in a
label is the Arial a reader sees. That setting is the one AAAI forbids for its
own submissions, because it emits an Identity-H encoding; these figures belong
to the project's living report and website, not to an AAAI paper, and the
alternative, Type 3, turns text into drawing procedures. `report/figures` ships
the PDF and the PNG side by side, so the PNG is the site copy and the PDF is the
archival one.

Output is deterministic. There is no timestamp in any artefact, the PDF
creation date is suppressed, and the SVG hash salt is fixed, so two runs of the
same script produce byte-identical files. Captions are collected in
`report/figures/out/captions.json`, written with sorted keys so that the file
does not depend on the order in which the plots were run.

Every value a figure draws is read from a committed artefact by the script that
draws it. This module never carries a data value.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.figure import Figure

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import atlas_palette  # noqa: E402  (the module sits next to this script)

__all__ = [
    "BAR_HATCHES",
    "DATA_DIR",
    "FIGURE_HEIGHT",
    "FIGURE_WIDTH",
    "OUT_DIR",
    "PNG_DPI",
    "THEME",
    "apply_style",
    "bar_labels",
    "categorical",
    "tokens",
    "figure",
    "fill_colours",
    "hatch_for_index",
    "ladder_colours",
    "ladder_steps",
    "load_json",
    "markers",
    "dashes",
    "register_caption",
    "save",
    "second_channel",
    "title",
]

# ---------------------------------------------------------------- the canvas

REPO_ROOT = _HERE.parents[1]
DATA_DIR = REPO_ROOT / "site" / "public" / "data"
OUT_DIR = _HERE / "out"

#: The report's text width in inches. Every figure is authored at this width.
FIGURE_WIDTH = 7.0
#: The default figure height in inches. A figure that needs a different height
#: passes one; nothing is ever rescaled after the fact.
FIGURE_HEIGHT = 4.6
#: Resolution of the PNG that the site embeds.
PNG_DPI = 300
#: The theme every figure in this set is drawn in. The palette module carries
#: both themes; the report is a light document, so the light theme is the one
#: the figures are authored in.
THEME = "light"

#: The font stack, in the documented order. Arial first, then the two
#: substitutes that carry the same metrics closely enough to keep a layout
#: intact on a machine without Arial.
FONT_STACK = ["Arial", "Helvetica", "DejaVu Sans"]
#: The face used inside mathtext, which has its own stack and ignores the
#: sans-serif list entirely.
MATH_FONT = "Arial"

#: Hatch patterns for a chart that carries more categories than the palette has
#: colours, in the order they are handed out. Every pattern is visible, so a
#: category is never carried by an empty hatch. A chart with four categories or
#: fewer uses the palette's own per-key hatch map instead of this cycle.
BAR_HATCHES = ["//", "xx", "\\\\", "++", "oo", "..", "||", "--", "//x", "\\\\x"]

#: Index sets into the ordered ladder, chosen per number of levels. The wash at
#: index 0 is the low end of a scale rather than a mark that has to be read on
#: its own, so it is only used when five levels are needed and the lowest bin
#: is the wash itself.
_LADDER_INDEX: dict[int, tuple[int, ...]] = {
    2: (1, 4),
    3: (1, 2, 4),
    4: (1, 2, 3, 4),
    5: (0, 1, 2, 3, 4),
}


# ---------------------------------------------------------------- the style

def apply_style(theme: str = THEME) -> dict[str, Any]:
    """Set the rcParams every figure in this set draws under.

    Returns the theme's palette so a script can take its colours from one call.
    """
    tokens = atlas_palette.tokens(theme)
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": list(FONT_STACK),
            "font.size": 9.0,
            "axes.labelsize": 9.0,
            "axes.titlesize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "legend.frameon": False,
            "axes.facecolor": tokens["panel"],
            "figure.facecolor": tokens["panel"],
            "savefig.facecolor": tokens["panel"],
            "axes.edgecolor": tokens["rule"],
            "axes.labelcolor": tokens["ink"],
            "text.color": tokens["ink"],
            "xtick.color": tokens["muted"],
            "ytick.color": tokens["muted"],
            "grid.color": tokens["rule"],
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "mathtext.fontset": "custom",
            "mathtext.rm": MATH_FONT,
            "mathtext.it": f"{MATH_FONT}:italic",
            "mathtext.bf": f"{MATH_FONT}:bold",
            "mathtext.sf": MATH_FONT,
            "pdf.fonttype": 42,
            "svg.hashsalt": "aidd-commons-report-figures",
            "savefig.bbox": None,
            "savefig.pad_inches": 0,
            "hatch.linewidth": 0.6,
            "lines.solid_capstyle": "round",
            "figure.autolayout": False,
        }
    )
    return atlas_palette.palette(theme)


# ---------------------------------------------------------------- the colours

def categorical(theme: str = THEME) -> dict[str, str]:
    """The measured categorical set for one theme."""
    return atlas_palette.categorical(theme)


def tokens(theme: str = THEME) -> dict[str, str]:
    """The nine pinned site tokens for one theme."""
    return atlas_palette.tokens(theme)


def fill_colours(theme: str = THEME) -> dict[str, str]:
    """The pale washes for bar interiors."""
    return atlas_palette.fills(theme)


def markers(theme: str = THEME) -> dict[str, str]:
    """The marker shape per categorical key."""
    return dict(atlas_palette.MARKER)


def dashes(theme: str = THEME) -> dict[str, object]:
    """The linestyle per categorical key."""
    return dict(atlas_palette.DASH)


def second_channel(theme: str = THEME) -> dict[str, dict[str, object]]:
    """The marker, hatch and dash mapping for one theme."""
    return atlas_palette.second_channel()


def ladder_colours(theme: str = THEME) -> list[str]:
    """The ordered ladder for one theme, low to high."""
    return atlas_palette.ladder(theme)


def ladder_steps(theme: str, count: int) -> list[str]:
    """Pick `count` steps from the ordered ladder, evenly spread.

    The ladder is the house channel for data with a direction, so an ordered
    quantity takes it and a nominal one does not. Index 0 is the wash nearest
    the panel, which is the low end of a scale rather than a mark that has to
    be read on its own, so it enters only when five levels are wanted.
    """
    if count not in _LADDER_INDEX:
        raise ValueError(f"no ladder selection for {count} levels")
    steps = atlas_palette.ladder(theme)
    return [steps[index] for index in _LADDER_INDEX[count]]


def hatch_for_index(index: int) -> str:
    """The hatch for the category at `index` in a chart with many categories."""
    return BAR_HATCHES[index % len(BAR_HATCHES)]


# ---------------------------------------------------------------- the canvas

def figure(width: float = FIGURE_WIDTH, height: float = FIGURE_HEIGHT) -> Figure:
    """A blank figure at its authored size."""
    return plt.figure(figsize=(width, height))


def axes_grid(
    fig: Figure,
    rows: int,
    cols: int = 1,
    *,
    left: float = 0.09,
    right: float = 0.985,
    bottom: float = 0.11,
    top: float = 0.93,
    wspace: float = 0.28,
    hspace: float = 0.42,
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
) -> list[Axes]:
    """Add a grid of axes with explicit margins.

    Nothing here is automatic. A layout that does not fit is cut, never scaled.
    """
    grid = fig.add_gridspec(
        rows,
        cols,
        width_ratios=list(width_ratios) if width_ratios else None,
        height_ratios=list(height_ratios) if height_ratios else None,
        left=left,
        right=right,
        bottom=bottom,
        top=top,
        wspace=wspace,
        hspace=hspace,
    )
    axes = [[fig.add_subplot(grid[row, col]) for col in range(cols)] for row in range(rows)]
    return [axes[row][col] for row in range(rows) for col in range(cols)]


def title(ax: Axes, text: str) -> None:
    """A panel title, which is a label and never a sentence."""
    ax.set_title(text, loc="left", fontweight="bold", color=atlas_palette.tokens(THEME)["ink"])


# ---------------------------------------------------------------- the labels

def bar_labels(
    ax: Axes,
    container: BarContainer,
    values: Sequence[float],
    *,
    orientation: str = "vertical",
    fmt: str = "{:g}",
    pad: float = 3.0,
    fontsize: float | None = None,
) -> None:
    """Write each bar's own value at the end of its bar."""
    ink = atlas_palette.tokens(THEME)["ink"]
    for bar, value in zip(container, values, strict=True):
        if orientation == "horizontal":
            anchor = (bar.get_width(), bar.get_y() + bar.get_height() / 2)
            offset = (pad, 0)
            align = {"ha": "left", "va": "center"}
        elif orientation == "vertical":
            anchor = (bar.get_x() + bar.get_width() / 2, bar.get_height())
            offset = (0, pad)
            align = {"ha": "center", "va": "bottom"}
        else:
            raise ValueError(f"unknown orientation {orientation!r}")
        ax.annotate(
            fmt.format(value),
            xy=anchor,
            xytext=offset,
            textcoords="offset points",
            fontsize=fontsize,
            color=ink,
            **align,
        )


# ---------------------------------------------------------------- the outputs

def save(fig: Figure, stem: str, theme: str = THEME) -> dict[str, Path]:
    """Write the vector PDF and the site PNG for a finished figure.

    The canvas is the authored canvas. `savefig.bbox` is pinned to None inside
    the context because `savefig(bbox_inches=None)` reads as "argument not
    given" and falls back to the rcParam, which is the trap this closes.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT_DIR / f"{stem}.pdf"
    png_path = OUT_DIR / f"{stem}.png"
    with mpl.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0}):
        fig.savefig(
            pdf_path,
            format="pdf",
            metadata={"CreationDate": None, "Producer": "AIDD Commons report figures"},
        )
        fig.savefig(
            png_path,
            format="png",
            dpi=PNG_DPI,
            metadata={"Software": "AIDD Commons report figures"},
        )
    plt.close(fig)
    return {"pdf": pdf_path, "png": png_path}


def register_caption(number: int, text: str) -> Path:
    """Add one caption fragment to the shared caption file.

    The file is written with sorted keys and a fixed indent, so it does not
    depend on the order in which the plots happened to run.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "captions.json"
    payload: dict[str, str] = {}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    payload[str(number)] = text
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------- the inputs

def load_json(path: Path) -> Any:
    """Read a committed artefact."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path: Path) -> Any:
    """Read a committed YAML artefact."""
    import yaml

    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def english_list(items: Sequence[str]) -> str:
    """A list written the way a sentence writes one."""
    words = list(items)
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


def iter_chunks(items: Iterable[Any], size: int) -> Iterable[list[Any]]:
    """Split a sequence into fixed-size chunks."""
    chunk: list[Any] = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
