"""Show the frozen rule and recompute every committed readiness state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.nomination_readiness_audit.protocol import (  # noqa: E402
    ProtocolError,
    load_protocol,
)
from aidd_commons.nomination_readiness_audit.summary import (  # noqa: E402
    build_summary,
    validate_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/nomination_readiness_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def read_summary() -> dict[str, Any]:
    value = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("summary must be an object")
    return value


def check(cache_dir: Path, committed: dict[str, Any]) -> list[str]:
    failures = validate_summary(committed)
    fresh = build_summary(
        LAB / "protocol.json",
        cache_dir,
        computed_on=committed.get("computed_on"),
        software=committed.get("software"),
    )
    if fresh != committed:
        failures.append("committed table differs from a fresh computation")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    cache_dir = args.cache_dir or (DEFAULT_CACHE if DEFAULT_CACHE.is_dir() else SIBLING_CACHE)
    try:
        protocol = load_protocol(LAB / "protocol.json")
        summary = read_summary()
        if args.action == "show":
            print(json.dumps(protocol["readiness_rule"], ensure_ascii=False))
            for row in summary["parents"]:
                print(json.dumps(row, ensure_ascii=False))
            print(json.dumps(summary["state_counts"], ensure_ascii=False))
            return 0
        failures = check(cache_dir, summary)
    except (OSError, ValueError, KeyError, TypeError, ProtocolError) as error:
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
