"""Write the small summary only after the frozen contract and counts pass."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.split_leakage_audit.summary import export_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/split_leakage_audit"
SIBLING_CACHE = ROOT / ".cache/decision_unit_scope"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    cache_dir = args.cache_dir or (DEFAULT_CACHE if DEFAULT_CACHE.is_dir() else SIBLING_CACHE)
    try:
        export_summary(LAB, cache_dir, LAB / "summary.json")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print("Wrote summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
