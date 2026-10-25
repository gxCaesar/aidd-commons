"""Real-snapshot overlap and missingness checks."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from aidd_commons.az_clearance_system.data import load_cached_systems
from aidd_commons.cyp_assay_system.data import load_cached_targets
from aidd_commons.decision_unit_scope.data import load_cached_cohort
from aidd_commons.multi_endpoint_integration.analysis import analyse
from aidd_commons.multi_endpoint_integration.summary import build_summary
from aidd_commons.multi_endpoint_tradeoff.analysis import (
    admitted_measurements,
    independent_measurements,
)

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / ".cache"


@pytest.fixture(scope="module")
def summary() -> dict:
    return build_summary(CACHE, computed_on="2026-10-23")


@pytest.mark.skipif(
    not (CACHE / "decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_real_overlap_is_explicit_and_missing_is_not_filled(summary: dict) -> None:
    matrix = summary["family_coverage_matrix"]
    assert matrix["efficacy+exposure"] == 1
    assert matrix["efficacy+interaction"] == 0
    assert matrix["exposure+interaction"] == 57
    assert matrix["efficacy+exposure+interaction"] == 0
    assert len(summary["profiles"]) == 58
    assert summary["counts"]["one_family_compound_count"] == 7850
    assert all(profile["toxicity"] is None for profile in summary["profiles"])
    assert all(
        profile[family] is None
        for profile in summary["profiles"]
        for family in profile["missing_families"]
    )
    single = summary["single_family_compounds"]
    assert all(
        parent not in {p["parent_chembl_id"] for p in summary["profiles"]}
        for parent in single["efficacy"]
    )


@pytest.mark.skipif(
    not (CACHE / "decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_clearance_bases_remain_separate(summary: dict) -> None:
    profile = next(
        profile for profile in summary["profiles"] if profile["parent_chembl_id"] == "CHEMBL1232461"
    )
    exposure = profile["exposure"]
    assert exposure is not None
    assert set(exposure["spread_by_unit"]) == {"mL.min-1.g-1", "uL.min-1.(10^6cells)-1"}
    assert all(item["count"] == 1 for item in exposure["spread_by_unit"].values())
    assert "ratio" not in exposure and "fold_change" not in exposure


@pytest.mark.skipif(
    not (CACHE / "decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_join_uses_parent_identifier_only() -> None:
    cohort = load_cached_cohort(CACHE / "decision_unit_scope")
    systems = load_cached_systems(CACHE / "az_clearance_system")
    targets = load_cached_targets(CACHE / "cyp_assay_system")
    measurements = independent_measurements(admitted_measurements(cohort))
    original = analyse(measurements, {}, systems, targets)
    assert any(p["parent_chembl_id"] == "CHEMBL1144" for p in original["profiles"])

    altered = {}
    for assay_id, dataset in systems.items():
        altered[assay_id] = replace(
            dataset,
            records=tuple(
                replace(record, parent_molecule_chembl_id="UNRELATED_PARENT")
                if record.parent_molecule_chembl_id == "CHEMBL1144"
                else record
                for record in dataset.records
            ),
        )
    changed = analyse(measurements, {}, altered, targets)
    assert not any(p["parent_chembl_id"] == "CHEMBL1144" for p in changed["profiles"])
    assert "CHEMBL1144" in changed["single_family_compounds"]["efficacy"]
