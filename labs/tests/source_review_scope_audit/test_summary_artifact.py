"""The committed summary is a compact, internally consistent projection."""

import json
from pathlib import Path

from aidd_commons.source_review_scope_audit.protocol import EXAMINED_IDS
from aidd_commons.source_review_scope_audit.summary import SCHEMA_VERSION, build_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/source_review_scope_audit"


def test_summary_has_required_fields_and_matches_live_counts() -> None:
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    live = build_summary(ROOT, LAB / "protocol.json", computed_on=committed["computed_on"])
    assert committed["schema_version"] == SCHEMA_VERSION
    assert committed["protocol_id"] == "aidd-commons.source-review-scope-audit-v1"
    assert committed["software"]["python"]
    assert committed["software"]["pyyaml"]
    assert committed["examined_record_ids"] == list(EXAMINED_IDS)
    assert committed["records"] == live["records"]
    assert committed["totals"] == live["totals"]
    assert committed["unresolved_claim_references"] == live["unresolved_claim_references"]
    assert committed["unmeasurable_routes"] == live["unmeasurable_routes"]
    assert committed["independent_reading"] == live["independent_reading"]
    assert all("entries" not in row and "claims" not in row for row in committed["records"])


def test_summary_totals_are_sums_of_examined_records() -> None:
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    rows = summary["records"]
    totals = summary["totals"]
    assert totals["records"] == len(rows)
    assert totals["evidence_entries"] == sum(row["evidence_entries"] for row in rows)
    for part, states in totals["parts"].items():
        for state, count in states.items():
            assert count == sum(row["part_counts"][part][state] for row in rows)
    for key, count in totals["special"].items():
        assert count == sum(row["special_counts"][key] for row in rows)
    for key, count in totals["claims"].items():
        assert count == sum(row["claim_counts"][key] for row in rows)
