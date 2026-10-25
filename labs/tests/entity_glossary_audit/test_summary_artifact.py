"""The committed result is a small current projection of cached data."""

import json
from pathlib import Path

import pytest
from aidd_commons.entity_glossary_audit.protocol import SUMMARY_SCHEMA_VERSION
from aidd_commons.entity_glossary_audit.summary import build_summary, validate_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/entity_glossary_audit"
CACHE = ROOT / ".cache/decision_unit_scope"


@pytest.mark.skipif(not CACHE.is_dir(), reason="the decision-unit ChEMBL snapshot is not cached")
def test_committed_summary_matches_cached_rows() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    computed = build_summary(
        LAB, CACHE, computed_on=artifact["computed_on"], software=artifact["software"]
    )
    assert artifact == computed


def test_committed_summary_counts_reconcile() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert validate_summary(artifact) == []
    assert artifact["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert artifact["admitted_point_row_count"] == 488
    assert artifact["admitted_measurement_count"] == 486
    assert artifact["totals"]["distinct_identifiers_across_kinds"] == sum(
        item["distinct_identifiers"] for item in artifact["per_kind"].values()
    )
    assert artifact["totals"]["identifier_uses"] == 488 * len(artifact["per_kind"])
    assert "activities" not in artifact
