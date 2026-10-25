"""The committed summary must match the validated source caches."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import aidd_commons.multi_endpoint_integration.summary as summary_module
import pytest
from aidd_commons.multi_endpoint_integration.protocol import (
    PACKAGE_VERSION_FALLBACK,
    load_protocol_document,
    validate_cache_lengths,
)
from aidd_commons.multi_endpoint_integration.summary import build_summary, check_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/multi_endpoint_integration"


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_committed_summary_matches_snapshots() -> None:
    load_protocol_document(LAB / "protocol.json")
    validate_cache_lengths(ROOT / ".cache")
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    computed = build_summary(ROOT / ".cache", computed_on=committed["computed_on"])
    check_summary(committed, computed)


def test_committed_summary_satisfies_local_contract() -> None:
    protocol = load_protocol_document(LAB / "protocol.json")
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    summary_module.audit_summary(committed)
    assert committed["protocol_id"] == protocol["protocol_id"]
    assert committed["counts"]["source_independent_activity_measurement_count"] == 486
    assert committed["counts"]["family_measurement_counts"] == {
        "efficacy": 462,
        "exposure": 1623,
        "interaction": 8032,
        "toxicity": 0,
    }
    assert committed["counts"]["profile_count"] == len(committed["profiles"])
    assert "activities" not in committed and "canonical_smiles" not in committed


def test_package_version_fallback_needs_no_repository_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_distribution(_name: str) -> str:
        raise PackageNotFoundError("aidd-commons-labs")

    monkeypatch.setattr(summary_module, "version", missing_distribution)
    assert summary_module.software_versions()["aidd_commons_labs"] == PACKAGE_VERSION_FALLBACK
