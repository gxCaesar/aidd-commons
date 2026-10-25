"""Show the contract and per-laboratory verdicts, or check the committed audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.tool_contract_audit.analysis import audit_records, load_records  # noqa: E402
from aidd_commons.tool_contract_audit.protocol import load_protocol  # noqa: E402
from aidd_commons.tool_contract_audit.summary import check_summary  # noqa: E402

LAB = Path(__file__).resolve().parent
LABS = LAB.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "check"))
    args = parser.parse_args()
    try:
        if args.action == "check":
            failures = check_summary(LAB, LABS, LAB / "summary.json")
            for failure in failures:
                print(f"FAIL: {failure}")
            if failures:
                return 1
            print(
                "PASS: protocol, field counts and per-laboratory verdicts agree with local records"
            )
            return 0
        protocol = load_protocol(LAB / "protocol.json")
        result = audit_records(
            load_records(
                LABS, protocol["source"], exclude=protocol["source"]["exclude_laboratory"]
            ),
            protocol["contract"],
        )
        print(json.dumps(protocol["contract"], indent=2, sort_keys=True))
        print("laboratory\tverdict\tfailed_fields")
        for row in result["per_laboratory"]:
            failures = "; ".join(
                f"{item['field']}={item['reason']}" for item in row["failed_fields"]
            )
            print(f"{row['laboratory']}\t{row['verdict']}\t{failures or '-'}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
