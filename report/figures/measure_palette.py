"""Measure the Atlas figure palette and write the evidence to report/figures/out/palette-cvd.json.

Every number this script writes is produced by the house toolkit in
`~/Desktop/skills/single-column-figs/assets/figset.py`, which is loaded from disk rather than
reimplemented here: `simulate_cvd` for the dichromat simulation, `_to_lab` and `_ciede2000` for
the distance, `cvd_report` for the worst pair and the luminance spread, and `check_palette` for
the four gates. The only thing computed here rather than borrowed is the WCAG 2.x contrast
ratio, which the toolkit does not carry.

The gates are the house gates and they are not softened. `figset.CVD_FLOOR` is asserted to be
the same 10.0 the palette module declares, so a future edit that lowers the floor in one place
fails loudly here instead of quietly making the palette look compliant.

Run it from the repository root:

    .venv/bin/python report/figures/measure_palette.py
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import os
import sys
from colorsys import rgb_to_hls
from pathlib import Path
from types import ModuleType
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import atlas_palette  # noqa: E402  (the module sits next to this script)

DEFAULT_TOOLKIT = Path.home() / "Desktop" / "skills" / "single-column-figs" / "assets" / "figset.py"
OUT_PATH = _HERE / "out" / "palette-cvd.json"

VISION_KINDS = ("normal", "deutan", "protan", "tritan")


def load_figset() -> ModuleType:
    """Load the house toolkit from disk."""
    path = Path(os.environ.get("AIDD_FIGSET_PATH", str(DEFAULT_TOOLKIT)))
    if not path.exists():
        raise FileNotFoundError(
            f"the house toolkit is not at {path}; set AIDD_FIGSET_PATH to the figset.py of the "
            "single-column-figs skill"
        )
    spec = importlib.util.spec_from_file_location("figset", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load the house toolkit from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def relative_luminance(hexcolor: str, figset: ModuleType) -> float:
    """WCAG 2.x relative luminance of an sRGB colour."""
    r, g, b = figset.mpl.colors.to_rgb(hexcolor)
    channels = []
    for value in (r, g, b):
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2])


def contrast_ratio(foreground: str, background: str, figset: ModuleType) -> float:
    """WCAG 2.x contrast ratio between two sRGB colours."""
    first = relative_luminance(foreground, figset)
    second = relative_luminance(background, figset)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def measure_theme(figset: ModuleType, theme: str) -> dict[str, Any]:
    """Measure one theme's categorical set, ladder and washes."""
    tokens = atlas_palette.tokens(theme)
    marks = atlas_palette.categorical(theme)
    ladder = atlas_palette.ladder(theme)
    other = "dark" if theme == "light" else "light"
    other_panel = atlas_palette.tokens(other)["panel"]

    pairs: list[dict[str, Any]] = []
    for (name_a, hex_a), (name_b, hex_b) in itertools.combinations(marks.items(), 2):
        distances: dict[str, float] = {}
        for kind in VISION_KINDS:
            lab_a = figset._to_lab(
                figset.simulate_cvd(hex_a, kind)
                if kind != "normal"
                else figset.mpl.colors.to_rgb(hex_a)
            )
            lab_b = figset._to_lab(
                figset.simulate_cvd(hex_b, kind)
                if kind != "normal"
                else figset.mpl.colors.to_rgb(hex_b)
            )
            distances[kind] = float(figset._ciede2000(lab_a, lab_b))
        pairs.append({"a": name_a, "b": name_b, **distances})

    worst: dict[str, dict[str, Any]] = {}
    for kind in VISION_KINDS:
        lowest = min(pairs, key=lambda pair: pair[kind])
        worst[kind] = {
            "distance": round(float(lowest[kind]), 4),
            "pair": f"{lowest['a']}/{lowest['b']}",
        }

    contrast: dict[str, dict[str, Any]] = {}
    for name, hex_value in marks.items():
        contrast[name] = {
            "hex": hex_value,
            "own_panel": round(contrast_ratio(hex_value, tokens["panel"], figset), 4),
            "other_panel": round(contrast_ratio(hex_value, other_panel, figset), 4),
        }
    for name, hex_value in atlas_palette.fills(theme).items():
        contrast[f"fill:{name}"] = {
            "hex": hex_value,
            "own_panel": round(contrast_ratio(hex_value, tokens["panel"], figset), 4),
            "other_panel": round(contrast_ratio(hex_value, other_panel, figset), 4),
        }
    for index, hex_value in enumerate(ladder):
        contrast[f"ladder:{index}"] = {
            "hex": hex_value,
            "own_panel": round(contrast_ratio(hex_value, tokens["panel"], figset), 4),
            "other_panel": round(contrast_ratio(hex_value, other_panel, figset), 4),
        }

    ladder_luminance = [rgb_to_hls(*figset.mpl.colors.to_rgb(step))[1] for step in ladder]
    gaps = [abs(a - b) for a, b in zip(ladder_luminance, ladder_luminance[1:], strict=False)]
    ladder_distance = min(
        float(
            figset._ciede2000(
                figset._to_lab(figset.mpl.colors.to_rgb(step)),
                figset._to_lab(figset.mpl.colors.to_rgb(mark)),
            )
        )
        for step in ladder
        for mark in marks.values()
    )

    report = figset.cvd_report(list(marks.values()), f"{theme} categorical set")
    spread = float(report["luminance_spread"])
    worst_cvd = min(float(report["deutan"]), float(report["protan"]))
    own_panel_contrasts = [
        contrast_ratio(value, tokens["panel"], figset) for value in marks.values()
    ]

    return {
        "theme": theme,
        "panel": tokens["panel"],
        "other_panel": other_panel,
        "categorical": dict(marks),
        "ladder": list(ladder),
        "fills": atlas_palette.fills(theme),
        "pairs": pairs,
        "worst_pair": worst,
        "contrast": contrast,
        "ladder_audit": {
            "adjacent_luminance_gaps": [round(gap, 4) for gap in gaps],
            "min_adjacent_gap": round(min(gaps), 4),
            "disjoint_from_categorical": not set(ladder) & set(marks.values()),
            "min_normal_distance_to_categorical": round(float(ladder_distance), 4),
        },
        "gates": {
            "cvd_floor": atlas_palette.CVD_FLOOR,
            "cvd_worst": round(worst_cvd, 4),
            "cvd_pass": worst_cvd >= atlas_palette.CVD_FLOOR,
            "luminance_spread": round(spread, 4),
            "luminance_budget": atlas_palette.LUMINANCE_BUDGET,
            "luminance_pass": spread <= atlas_palette.LUMINANCE_BUDGET,
            "contrast_floor": atlas_palette.CONTRAST_FLOOR,
            "contrast_min_on_own_panel": round(min(own_panel_contrasts), 4),
            "contrast_pass": min(own_panel_contrasts) >= atlas_palette.CONTRAST_FLOOR,
            "ladder_min_gap": round(min(gaps), 4),
            "ladder_gap_floor": 0.05,
            "ladder_pass": min(gaps) >= 0.05,
            "categorical_disjoint_from_ladder": not set(ladder) & set(marks.values()),
        },
    }


