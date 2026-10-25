"""Export the compact summary only after all audits pass."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.crossdomain_tradeoff.summary import export_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    try:
        export_summary(LAB, args.cache_root, LAB / "summary.json")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"Wrote {LAB / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
