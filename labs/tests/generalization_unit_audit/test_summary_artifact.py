"""The committed summary matches a fresh reading of the frozen snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.generalization_unit_audit.analysis import check_invariants
from aidd_commons.generalization_unit_audit.protocol import SUMMARY_SCHEMA_VERSION, UNITS
from aidd_commons.generalization_unit_audit.summary import build_summary, validate_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/generalization_unit_audit"
CACHE = ROOT / ".cache/decision_unit_scope"


def test_committed_summary_has_consistent_unit_counts() -> None:
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert committed["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert not validate_summary(committed)
    assert not check_invariants(committed)
    assert set(committed["units"]) == set(UNITS)
    assert committed["admitted_measurement_count"] == 486
    assert committed["admitted_point_row_count"] == 488
    assert all(item["measurement_count"] >= 486 for item in committed["units"].values())
    comparison = committed["two_unit_comparison"]
    assert comparison["units"] == {
        name: committed["units"][name]
        for name in (comparison["most_values"], comparison["fewest_values"])
    }


def test_cached_cohort_reproduces_committed_summary_when_present() -> None:
    if not CACHE.is_dir():
        pytest.skip("the frozen ChEMBL snapshot is not installed")
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    fresh = build_summary(LAB, CACHE, computed_on=committed["computed_on"])
    assert committed == fresh
