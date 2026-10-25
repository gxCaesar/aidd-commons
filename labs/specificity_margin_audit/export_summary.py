"""Write the small count summary after all checks pass."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.specificity_margin_audit.summary import export_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/specificity_margin_audit"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        export_summary(LAB, args.cache_dir, LAB / "summary.json")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print("Wrote summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
