"""The site's figure palette, derived from the site's own tokens and measured against the
house colour-vision gates.

The project decided on 2026-10-21 to unify every visual on the teal and coral identity that
the site already carries, in place of the standing seaborn-deep house palette. That decision
changed where the colours come from; it did not change what they have to survive. The gates in
`figset.check_palette` (colour-vision floor, luminance spread, categorical set disjoint from
the ordered ladder, ladder adjacent luminance gap, and a mandatory second channel for every
categorical key) still apply unchanged, and the floor is still 10.0 CIEDE2000 under
deuteranopia and protanopia. This module is the Python source of truth for the palette;
`site/src/data/atlas-palette.json` is its mirror for the site, and
`report/figures/measure_palette.py` is what measures it and writes the evidence to
`report/figures/out/palette-cvd.json`.

The nine site tokens below are copied verbatim from `site/src/styles/global.css` and are not
reinterpreted here. Everything else is derived from them by two operations only: a mix in
sRGB toward white or black, and the token itself unchanged. No colour outside the site's teal,
coral, ink and grey families is introduced, so the palette cannot drift away from the identity
it is meant to carry.

How the categorical set was derived, and why it is shaped the way it is:

The three pinned colours that carry the identity, teal, coral and the focus accent, do not
survive the gates as they stand. Measured by `figset.cvd_report`, teal against the pinned
coral measures 35.7 under deuteranopia, which is comfortable, but the site's own warm pair,
coral against the focus accent, measures 6.06, and the pinned teal against the pinned muted
measures 2.72, because under deuteranopia the red axis collapses onto the yellow axis
and a desaturated blue-grey sits on top of a teal of similar lightness. The house palette
passes because it spans six distinct hues; this identity has two, so lightness and chroma
have to carry the separation that hue cannot.

Each categorical colour is therefore a measured step away from a pinned token:

* the light teal is the pinned teal lightened 20% toward white, because the pinned teal
  measures 4.96:1 on the light panel but only 2.88:1 on the dark panel, and the step that
  clears 3:1 on its own panel also opens the gap against the slate;
* the light coral is the pinned coral, unchanged, and the light ember is that same coral
  darkened 30% toward black, which is the step that separates the two warm colours under
  deuteranopia;
* the light slate is the pinned muted token darkened 7% toward black;
* the dark teal and the dark ember are the pinned dark tokens, unchanged, and the dark coral
  is the pinned dark coral darkened 25% toward black, for the same reason as its light
  counterpart: the two warm colours have to differ in lightness, not only in hue;
* the dark slate is the pinned dark muted token darkened 30% toward black.

The result, measured rather than asserted, is in `report/figures/out/palette-cvd.json`. The
light set clears the floor at 15.21 under deuteranopia and 14.03 under protanopia, the dark
set at 13.07 and 14.63, and the worst pair under normal vision is 15.43 and 24.00. The
tritanopia distances are reported in the same file because the house gates do not gate on
them, but a palette that is only legible to dichromats is not a palette.

The ordered ladder is a separate artefact for data with a direction. It is kept in the teal
family, running pale to deep in the light theme and deep to pale in the dark one, and it leans
toward the site's deep ink at its dark end so that no ladder step can be mistaken for a
categorical colour: the smallest CIEDE2000 distance between a ladder step and any categorical
colour is 12.75 in the light theme and 6.08 in the dark theme. The step nearest the panel in
each ladder is a wash by construction, the light ladder's palest at 1.13:1 and the dark
ladder's deepest at 1.96:1; those are the low end of a scale rather than marks that have to be
read on their own, and the categorical set is what carries a mark that does.

The second channel is not optional. Every categorical key carries a marker, a hatch and a
dash, so that a printed figure, a projector and a photocopy still separate the series after
colour has been taken away.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "CATEGORICAL_DARK",
    "CATEGORICAL_LIGHT",
    "CVD_FLOOR",
    "CONTRAST_FLOOR",
    "DASH",
    "FILL_DARK",
    "FILL_LIGHT",
    "HATCH",
    "LADDER_DARK",
    "LADDER_LIGHT",
    "LUMINANCE_BUDGET",
    "MARKER",
    "THEMES",
    "TOKENS_DARK",
    "TOKENS_LIGHT",
    "categorical",
    "dark_palette",
    "fills",
    "ladder",
    "light_palette",
    "palette",
    "second_channel",
    "tokens",
]


# ---------------------------------------------------------------- the nine pinned tokens
# Copied verbatim from site/src/styles/global.css. These are the site's own values and the
# palette is derived from them, not chosen beside them.
TOKENS_LIGHT: Final[dict[str, str]] = {
    "bg": "#fbf8f1",
    "panel": "#fffdf8",
    "ink": "#13283d",
    "muted": "#536675",
    "rule": "#ccd4d3",
    "teal": "#087c78",
    "teal_deep": "#075e5c",
    "coral": "#c85f51",
    "focus": "#e05d44",
}

TOKENS_DARK: Final[dict[str, str]] = {
    "bg": "#10202e",
    "panel": "#172b3b",
    "ink": "#edf3f2",
    "muted": "#b7c6cc",
    "rule": "#3d5665",
    "teal": "#4fc7bf",
    "teal_deep": "#90e4dc",
    "coral": "#fc9a88",
    "focus": "#ffb15b",
}

THEMES: Final[tuple[str, ...]] = ("light", "dark")


# ---------------------------------------------------------------- the derived categorical set
# Four colours, one per role. The roles are the same in both themes so that a chart does not
# have to change its series names when the page changes theme; only the values do.
CATEGORICAL_LIGHT: Final[dict[str, str]] = {
    "teal": "#399693",
    "coral": "#c85f51",
    "ember": "#8c4239",
    "slate": "#4d5f6d",
}

CATEGORICAL_DARK: Final[dict[str, str]] = {
    "teal": "#4fc7bf",
    "coral": "#bd7366",
    "ember": "#ffb15b",
    "slate": "#808b8f",
}


# ---------------------------------------------------------------- the ordered ladder
# For data with a direction. Pale to deep in the light theme, deep to pale in the dark one,
# because the dark end of a ramp has to be the visible end on a dark panel.
LADDER_LIGHT: Final[list[str]] = ["#e6f2f1", "#b5dcda", "#77b9bd", "#35757f", "#123a49"]
LADDER_DARK: Final[list[str]] = ["#2c5c68", "#3f8183", "#5ba39d", "#86c9c3", "#bce8e3"]


# ---------------------------------------------------------------- pale washes for bar interiors
# A wash of the mark colour: 84% toward white in the light theme, 55% toward black in the dark
# one, which keeps the hue instead of drifting toward the panel.
FILL_LIGHT: Final[dict[str, str]] = {
    "teal": "#dfeeee",
    "coral": "#f6e5e3",
    "ember": "#ede1df",
    "slate": "#e3e5e8",
}

FILL_DARK: Final[dict[str, str]] = {
    "teal": "#245a56",
    "coral": "#55342e",
    "ember": "#735029",
    "slate": "#3a3f40",
}


# ---------------------------------------------------------------- the second channel
# Colour alone never carries a category. Every key resolves in all three mappings.
MARKER: Final[dict[str, str]] = {
    "teal": "o",
    "coral": "s",
    "ember": "^",
    "slate": "D",
}

HATCH: Final[dict[str, str]] = {
    "teal": "",
    "coral": "//",
    "ember": "\\\\",
    "slate": "xx",
}

DASH: Final[dict[str, object]] = {
    "teal": "-",
    "coral": "--",
    "ember": ":",
    "slate": (0, (3, 1, 1, 1)),
}


# ---------------------------------------------------------------- the gates
# The house floor, unchanged. Lowering it is not an option that belongs to this module; if a
# future palette cannot clear it, the palette changes.
CVD_FLOOR: Final[float] = 10.0
LUMINANCE_BUDGET: Final[float] = 0.22
CONTRAST_FLOOR: Final[float] = 3.0


def _theme(theme: str) -> str:
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r}; expected one of {THEMES}")
    return theme


def tokens(theme: str) -> dict[str, str]:
    """The nine pinned tokens for one theme."""
    return dict(TOKENS_LIGHT if _theme(theme) == "light" else TOKENS_DARK)


def categorical(theme: str) -> dict[str, str]:
    """The derived categorical set for one theme, in series order."""
    return dict(CATEGORICAL_LIGHT if _theme(theme) == "light" else CATEGORICAL_DARK)


def ladder(theme: str) -> list[str]:
    """The ordered ladder for one theme, low to high."""
    return list(LADDER_LIGHT if _theme(theme) == "light" else LADDER_DARK)


def fills(theme: str) -> dict[str, str]:
    """The pale wash for each categorical key, for bar interiors and container blocks."""
    return dict(FILL_LIGHT if _theme(theme) == "light" else FILL_DARK)


def second_channel() -> dict[str, dict[str, object]]:
    """The marker, hatch and dash mapping for each categorical key."""
    return {"marker": dict(MARKER), "hatch": dict(HATCH), "dash": dict(DASH)}


def palette(theme: str) -> dict[str, object]:
    """Everything one theme needs to draw: tokens, marks, ladder, washes and second channel."""
    name = _theme(theme)
    return {
        "theme": name,
        "tokens": tokens(name),
        "categorical": categorical(name),
        "ladder": ladder(name),
        "fills": fills(name),
        "second_channel": second_channel(),
    }


def light_palette() -> dict[str, object]:
    """The light theme variant."""
    return palette("light")


def dark_palette() -> dict[str, object]:
    """The dark theme variant."""
    return palette("dark")
