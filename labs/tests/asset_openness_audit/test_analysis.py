"""The analysis counts distinct claims and literal scope limits."""

from pathlib import Path

from aidd_commons.asset_openness_audit.analysis import (
    analyze,
    audit_record,
    check_invariants,
    scope_limits_grant,
)
from aidd_commons.asset_openness_audit.protocol import EXAMINED_IDS
from aidd_commons.asset_openness_audit.records import load_catalogue

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = ROOT / "catalog/resources"


def test_one_record_retains_evidence_scope_and_caveats() -> None:
    record = load_catalogue(CATALOGUE)["model-boltz-2"]
    row = audit_record(record)
    assert row["errors"] == []
    assert row["dimensions"]["inference_code"]["evidence"] == ["readme"]
    assert row["evidence_entries"]["readme"]["url"].startswith("https://")
    assert row["licenses"][0]["scope"] == record["licenses"][0]["scope"]
    assert row["caveats"] == record["caveats"]
    assert row["scope_limits_grant"] is True


def test_scope_limit_is_literal_and_not_a_legal_conclusion() -> None:
    assert scope_limits_grant("source code only")
    assert scope_limits_grant("Weights are NOT included")
    assert scope_limits_grant("no separate terms stated")
    assert scope_limits_grant("does not cover datasets")
    assert not scope_limits_grant("Apache-2.0 inference-code")
    assert not scope_limits_grant("annotation package")


def test_aggregate_counts_recompute_from_catalogue() -> None:
    result = analyze(load_catalogue(CATALOGUE), EXAMINED_IDS)
    assert check_invariants(result, EXAMINED_IDS) == []
    assert result["examined_counts"] == {
        "available": 57,
        "not_applicable": 26,
        "unverified": 83,
        "not_available": 2,
        "records_with_license": 22,
        "records_without_verified_access": 0,
        "records_with_scope_limit": 9,
    }
    assert result["whole_catalogue"] == {
        "records": 228,
        "records_with_seven_separate_dimensions": 228,
    }
