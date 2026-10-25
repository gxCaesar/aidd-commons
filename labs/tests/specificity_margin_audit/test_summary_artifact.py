"""The committed census matches an independent read of the cached snapshot."""

import json
from pathlib import Path

import aidd_commons.specificity_margin_audit.summary as summary_module
import pytest
from aidd_commons.specificity_margin_audit.summary import (
    EXPECTED_COUNTS,
    build_summary,
    check_summary,
    validate_summary,
)

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/specificity_margin_audit"
SOURCE_CACHE = ROOT / ".cache/skempi_affinity"


@pytest.mark.skipif(
    not SOURCE_CACHE.is_dir(), reason="the SKEMPI affinity source archive is not cached"
)
def test_committed_summary_matches_archive():
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    fresh = build_summary(LAB, SOURCE_CACHE, computed_on=artifact["computed_on"])
    assert artifact["partner_distribution"] == fresh["partner_distribution"]
    assert artifact["comparable_pair_count"] == fresh["comparable_pair_count"]
    assert artifact["per_protein"] == fresh["per_protein"]
    assert check_summary(LAB, SOURCE_CACHE, LAB / "summary.json") == []


def test_committed_summary_satisfies_local_contract():
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert artifact["archive_counts"] == EXPECTED_COUNTS
    assert validate_summary(artifact) == []


def test_changed_summary_is_detected(tmp_path, monkeypatch):
    expected = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert validate_summary(expected) == []
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    artifact["per_protein"][0]["measurement_count"] += 1
    output = tmp_path / "summary.json"
    output.write_text(json.dumps(artifact), encoding="utf-8")
    # Source re-reading is covered separately; here only the saved census is mutated.
    monkeypatch.setattr(summary_module, "build_summary", lambda *_args, **_kwargs: expected)
    assert check_summary(LAB, SOURCE_CACHE, output)
