"""Show question states or recompute the audit invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.open_question_audit.analysis import analyze, check_invariants  # noqa: E402
from aidd_commons.open_question_audit.protocol import load_protocol, load_sources  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        protocol = load_protocol(LAB / "protocol.json")
        result = analyze(load_sources(ROOT, protocol), protocol)
        failures = check_invariants(result, protocol)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if action == "show":
        for state, topics in result["state_topics"].items():
            print(json.dumps({"state": state, "count": len(topics), "topics": topics}))
        for key in ("open_with_falsifier", "open_without_falsifier", "held_without_falsifier"):
            print(json.dumps({key: result[key]}))
        print(json.dumps({"missing_measurement": result["missing_measurement"]}))
        print(json.dumps({"lowered_topics": result["lowered_topics"]}))
    for failure in failures:
        print(f"FAIL: {failure}")
    if action == "check":
        print(f"topic_count={result['topic_count']} failures={len(failures)}")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
