"""Show each compound verdict or audit the committed summary against the cache."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.l1000_perturbation_context.data import load_cached_cell_lines  # noqa: E402
from aidd_commons.mechanism_consistency.analysis import (  # noqa: E402
    analyse,
    counterevidence_counts,
    counts,
)
from aidd_commons.mechanism_consistency.protocol import load_protocol  # noqa: E402
from aidd_commons.mechanism_consistency.summary import check_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/l1000_perturbation_context"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        protocol = load_protocol(LAB / "protocol.json")
        if args.action == "check":
            failures = check_summary(LAB, args.cache_dir, LAB / "summary.json")
            for failure in failures:
                print(f"FAIL: {failure}")
            if failures:
                return 1
            print("PASS: protocol, per-compound rules, counts and cached snapshot agree")
            return 0
        verdicts, cohort = analyse(load_cached_cell_lines(args.cache_dir))
        print(f"explanations={protocol['explanations']}")
        print(f"informative_rho_minimum={protocol['comparison']['informative_rho_minimum']}")
        print(f"cohort={cohort}")
        print(f"side_counts={counts(verdicts)}")
        print(f"counterevidence_counts={counterevidence_counts(verdicts)}")
        print("pert_id\tpert_iname\tmatched_rho\tmismatched_rho\tverdict\treason")
        for row in verdicts:
            print(
                f"{row.pert_id}\t{row.pert_iname}\t{row.matched_rho:.6f}\t"
                f"{row.mismatched_rho:.6f}\t{row.verdict}\t{row.reason}"
            )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
