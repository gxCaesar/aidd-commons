"""Show and check the committed split and leakage audit counts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.split_leakage_audit.protocol import (  # noqa: E402
    RDKIT_VERSION,
    ProtocolError,
    load_protocol,
)
from aidd_commons.split_leakage_audit.summary import (  # noqa: E402
    build_summary,
    validate_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/split_leakage_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def read_summary() -> dict[str, Any]:
    value = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("summary must be an object")
    return value


def check(cache_dir: Path) -> list[str]:
    load_protocol(LAB / "protocol.json")
    summary = read_summary()
    failures = validate_summary(summary)
    if summary.get("software", {}).get("rdkit") != RDKIT_VERSION:
        failures.append(
            "the committed reading was computed with an RDKit release other than the "
            "one the protocol declares"
        )
    if not cache_dir.is_dir():
        failures.append(f"snapshot cache missing: {cache_dir}")
        return failures
    fresh = build_summary(LAB, cache_dir, computed_on=summary.get("computed_on"))
    # The software block records the environment a run happened in, so it is
    # reported rather than compared. The counts are what must agree.
    counted = {key: value for key, value in fresh.items() if key != "software"}
    committed = {key: value for key, value in summary.items() if key != "software"}
    if counted != committed:
        failures.append("committed counts differ from a fresh computation")
    if fresh.get("software") != summary.get("software"):
        print(
            f"NOTE  this environment runs RDKit {fresh['software']['rdkit']} and the committed "
            f"reading was computed with {summary['software']['rdkit']}; the counts agree"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    cache_dir = args.cache_dir or (DEFAULT_CACHE if DEFAULT_CACHE.is_dir() else SIBLING_CACHE)
    try:
        load_protocol(LAB / "protocol.json")
        summary = read_summary()
        if args.action == "show":
            print(f"admitted measurements: {summary['admitted_measurement_count']}")
            print(f"row split: {summary['row_split']}")
            print(f"grouped parent split: {summary['grouped_parent_split']}")
            for route, counts in summary["routes"].items():
                print(f"{route}: {counts}")
            print(f"aggregate: {summary['aggregate']}")
            print(f"highest overlap route: {summary['highest_overlap_route']}")
            print(f"untestable routes: {', '.join(summary['untestable_routes'])}")
            return 0
        failures = check(cache_dir)
    except (OSError, ValueError, KeyError, ProtocolError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print("PASS: protocol, summary and cached measurements agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
