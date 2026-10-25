"""Show the cycle audit or check the committed summary against the cached source."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.free_energy_network_audit.summary import (  # noqa: E402
    build_summary,
    check_summary,
)

LAB = Path(__file__).resolve().parent
DEFAULT_CACHE = LAB.parents[1] / ".cache/free_energy_network_audit"


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
            print("PASS: protocol, cycle classifications, summary and cached archives agree")
            return 0
        summary = build_summary(LAB, args.cache_dir)
        for system in summary["systems"]:
            print(
                f"{system['system']}: edges={system['edge_count']} "
                f"solvent={system['solvent_edges']} complex={system['complex_edges']} "
                f"solvent_estimates={system['solvent_estimates']} "
                f"complex_estimates={system['complex_estimates']} "
                f"estimates_per_edge={system['estimates_per_edge']} "
                f"cycles={system['cycle_count']} closed={system['closed_cycle_count']} "
                f"failed={system['failed_cycle_count']}"
            )
            for cycle in system["cycles"]:
                status = "closed" if cycle["closed"] else "FAILED"
                print(
                    f"  {status}\t{cycle['name']}\tsum={cycle['signed_sum_kcal_mol']:+.6f} "
                    f"+/- {cycle['standard_error_kcal_mol']:.6f} kcal/mol\t"
                    f"tolerance={cycle['tolerance_kcal_mol']:.6f} kcal/mol"
                )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
