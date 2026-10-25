"""Show unit counts or recompute and check the committed summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.generalization_unit_audit.protocol import (  # noqa: E402
    RDKIT_VERSION,
    load_protocol,
)
from aidd_commons.generalization_unit_audit.summary import (  # noqa: E402
    build_summary,
    validate_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/generalization_unit_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def read_summary() -> dict[str, Any]:
    value = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("summary must be an object")
    return value


def check(cache_dir: Path) -> list[str]:
    load_protocol(LAB / "protocol.json")
    committed = read_summary()
    failures = validate_summary(committed)
    if committed.get("software", {}).get("rdkit") != RDKIT_VERSION:
        failures.append("committed RDKit version differs from the frozen protocol")
    if not cache_dir.is_dir():
        return [*failures, f"snapshot cache missing: {cache_dir}"]
    fresh = build_summary(LAB, cache_dir, computed_on=committed.get("computed_on"))
    if {key: value for key, value in fresh.items() if key != "software"} != {
        key: value for key, value in committed.items() if key != "software"
    }:
        failures.append("committed counts differ from a fresh computation")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    cache_dir = args.cache_dir or (DEFAULT_CACHE if DEFAULT_CACHE.is_dir() else SIBLING_CACHE)
    try:
        load_protocol(LAB / "protocol.json")
        if args.action == "show":
            summary = read_summary()
            for name, counts in summary["units"].items():
                print(f"{name}: {json.dumps(counts, sort_keys=True)}")
            print(f"admitted_measurements: {summary['admitted_measurement_count']}")
            unavailable = json.dumps(summary["units_table_cannot_name"], sort_keys=True)
            print(f"units_table_cannot_name: {unavailable}")
            print(
                f"two_unit_comparison: {json.dumps(summary['two_unit_comparison'], sort_keys=True)}"
            )
            return 0
        failures = check(cache_dir)
    except (OSError, ValueError, KeyError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    for failure in failures:
        print(f"FAIL: {failure}")
    print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
