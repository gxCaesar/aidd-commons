"""Show per-source coverage or check the committed construct audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.biologic_construct_audit.analysis import (  # noqa: E402
    classified_source_rows,
    load_snapshot,
)
from aidd_commons.biologic_construct_audit.protocol import load_protocol  # noqa: E402
from aidd_commons.biologic_construct_audit.summary import (  # noqa: E402
    build_summary,
    check_summary,
)

LAB = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    action = parser.parse_args().action
    try:
        if action == "check":
            failures = check_summary(LAB, LAB / "summary.json")
            for failure in failures:
                print(f"FAIL: {failure}")
            if failures:
                return 1
            print("PASS: protocol, committed source snapshot, audit rules and summary agree")
            return 0
        result = build_summary(LAB)
        print(f"entity_count={result['entity_count']}")
        print(f"per_field_counts={result['per_field_counts']}")
        print(f"entities_by_fields={result['entities_by_fields']}")
        protocol = load_protocol(LAB / "protocol.json")
        source_rows = classified_source_rows(load_snapshot(LAB, protocol), protocol)
        print(
            "entity\tsource\tmodality\tconstruct\texpression_system\tintended_function\tassembly\tparts_distinguished\tdefined_construct"
        )
        for row in source_rows:
            values = row["values"]
            print(
                "\t".join(
                    [
                        row["entity"],
                        row["source"],
                        *(values[name] or "unstated" for name in values),
                        row["assembly"],
                        str(row["parts_distinguished"]).lower(),
                        str(row["defined_construct"]).lower(),
                    ]
                )
            )
        print(f"gaps={result['gaps']}")
        print(f"source_coverage_differences={result['source_coverage_differences']}")
        print(f"source_disagreements={result['source_disagreements']}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
