"""The real cached join supplies contradictions without crossing clearance bases."""

from __future__ import annotations

from pathlib import Path

import pytest
from aidd_commons.multi_endpoint_integration.summary import build_summary as joined_summary
from aidd_commons.target_product_profile.summary import compute

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_real_compound_failing_gate_is_not_satisfying() -> None:
    summary, evaluations = compute(ROOT / ".cache")
    assert len(evaluations) == summary["counts"]["cohort_compound_count"] == 58
    assert summary["counts"]["contradicted_compound_count"] > 0
    failing = [row for row in evaluations if row["failed_gates"]]
    assert len(failing) == summary["counts"]["contradicted_compound_count"]
    assert all(not row["profile_satisfying"] for row in failing)
    assert all(row["parent_chembl_id"] not in summary["satisfying_parent_ids"] for row in failing)
    assert summary["per_gate"]["cyp3a4_inhibition"]["fail"] == 20


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_clearance_bases_remain_separate() -> None:
    joined = joined_summary(ROOT / ".cache")
    profile = next(row for row in joined["profiles"] if row["parent_chembl_id"] == "CHEMBL1232461")
    exposure = profile["exposure"]
    assert exposure is not None
    assert set(exposure["spread_by_unit"]) == {"mL.min-1.g-1", "uL.min-1.(10^6cells)-1"}
    summary, evaluations = compute(ROOT / ".cache")
    evaluated = next(row for row in evaluations if row["parent_chembl_id"] == "CHEMBL1232461")
    assert evaluated["outcomes"]["human_microsome_clearance"] == "pass"
    assert evaluated["outcomes"]["rat_hepatocyte_clearance"] == "met"
    assert "fold_change" not in str(summary)
