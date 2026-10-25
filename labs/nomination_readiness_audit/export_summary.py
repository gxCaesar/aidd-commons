"""Recompute the small committed summary after all contracts pass."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.nomination_readiness_audit.summary import build_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/nomination_readiness_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    cache_dir = args.cache_dir or (DEFAULT_CACHE if DEFAULT_CACHE.is_dir() else SIBLING_CACHE)
    try:
        summary = build_summary(LAB / "protocol.json", cache_dir, output=LAB / "summary.json")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"summary_bytes={(LAB / 'summary.json').stat().st_size}")
    print(f"admitted_measurements={summary['admitted_measurement_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
