#!/usr/bin/env python3
"""Validate the PNG/PDF products the site actually publishes and their source captions.

Legacy SVG inputs are outside this delivery contract and are never changed by this
check. A nonempty manifest must cover every page placement, each image must decode at
its declared intrinsic dimensions, and each vector download must be a regular PDF file.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
FIGURE_DIR = REPO_ROOT / "site/public/figures"
REPORT_OUT = REPO_ROOT / "report/figures/out"
MANIFEST_PATH = REPO_ROOT / "site/src/data/atlas-figures.json"
PAGES = {
    "/": REPO_ROOT / "site/src/pages/index.astro",
    "/audit/": REPO_ROOT / "site/src/pages/audit/index.astro",
    "/labs/": REPO_ROOT / "site/src/pages/labs/index.astro",
    "/report/": REPO_ROOT / "site/src/pages/report/index.astro",
}


def check_delivery(
    figure: dict[str, Any],
    directory: Path,
    captions: dict[str, str],
    schematics: dict[str, str],
) -> list[str]:
    """Check one declared pair, including the known wrong-size and stale-caption defects."""
    problems: list[str] = []
    name = figure.get("id", "?")
    required = ("id", "file", "pdf", "source_stem", "width", "height", "alt", "caption", "pages")
    for field in required:
        if not figure.get(field):
            problems.append(f"{name}: the manifest has no {field}")
    stem = figure.get("source_stem", "")
    if not re.fullmatch(r"(?:plot_\d+_[a-z_]+|schematic-\d+-[a-z-]+)", stem):
        problems.append(f"{name}: invalid source generator stem {stem!r}")
        return problems
    plot = re.match(r"plot_(\d+)_", stem)
    if plot:
        expected_caption = captions.get(plot.group(1))
    else:
        schematic = re.match(r"schematic-(\d+)-", stem)
        expected_caption = schematics.get(f"S{int(schematic.group(1))}")
    if expected_caption is None or figure.get("caption") != expected_caption:
        problems.append(f"{name}: caption differs from its native source manifest")
    for field, suffix in (("file", ".png"), ("pdf", ".pdf")):
        filename = figure.get(field)
        expected = stem.replace("_", "-") + suffix
        if filename != expected:
            problems.append(f"{name}: {field} must be the source-derived {expected}")
            continue
        path = directory / filename
        if not path.is_file() or path.is_symlink():
            problems.append(f"{name}: {filename} is not a regular delivery file")
            continue
        if suffix == ".png":
            try:
                with Image.open(path) as image:
                    if image.format != "PNG":
                        problems.append(f"{name}: preview is not PNG")
                    if image.size != (figure.get("width"), figure.get("height")):
                        problems.append(f"{name}: declared dimensions differ from the PNG")
                    image.verify()
            except (OSError, ValueError, SyntaxError) as error:
                problems.append(f"{name}: PNG cannot be decoded: {error}")
        else:
            content = path.read_bytes()
            if not content.startswith(b"%PDF-") or not content.rstrip().endswith(b"%%EOF"):
                problems.append(f"{name}: vector download is not a complete PDF")
    return problems


def check_manifest() -> list[str]:
    """Check all products and both directions of the page-placement registration."""
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    figures = payload.get("figures", [])
    if not figures:
        return ["the manifest registers no figure"]
    captions = json.loads((REPORT_OUT / "captions.json").read_text(encoding="utf-8"))
    schematics = json.loads((REPORT_OUT / "captions-schematics.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    ids: set[str] = set()
    for figure in figures:
        problems.extend(check_delivery(figure, FIGURE_DIR, captions, schematics))
        name = figure.get("id", "?")
        if name in ids:
            problems.append(f"{name}: duplicate figure id")
        ids.add(name)
        generator = (
            REPO_ROOT / "report/figures" / (figure.get("source_stem", "").replace("-", "_") + ".py")
        )
        if not generator.is_file():
            problems.append(f"{name}: source generator does not exist")
        for page in figure.get("pages", []):
            source = PAGES.get(page)
            if source is None:
                problems.append(f"{name}: {page} is not a registered figure page")
            elif f'id="{name}"' not in source.read_text(encoding="utf-8"):
                problems.append(f"{name}: {page} does not place the figure")
    for page, source in PAGES.items():
        for used in re.findall(r'<AtlasFigure id="([^"]+)"', source.read_text(encoding="utf-8")):
            if not any(
                figure.get("id") == used and page in figure.get("pages", []) for figure in figures
            ):
                problems.append(f"{page}: places {used} without a matching manifest placement")
    return problems


def main() -> int:
    try:
        problems = check_manifest()
    except (OSError, ValueError) as error:
        print(f"site figure validation failed: {error}", file=sys.stderr)
        return 1
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"checked {len(payload['figures'])} source-bound PNG/PDF pairs and all page placements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
