"""Show the cross-domain decisions or check the committed summary against the caches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.crossdomain_tradeoff.protocol import load_protocol_document  # noqa: E402
from aidd_commons.crossdomain_tradeoff.summary import (  # noqa: E402
    build_summary,
    check_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def show(summary: dict[str, Any]) -> None:
    for decision in summary["teaching_decisions"] + summary["measured_decisions"]:
        print(decision["id"])
        for name, entry in decision["inputs"].items():
            print(f"  {name}: {entry['state']}")
            print(
                f"    value: {entry['value']} {entry['unit'] or ''}"
                f"; meets rule: {entry['meets_threshold']}"
                f"; evidence: {entry['evidence_kind']}"
            )
            if entry["note"]:
                print(f"    note: {entry['note']}")
        print(f"  blocking input: {decision['blocking_input']}")
        print(f"  next decision: {decision['next_decision']}")
        print(f"  evidence grade: {json.dumps(decision['evidence_grade'])}")
        print(f"  nomination complete: {decision['complete']}")
    print(f"Teaching blocking input: {json.dumps(summary['teaching_blocking_counts'])}")
    print(f"Teaching next decision: {json.dumps(summary['teaching_next_decision_counts'])}")
    print(f"Teaching complete: {summary['teaching_complete_count']}")
    print(f"Measured candidates: {summary['measured_candidate_count']}")
    print(f"Measured blocking input: {json.dumps(summary['measured_blocking_counts'])}")
    print(f"Measured next decision: {json.dumps(summary['measured_next_decision_counts'])}")
    print(f"Measured input states: {json.dumps(summary['measured_input_state_counts'])}")
    print(f"Measured complete: {summary['measured_complete_count']}")
    print(summary["boundary_statement"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    try:
        load_protocol_document(LAB / "protocol.json")
        computed = build_summary(args.cache_root)
        if args.action == "show":
            show(computed)
        else:
            committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
            check_summary(committed, computed)
            print("PASS: protocol, cached decisions and committed summary agree")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