def run_house_gates(figset: ModuleType, theme: str) -> dict[str, Any]:
    """Override the toolkit's palette with this theme's set and run its four gates."""
    marks = atlas_palette.categorical(theme)
    toolkit: Any = figset
    toolkit.PALETTE = dict(marks)
    toolkit.ORDER = list(marks)
    toolkit.FILL = dict(atlas_palette.fills(theme))
    toolkit.MARKER = dict(atlas_palette.MARKER)
    toolkit.HATCH = dict(atlas_palette.HATCH)
    toolkit.DASH = dict(atlas_palette.DASH)
    toolkit.LADDER = list(atlas_palette.ladder(theme))
    report = toolkit.check_palette(verbose=True)
    toolkit.require_second_channel(list(marks), toolkit.MARKER, toolkit.HATCH, toolkit.DASH)
    return {key: round(float(value), 4) for key, value in report.items()}


def main() -> int:
    figset = load_figset()
    print(f"toolkit: {os.environ.get('AIDD_FIGSET_PATH', str(DEFAULT_TOOLKIT))}")

    if float(figset.CVD_FLOOR) != atlas_palette.CVD_FLOOR:
        raise AssertionError(
            f"the house floor is {figset.CVD_FLOOR} but the palette module declares "
            f"{atlas_palette.CVD_FLOOR}; they must be the same number"
        )

    themes: dict[str, Any] = {}
    house: dict[str, Any] = {}
    for theme in atlas_palette.THEMES:
        print(f"\n=== {theme} theme ===")
        themes[theme] = measure_theme(figset, theme)
        house[theme] = run_house_gates(figset, theme)
        gates = themes[theme]["gates"]
        for key in ("cvd_pass", "luminance_pass", "contrast_pass", "ladder_pass"):
            if not gates[key]:
                raise AssertionError(f"{theme} theme fails the {key} gate: {gates}")

    payload = {
        "generated_by": "report/figures/measure_palette.py",
        "source_of_truth": "report/figures/atlas_palette.py",
        "site_mirror": "site/src/data/atlas-palette.json",
        "toolkit": {
            "name": "single-column-figs/assets/figset.py",
            "resolved_from": "the AIDD_FIGSET_PATH override or the skill's own assets folder",
            "cvd_floor": float(figset.CVD_FLOOR),
            "luminance_budget": float(figset.LUMINANCE_BUDGET),
        },
        "cvd_floor": atlas_palette.CVD_FLOOR,
        "floors": {
            "cvd_ciede2000": atlas_palette.CVD_FLOOR,
            "luminance_spread": atlas_palette.LUMINANCE_BUDGET,
            "wcag_contrast": atlas_palette.CONTRAST_FLOOR,
            "ladder_adjacent_luminance_gap": 0.05,
        },
        "vision_kinds": list(VISION_KINDS),
        "themes": themes,
        "house_gates": house,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for theme, data in themes.items():
        gates = data["gates"]
        worst = data["worst_pair"]
        print(
            f"\n{theme}: worst pair deutan {worst['deutan']['distance']:.2f} "
            f"({worst['deutan']['pair']}), protan {worst['protan']['distance']:.2f} "
            f"({worst['protan']['pair']}), tritan {worst['tritan']['distance']:.2f}, "
            f"normal {worst['normal']['distance']:.2f}"
        )
        print(
            f"       floor {gates['cvd_floor']}, luminance spread {gates['luminance_spread']} "
            f"of {gates['luminance_budget']}, contrast on its own panel "
            f"{gates['contrast_min_on_own_panel']}, ladder gap {gates['ladder_min_gap']}"
        )

    print(f"\nwritten {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
