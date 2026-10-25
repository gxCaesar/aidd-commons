"""The committed counts and rules must agree with the owning cached snapshot."""

import json
from pathlib import Path

import pytest
from aidd_commons.mechanism_consistency.summary import (
    build_summary,
    check_summary,
    validate_summary,
)

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/mechanism_consistency"
CACHE = ROOT / ".cache/l1000_perturbation_context"


@pytest.mark.skipif(not CACHE.is_dir(), reason="the L1000 perturbation snapshot is not cached")
def test_committed_summary_matches_snapshot():
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    fresh = build_summary(LAB, CACHE, computed_on=artifact["computed_on"])
    assert artifact["cohort"] == fresh["cohort"]
    assert artifact["side_counts"] == fresh["side_counts"]
    assert artifact["counterevidence_counts"] == fresh["counterevidence_counts"]
    assert artifact["falsifying_observation"] == fresh["falsifying_observation"]
    assert check_summary(LAB, CACHE, LAB / "summary.json") == []


def test_committed_summary_satisfies_local_contract():
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert validate_summary(artifact) == []
