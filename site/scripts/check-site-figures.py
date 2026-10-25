#!/usr/bin/env python3
"""Check the site's figures before they ship.

Four things are checked, and every one of them is a property of the products rather than
of the intent behind them.

1. Every file in `site/public/figures/` is a figure, it is not empty, and it is well
   formed XML.
2. Every one of them refers to a CSS custom property, so the drawing follows the site's
   theme rather than carrying a palette of its own.
3. No colour of the report's own palette is left in any of them. A leftover hex is a
   colour that will not change with the theme, which is the defect this check exists to
   catch.
4. Every figure the site places is registered in `site/src/data/atlas-figures.json` with
   a file that exists, an alt text, a caption and the pages it belongs on, and every
   figure that is placed is placed on a page that asks for it.

The script exits with a non-zero status when a check fails, so it can be run on its own or
from a build.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
FIGURE_DIR = REPO_ROOT / "site" / "public" / "figures"
MANIFEST_PATH = REPO_ROOT / "site" / "src" / "data" / "atlas-figures.json"
PAGES = {
    "/": REPO_ROOT / "site" / "src" / "pages" / "index.astro",
    "/audit/": REPO_ROOT / "site" / "src" / "pages" / "audit" / "index.astro",
    "/labs/": REPO_ROOT / "site" / "src" / "pages" / "labs" / "index.astro",
    "/report/": REPO_ROOT / "site" / "src" / "pages" / "report" / "index.astro",
}

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
VARIABLE_RE = re.compile(r"var\(--atlas")


def palette_hexes() -> dict[str, set[str]]:
    """Every colour the report's palette defines, by theme."""
    sys.path.insert(0, str(REPO_ROOT / "report" / "figures"))
    import atlas_palette

    colours: dict[str, set[str]] = {}
    for theme in atlas_palette.THEMES:
        found: set[str] = set()
        for group in (
            atlas_palette.tokens(theme),
            atlas_palette.categorical(theme),
            atlas_palette.fills(theme),
        ):
            found.update(value.lower() for value in group.values())
        found.update(value.lower() for value in atlas_palette.ladder(theme))
        colours[theme] = found
    return colours


def check_figures(hexes: set[str]) -> list[str]:
    """Every file in the figures directory, checked on its own."""
    problems: list[str] = []
    if not FIGURE_DIR.is_dir():
        return [f"{FIGURE_DIR} does not exist"]

    files = sorted(FIGURE_DIR.glob("*.svg"))
    if not files:
        return [f"{FIGURE_DIR} holds no figure"]

    for path in files:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            problems.append(f"{path.name}: the file is empty")
            continue
        if not VARIABLE_RE.search(text):
            problems.append(f"{path.name}: no reference to a site colour property")
        left = sorted({value.lower() for value in HEX_RE.findall(text)} & hexes)
        if left:
            problems.append(f"{path.name}: palette colours left in the file: {', '.join(left)}")
        try:
            ElementTree.fromstring(text)
        except ElementTree.ParseError as error:
            problems.append(f"{path.name}: not well formed XML: {error}")
    return problems


def check_manifest() -> list[str]:
    """The manifest, and the pages that place the figures."""
    problems: list[str] = []
    if not MANIFEST_PATH.exists():
        return [f"{MANIFEST_PATH} does not exist"]

    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    figures = payload.get("figures", [])
    if not figures:
        return ["the manifest registers no figure"]

    for figure in figures:
        for field in ("id", "file", "alt", "caption", "pages"):
            if not figure.get(field):
                problems.append(f"{figure.get('id', '?')}: the manifest has no {field}")
        if not (FIGURE_DIR / figure["file"]).exists():
            problems.append(f"{figure['id']}: {figure['file']} is not in the figures directory")
        for page in figure.get("pages", []):
            source = PAGES.get(page)
            if source is None:
                problems.append(f"{figure['id']}: {page} is not a page this site serves")
            elif f'id="{figure["id"]}"' not in source.read_text(encoding="utf-8"):
                problems.append(f"{figure['id']}: {page} does not place the figure")

    for page, source in PAGES.items():
        if not source.exists():
            continue
        text = source.read_text(encoding="utf-8")
        for used in re.findall(r'<AtlasFigure id="([^"]+)"', text):
            if not any(figure["id"] == used for figure in figures):
                problems.append(f"{page}: places {used}, which the manifest does not register")
    return problems


def main() -> int:
    colours = palette_hexes()
    problems = check_figures(colours["light"] | colours["dark"])
    problems += check_manifest()

    files = sorted(FIGURE_DIR.glob("*.svg")) if FIGURE_DIR.is_dir() else []
    print(f"checked {len(files)} figures in {FIGURE_DIR}")
    for path in files:
        print(f"  {path.name:<44} {path.stat().st_size:>7} bytes")

    if problems:
        print()
        print("the site figures do not pass:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print()
    print("every figure is themed, empty of palette colours, and registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
