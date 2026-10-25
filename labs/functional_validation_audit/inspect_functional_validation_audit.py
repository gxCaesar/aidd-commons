"""Show the record-kind counts and check them against both cached tables."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.functional_validation_audit.protocol import (  # noqa: E402
    KINDS,
    load_protocol,
)
from aidd_commons.functional_validation_audit.summary import (  # noqa: E402
    build_summary,
    validate_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/functional_validation_audit"


def read_summary() -> dict[str, Any]:
    value = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("summary must be an object")
    return value


def check(cache_dir: Path) -> list[str]:
    load_protocol(LAB / "protocol.json")
    committed = read_summary()
    failures = validate_summary(committed)
    if failures:
        return failures
    fresh = build_summary(
        LAB,
        cache_dir / "chembl37",
        cache_dir / "pubchem_bioassay",
        computed_on=committed["computed_on"],
    )
    for value in (committed, fresh):
        value.pop("software", None)
    if committed != fresh:
        failures.append("committed counts differ from the cached records")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        load_protocol(LAB / "protocol.json")
        summary = read_summary()
        failures = validate_summary(summary)
        if failures:
            raise ValueError("; ".join(failures))
        if args.action == "show":
            for table, data in summary["tables"].items():
                print(f"{table}: {data['total_records']} records")
                for kind in KINDS:
                    print(f"  {kind}: {data['kind_counts'][kind]}")
            print(f"no claim: {summary['records_licensing_no_claim']}")
            print(f"unmeasurable routes: {', '.join(summary['unmeasurable_routes'])}")
            return 0
        failures = check(args.cache_dir)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print("PASS: protocol, claim rules, summary and cached records agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
