"""Show the separate endpoint families or audit the committed summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.data import DataContractError  # noqa: E402
from aidd_commons.multi_endpoint_tradeoff.protocol import (  # noqa: E402
    FAMILIES,
    ProtocolContractError,
    load_protocol_document,
)
from aidd_commons.multi_endpoint_tradeoff.summary import (  # noqa: E402
    SummaryContractError,
    audit_summary,
    build_summary,
)

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def check(committed: dict[str, Any], computed: dict[str, Any]) -> None:
    audit_summary(committed)
    audit_summary(computed)
    for field, value in computed.items():
        if field not in {"computed_on", "software"} and committed.get(field) != value:
            raise SummaryContractError(f"committed {field} differs from the cached computation")


def show(summary: dict[str, Any]) -> None:
    print(f"Admitted independent measurements: {summary['admitted_measurement_count']}")
    for family in FAMILIES:
        item = summary["families"][family]
        print(
            f"{family}: n={item['independent_measurement_count']}, "
            f"documents={item['distinct_document_count']}, assays={item['distinct_assay_count']}, "
            f"median={item['median']} {item['unit']}, IQR={item['interquartile_range']} "
            f"{item['unit']}, compounds without measurement="
            f"{item['compounds_without_measurement_count']}"
        )
    print("Per-parent independent measurement counts:")
    for compound in summary["per_compound_coverage"]:
        counts = ", ".join(
            f"{family}={compound['families'][family]['independent_measurement_count']}"
            for family in FAMILIES
        )
        print(f"  {compound['parent_molecule_chembl_id']} {compound['pref_name']}: {counts}")
    print("Parents with an empty named family:")
    for compound in summary["compounds_with_empty_family"]:
        print(
            f"  {compound['parent_molecule_chembl_id']}: "
            f"{', '.join(compound['missing_families'])} missing, "
            f"{compound['present_named_family_count']} named families present"
        )
    print("No family score or ranking is computed. Missing is not safe, clean or bioavailable.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/multi_endpoint_tradeoff")
    args = parser.parse_args()
    try:
        load_protocol_document(LAB / "protocol.json")
        computed = build_summary(args.cache_dir)
        audit_summary(computed)
        if args.action == "check":
            committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
            check(committed, computed)
            print("PASS: protocol, cached measurements and committed summary agree")
        else:
            show(computed)
    except (
        ProtocolContractError,
        DataContractError,
        SummaryContractError,
        OSError,
        ValueError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
