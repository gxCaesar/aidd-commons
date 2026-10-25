"""Export a count-only summary after checking the frozen rule and both caches."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.functional_validation_audit.summary import export_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/functional_validation_audit"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        export_summary(
            LAB,
            args.cache_dir / "chembl37",
            args.cache_dir / "pubchem_bioassay",
            LAB / "summary.json",
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print("Wrote summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
