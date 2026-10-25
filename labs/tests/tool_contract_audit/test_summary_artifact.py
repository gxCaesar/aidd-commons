"""The committed summary reconciles with records on disk."""

from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.tool_contract_audit.analysis import audit_records, load_records
from aidd_commons.tool_contract_audit.protocol import BOUNDARY, expected_fields
from aidd_commons.tool_contract_audit.summary import check_summary, validate_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/tool_contract_audit"


def test_committed_summary_counts_and_verdicts_match_local_records() -> None:
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    protocol = expected_fields()
    current = audit_records(
        load_records(
            ROOT / "labs",
            protocol["source"],
            exclude=protocol["source"]["exclude_laboratory"],
        ),
        protocol["contract"],
    )
    assert validate_summary(summary) == []
    assert summary["contract"] == protocol["contract"]
    assert summary["boundary"] == BOUNDARY
    for field in current:
        assert summary[field] == current[field]
    assert check_summary(LAB, ROOT / "labs", LAB / "summary.json") == []
