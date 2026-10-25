"""The committed artifact contains bounded counts that reconcile."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.functional_validation_audit.summary import build_summary, validate_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/functional_validation_audit"
CACHE = ROOT / ".cache/functional_validation_audit"


def test_committed_summary_is_count_only_and_consistent() -> None:
    raw = (LAB / "summary.json").read_text(encoding="utf-8")
    summary = json.loads(raw)
    assert validate_summary(summary) == []
    assert summary["tables"]["chembl37"]["total_records"] == 1004
    assert summary["tables"]["pubchem_bioassay"]["total_records"] == 1257
    assert summary["records_licensing_no_claim"] == 15
    assert '"activities"' not in raw
    assert '"canonical_smiles"' not in raw
    assert len(raw) < 20_000


@pytest.mark.skipif(
    not (CACHE / "chembl37/status.json").is_file(),
    reason="the laboratory cache is not present",
)
def test_cached_records_reproduce_the_committed_counts() -> None:
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    fresh = build_summary(
        LAB, CACHE / "chembl37", CACHE / "pubchem_bioassay", computed_on=summary["computed_on"]
    )
    assert fresh == summary
