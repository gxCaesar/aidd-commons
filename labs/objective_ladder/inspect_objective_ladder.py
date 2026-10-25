"""Read the ladder, and check that what is committed still holds.

    python labs/objective_ladder/inspect_objective_ladder.py show
    python labs/objective_ladder/inspect_objective_ladder.py check

`show` prints the ladder. `check` recomputes it from the cached records and
compares it with the committed summary, and exits non-zero when anything
differs, when a target is missing an objective, or when an empty cell carries
no reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidd_commons.objective_ladder.data import DEFAULT_CACHE_DIR  # noqa: E402
from aidd_commons.objective_ladder.protocol import (  # noqa: E402
    ABSENCE_REASONS,
    OBJECTIVES,
    load_protocol,
)
from aidd_commons.objective_ladder.runner import read_ladders  # noqa: E402

LAB = Path(__file__).resolve().parent
SUMMARY_PATH = LAB / "summary.json"


def show(ladders) -> None:
    for ladder in ladders:
        print(f"{ladder.symbol} ({ladder.accession}) - {ladder.name}")
        for name in OBJECTIVES:
            outcome = ladder.outcomes[name]
            mark = "record " if outcome.found else "empty  "
            line = outcome.record or outcome.detail
            print(f"    {mark} {name:<24} {line[:150]}")
        print(f"    {ladder.evidenced} of {len(OBJECTIVES)} objectives carry a record")
        print()


def check(ladders, protocol) -> list[str]:
    """Return the failures, if any."""
    failures: list[str] = []
    for ladder in ladders:
        missing = [name for name in OBJECTIVES if name not in ladder.outcomes]
        if missing:
            failures.append(f"{ladder.accession}: the ladder has no outcome for {missing}")
        for name in OBJECTIVES:
            outcome = ladder.outcomes.get(name)
            if outcome is None:
                continue
            if not outcome.found:
                if not outcome.absence_reason:
                    failures.append(f"{ladder.accession}: the empty {name} cell carries no reason")
                elif outcome.absence_reason not in ABSENCE_REASONS:
                    failures.append(
                        f"{ladder.accession}: the empty {name} cell carries an undeclared reason"
                    )
            elif not outcome.record:
                failures.append(f"{ladder.accession}: the filled {name} cell names no record")

    if not SUMMARY_PATH.exists():
        failures.append("the committed summary is missing")
        return failures
    committed = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    if committed.get("protocol_id") != protocol.protocol_id:
        failures.append("the committed summary names a different protocol")
    for target in committed.get("targets", []):
        recorded = target.get("evidenced_objectives")
        ladder = next((item for item in ladders if item.accession == target.get("accession")), None)
        if ladder is None:
            failures.append(
                f"{target.get('accession')}: the summary names a target that is not read"
            )
        elif recorded != ladder.evidenced:
            failures.append(
                f"{target.get('accession')}: the summary records {recorded} objectives, "
                f"the reading finds {ladder.evidenced}"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    arguments = parser.parse_args()

    protocol = load_protocol()
    ladders = read_ladders(protocol, arguments.cache_dir)

    if arguments.action == "show":
        show(ladders)
        return 0

    failures = check(ladders, protocol)
    if failures:
        for failure in failures:
            print(f"FAIL  {failure}")
        return 1
    print("PASS  the committed summary matches the reading, and every empty cell carries a reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
