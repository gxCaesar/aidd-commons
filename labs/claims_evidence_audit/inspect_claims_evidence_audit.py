"""Show every selected cell or recompute the evidence and claim invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.claims_evidence_audit.analysis import analyze, check_invariants  # noqa: E402
from aidd_commons.claims_evidence_audit.protocol import load_protocol  # noqa: E402
from aidd_commons.claims_evidence_audit.records import load_sources  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        protocol = load_protocol(LAB / "protocol.json")
        result = analyze(load_sources(ROOT, protocol), protocol, ROOT)
        failures = check_invariants(result, protocol)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if action == "show":
        for cell in result["cells"]:
            print(json.dumps(cell, ensure_ascii=False))
        print(json.dumps({"state_counts": result["state_counts"]}, ensure_ascii=False))
        print(json.dumps({"unsupported_claims": result["unsupported_claims"]}, ensure_ascii=False))
        print(json.dumps({"disagreements": result["disagreements"]}, ensure_ascii=False))
        print(json.dumps({"claims": result["claims"]}, ensure_ascii=False))
        print(
            "A default unknown does not establish absence. The own row is a stated floor, "
            "not a measure of teaching quality."
        )
    else:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"invariants={len(failures)} failure(s)")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
