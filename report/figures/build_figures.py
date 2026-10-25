"""Draw every figure the living report carries, and check the caption manifests.

The figures in this directory are products, not illustrations. Each one is drawn by a
script that reads a committed artefact, so the artwork and the numbers behind it cannot
drift apart silently. This module is the entry point the report build calls before Pandoc
runs, and it does four things.

1. It runs every generator in this directory, the `plot_*.py` data figures and the
   `schematic_*.py` drawings, in name order. Each generator exposes its own entry point:
   a plot exposes `build()`, which saves the vector PDF and the site PNG and registers its
   caption; a schematic exposes `build()`, which returns the canvas, and `main()`, which
   saves it as a PDF and a PNG. The orchestrator calls `build()` on both, and the shared
   save helper writes the schematic's two products from the same native canvas.

2. It writes the raster copy of every schematic, so that every figure in the set has a
   vector file and a raster file, and the site can take either.

3. It prunes the plot caption manifest to the figures that were actually drawn, so that a
   generator that was deleted does not leave its caption behind.

4. It checks both caption manifests against the files on disk, in both directions, and
   stops the build when a figure has no caption or a caption has no figure. The same check
   runs as a test, in `tests/report/figure-manifest.test.ts`. It is here as well so that a
   broken set is caught at build time and not only in CI.

Determinism. The artwork carries its own epoch, `SOURCE_DATE_EPOCH=0`, which is the value
the shared style module already pins, so a build reproduces the committed figure files byte
for byte and the document's own epoch does not leak into the artwork. The caption manifest
is written with sorted keys, so its bytes do not depend on the order the plots ran in.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "out"
CAPTION_FILE = OUT_DIR / "captions.json"
SCHEMATIC_CAPTION_FILE = OUT_DIR / "captions-schematics.json"

# The artwork's own epoch, pinned before anything imports matplotlib. The document's epoch
# is a separate concern and belongs to the document.
os.environ["SOURCE_DATE_EPOCH"] = "0"
os.environ.setdefault("MPLBACKEND", "Agg")

# The figure set is drawn from committed sources and shipped as files; a bytecode cache
# beside the sources is noise in the tree and in the public export.
sys.dont_write_bytecode = True

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

#: A generator is named by its family and its index, so the shared style modules are not
#: mistaken for figures. The generators are named with an underscore and the files they
#: write with a hyphen, and the two are read apart here.
PLOT_PATTERN = re.compile(r"^plot_\d+_")
SCHEMATIC_PATTERN = re.compile(r"^schematic_\d+_")
SCHEMATIC_STEM_PATTERN = re.compile(r"^schematic-\d+-")

#: The suffixes a figure may be written under. Every one of them is a product of a
#: generator and every one of them has to carry a caption.
PRODUCT_SUFFIXES = (".pdf", ".png", ".svg")


def generator_names(pattern: re.Pattern[str]) -> list[str]:
    """The module names of the generators that match `pattern`, in name order."""
    return sorted(path.stem for path in HERE.glob("*.py") if pattern.match(path.stem))


def caption_key(stem: str) -> str | None:
    """The manifest key a figure stem belongs under, or None if it is not a figure."""
    if PLOT_PATTERN.match(stem):
        return stem.split("_")[1]
    if SCHEMATIC_STEM_PATTERN.match(stem):
        return f"S{int(stem.split('-')[1])}"
    return None


def reset_style() -> None:
    """Put matplotlib's rcParams back to their defaults.

    The two families do not share a style. A data figure sets its own style through
    `figure_style.apply_style`, and a schematic sets its own through `schematic_style`,
    which installs its rules once, when it is imported. Without this reset the first
    data figure's rules would reach the schematics that follow it, and the artwork
    would depend on the order the orchestrator happened to run in. Each generator is
    therefore drawn from the defaults it was designed against, exactly as it would be
    when it is run on its own.
    """
    import matplotlib

    matplotlib.rcParams.update(matplotlib.rcParamsDefault)


def draw_plots() -> list[str]:
    """Run every data-figure generator and return the stems it wrote."""
    stems: list[str] = []
    for name in generator_names(PLOT_PATTERN):
        reset_style()
        module = importlib.import_module(name)
        module.build()
        stems.append(module.STEM)
    return stems


def draw_schematics() -> list[str]:
    """Run every schematic generator and return the stems it wrote."""
    import matplotlib
    import matplotlib.pyplot as plt
    import schematic_style

    stems: list[str] = []
    for name in generator_names(SCHEMATIC_PATTERN):
        reset_style()
        matplotlib.rcParams.update(schematic_style.house_rc())
        module = importlib.import_module(name)
        canvas = module.build()
        canvas.save(OUT_DIR, module.STEM)
        plt.close(canvas.fig)
        stems.append(module.STEM)
    return stems


def prune_captions(stems: list[str]) -> None:
    """Drop the captions of figures that were not drawn."""
    if not CAPTION_FILE.exists():
        return
    payload = json.loads(CAPTION_FILE.read_text(encoding="utf-8"))
    keep = {key for key in payload if key in {caption_key(stem) for stem in stems}}
    if keep == set(payload):
        return
    CAPTION_FILE.write_text(
        json.dumps(
            {key: payload[key] for key in sorted(keep)},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def check_manifests(stems: list[str]) -> list[str]:
    """Check both manifests against the files on disk, in both directions."""
    problems: list[str] = []

    captions: dict[str, str] = {}
    if CAPTION_FILE.exists():
        captions = json.loads(CAPTION_FILE.read_text(encoding="utf-8"))
    else:
        problems.append(f"{CAPTION_FILE.name} is missing")

    schematic_captions: dict[str, str] = {}
    if SCHEMATIC_CAPTION_FILE.exists():
        schematic_captions = json.loads(SCHEMATIC_CAPTION_FILE.read_text(encoding="utf-8"))
    else:
        problems.append(f"{SCHEMATIC_CAPTION_FILE.name} is missing")

    def manifest_for(key: str) -> dict[str, str]:
        return schematic_captions if key.startswith("S") else captions

    for stem in stems:
        key = caption_key(stem)
        if key is None:
            problems.append(f"{stem}: not a figure name")
            continue
        if key not in manifest_for(key):
            problems.append(f"{stem}: no caption under {key}")
        for suffix in (".pdf", ".png"):
            if not (OUT_DIR / f"{stem}{suffix}").exists():
                problems.append(f"{stem}: no {suffix} file")

    for path in sorted(OUT_DIR.iterdir()):
        if path.suffix not in PRODUCT_SUFFIXES:
            continue
        key = caption_key(path.stem)
        if key is None or key not in manifest_for(key):
            problems.append(f"{path.name}: no caption")

    return problems


def main() -> int:
    """Draw the set, check the manifests, and report what was written."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    plot_stems = draw_plots()
    schematic_stems = draw_schematics()
    stems = plot_stems + schematic_stems

    prune_captions(plot_stems)

    problems = check_manifests(stems)
    if problems:
        print("the figure set and its caption manifests disagree:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    for stem in stems:
        print(f"wrote {OUT_DIR / f'{stem}.pdf'}")
    print(f"drew {len(stems)} figures and checked {len(stems)} captions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
