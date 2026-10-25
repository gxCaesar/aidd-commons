"""Trim an evidence entry's `supports` list to the ten metadata groups.

The catalogue's schema lets an evidence entry say which metadata groups it
supports, and it admits exactly ten of them: name, kind, summary, identifiers,
stages, modalities, tasks, relations, caveats and acknowledgements. The access
level, the seven openness dimensions and the licences are claims in their own
right, each with its own evidence references, and they are not in that list.

An entry that names one of them is rejected by the validator, and the rejection
is correct: the list answers "which metadata does this page support", and an
access level is not metadata.

    python scripts/catalog/fix-evidence-supports.py             # report
    python scripts/catalog/fix-evidence-supports.py --write     # rewrite

The rewrite keeps the order the groups were written in and drops only the
names outside the ten, so the diff is the removal and nothing else.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "catalog/resources"

#: The groups an evidence entry may say it supports.
ALLOWED = (
    "name",
    "kind",
    "summary",
    "identifiers",
    "stages",
    "modalities",
    "tasks",
    "relations",
    "caveats",
    "acknowledgements",
)

SUPPORTS = re.compile(
    r"^(?P<indent>\s*)supports:\s*\[(?P<groups>[^\]]*)\]\s*$",
    re.MULTILINE,
)


def fix(text: str) -> tuple[str, list[str]]:
    """Return the text with its supports lists trimmed, and what was dropped."""
    dropped: list[str] = []

    def replace(match: re.Match[str]) -> str:
        groups = [group.strip() for group in match.group("groups").split(",") if group.strip()]
        kept = [group for group in groups if group in ALLOWED]
        for group in groups:
            if group not in ALLOWED:
                dropped.append(group)
        return f"{match.group('indent')}supports: [{', '.join(kept)}]"

    return SUPPORTS.sub(replace, text), dropped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    changed = 0
    for path in sorted(RESOURCES.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        updated, dropped = fix(text)
        if not dropped:
            continue
        changed += 1
        unique = sorted(set(dropped))
        print(f"{path.name}: dropped {', '.join(unique)}")
        if arguments.write:
            path.write_text(updated, encoding="utf-8")

    if changed == 0:
        print("every supports list names only the ten metadata groups")
    elif not arguments.write:
        print("re-run with --write to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
