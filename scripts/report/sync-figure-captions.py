"""Copy the generated figure captions into the report that carries them.

Every figure in this project is drawn by a script that reads a committed artefact, and
every one of those scripts writes its own caption into a manifest. The report embeds
each figure with the caption in the alt text, because that is how the document build
turns an image into a figure with a caption under it.

That leaves the caption in the report a hand-maintained copy of a generated string, and
a hand-maintained copy drifts. It had drifted here: the report carried a catalogue size
of 191 records while the manifest said 215, and coverage depths two readings behind the
audit. The number in the caption is a claim about the data, so a stale copy of it is a
stale claim.

    python scripts/report/sync-figure-captions.py            # rewrite the captions
    python scripts/report/sync-figure-captions.py --check    # report drift, change nothing

The check mode is what the test runs, so the drift is caught by the suite rather than by
whoever reads the document next.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "report/figures/out"
REPORT = ROOT / "report/aidd-commons-living-report-v0.1.md"

#: An embedded figure: the alt text, the path, and the trailing Pandoc attribute block.
FIGURE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<path>figures/out/(?:plot_\d+_|schematic-\d+-)[^)]*)\)"
    r"(?P<attrs>\{[^}]*\})"
)

#: The key a figure path belongs under in the caption manifests.
PLOT = re.compile(r"plot_(\d+)_")
SCHEMATIC = re.compile(r"schematic-(\d+)-")


def manifest_key(path: str) -> str | None:
    """The manifest key a figure path belongs under, or None when it is not a figure."""
    plot = PLOT.search(path)
    if plot is not None:
        return plot.group(1)
    schematic = SCHEMATIC.search(path)
    if schematic is not None:
        return f"S{int(schematic.group(1))}"
    return None


def load_captions() -> dict[str, str]:
    """Every caption the generators wrote, keyed by manifest key."""
    captions: dict[str, str] = {}
    for name in ("captions.json", "captions-schematics.json"):
        path = FIGURE_DIR / name
        if not path.exists():
            continue
        captions.update(json.loads(path.read_text(encoding="utf-8")))
    return captions


def sync(text: str, captions: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """Return the document with every caption replaced, the drift found and the gaps."""
    drift: list[str] = []
    gaps: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = manifest_key(match.group("path"))
        if key is None:
            return match.group(0)
        caption = captions.get(key)
        if caption is None:
            gaps.append(match.group("path"))
            return match.group(0)
        if caption.strip() != match.group("alt").strip():
            drift.append(match.group("path"))
        return f"![{caption}]({match.group('path')}){match.group('attrs')}"

    return FIGURE.sub(replace, text), drift, gaps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without rewriting")
    parser.add_argument("--report", default=str(REPORT), help="the document to read")
    arguments = parser.parse_args()

    report = Path(arguments.report)
    text = report.read_text(encoding="utf-8")
    captions = load_captions()
    updated, drift, gaps = sync(text, captions)

    for path in gaps:
        print(f"no caption for {path}", file=sys.stderr)
    if gaps:
        return 1

    if not drift:
        print(f"every caption in {report.name} matches the generated manifest")
        return 0

    if arguments.check:
        print(f"{len(drift)} captions in {report.name} differ from the generated manifest:")
        for path in drift:
            print(f"  {path}")
        return 1

    report.write_text(updated, encoding="utf-8")
    print(f"updated {len(drift)} captions in {report.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
