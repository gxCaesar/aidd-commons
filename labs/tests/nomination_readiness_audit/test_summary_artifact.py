"""The committed result matches a fresh recount of the cached snapshot."""

import json
from pathlib import Path

import pytest
from aidd_commons.nomination_readiness_audit.summary import (
    SCHEMA_VERSION,
    build_summary,
    validate_summary,
)

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/nomination_readiness_audit"
CACHE = ROOT / ".cache/decision_unit_scope"


@pytest.mark.skipif(not CACHE.is_dir(), reason="the decision-unit ChEMBL snapshot is not cached")
def test_committed_summary_matches_measurements() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    actual = build_summary(
        LAB / "protocol.json",
        CACHE,
        computed_on=artifact["computed_on"],
        software=artifact["software"],
    )
    assert artifact == actual


def test_committed_summary_counts_reconcile() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert validate_summary(artifact) == []
    assert artifact["schema_version"] == SCHEMA_VERSION
    assert artifact["cohort_size"] == 10
    assert artifact["admitted_measurement_count"] == 486
    assert sum(artifact["state_counts"].values()) == artifact["cohort_size"]
    assert len(artifact["parents"]) == artifact["cohort_size"]
    assert all("activity_id" not in row for row in artifact["parents"])
