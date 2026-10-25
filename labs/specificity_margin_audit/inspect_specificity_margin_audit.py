"""Show the partner census or compare its committed summary with the archive."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.specificity_margin_audit.summary import (  # noqa: E402
    build_summary,
    check_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/specificity_margin_audit"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        if args.action == "check":
            failures = check_summary(LAB, args.cache_dir, LAB / "summary.json")
            for failure in failures:
                print(f"FAIL: {failure}")
            if failures:
                return 1
            print("PASS: protocol, summary and cached archive agree")
            return 0
        result = build_summary(LAB, args.cache_dir)
        print(f"archive_counts={result['archive_counts']}")
        print(f"partner_distribution={result['partner_distribution']}")
        print(f"comparable_pair_count={result['comparable_pair_count']}")
        print("protein\tmeasurements\tdistinct_partners\tbeyond_one_partner")
        for row in result["per_protein"]:
            print(
                f"{row['protein']}\t{row['measurement_count']}\t"
                f"{row['distinct_partners']}\t{row['beyond_one_partner']}"
            )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
