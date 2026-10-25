"""Show measured counts or check the frozen snapshot's structural invariants."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.skempi_affinity.analysis import (  # noqa: E402
    analyze,
    check_invariants,
)
from aidd_commons.skempi_affinity.data import load_cached  # noqa: E402
from aidd_commons.skempi_affinity.protocol import load_protocol  # noqa: E402

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DEFAULT_CACHE = ROOT / ".cache/skempi_affinity"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    args = parser.parse_args()
    try:
        load_protocol(LAB / "protocol.json")
        dataset = load_cached(DEFAULT_CACHE)
        result = analyze(dataset)
        failures = check_invariants(dataset, result)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if args.action == "show":
        for key in ("rows", "complexes", "complete_pairs", "field_counts", "classes",
                    "row_split_diagnostic", "complex_holdout"):
            print(f"{key}={result[key]}")
    else:
        # These are independent, measured snapshot oracles, never the result source.
        expected = {
            "": (4669, 249, 739),
            "AB/AG": (830, 51, 719),
            "Pr/PI": (1026, 59, 1026),
            "TCR/pMHC": (560, 37, 2),
        }
        observed = {
            name: (item["rows"], item["complexes"], item["complete_pairs"])
            for name, item in result["classes"].items()
        }
        if result["rows"] != 7085 or observed != expected:
            failures.append("snapshot audit count differs from the frozen source reading")
        if result["classes"].get("AB/AG", {}).get("top_five_rows") != 347:
            failures.append("complex concentration differs from the frozen source reading")
        print(f"invariants={len(failures)} failure(s)")
        print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
