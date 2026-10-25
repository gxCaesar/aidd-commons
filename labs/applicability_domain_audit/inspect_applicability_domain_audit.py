"""Show measured aggregates or check the applicability-domain audit invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.applicability_domain_audit.analysis import (  # noqa: E402
    analyze,
    check_invariants,
    load_release,
)
from aidd_commons.applicability_domain_audit.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        protocol = load_protocol(LAB / "protocol.json")
        result = analyze(load_release(ROOT / protocol["source"]["path"]))
        failures = check_invariants(result)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if action == "show":
        print(
            json.dumps(
                {
                    "cohort": result.cohort,
                    "split": result.split,
                    "distance_statistics": result.distance_statistics,
                    "error_halves": result.error_halves,
                },
                indent=2,
            )
        )
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if action == "check":
        print(f"invariants={len(failures)} failure(s)")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
