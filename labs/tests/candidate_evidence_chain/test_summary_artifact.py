"""The committed small summary must agree with validated cached measurements."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import aidd_commons.candidate_evidence_chain.summary as summary_module
import pytest
from aidd_commons.candidate_evidence_chain.protocol import (
    PACKAGE_VERSION_FALLBACK,
    load_protocol_document,
)
from aidd_commons.candidate_evidence_chain.summary import build_summary, check_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/candidate_evidence_chain"


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_committed_summary_matches_cached_sources() -> None:
    load_protocol_document(LAB / "protocol.json")
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    computed = build_summary(ROOT / ".cache", computed_on=committed["computed_on"])
    check_summary(committed, computed)


def test_committed_summary_satisfies_local_contract() -> None:
    protocol = load_protocol_document(LAB / "protocol.json")
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    summary_module.audit_summary(committed)
    assert committed["protocol_id"] == protocol["protocol_id"]
    assert committed["claim_count"] == 0
    assert committed["first_non_measured_distribution"] == {"mechanism": 3}
    assert len(committed["chains"]) == 3
    assert "archive_rows" not in committed and "profiles" not in committed


def test_package_version_fallback_needs_no_repository_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_distribution(_name: str) -> str:
        raise PackageNotFoundError("aidd-commons-labs")

    monkeypatch.setattr(summary_module, "version", missing_distribution)
    assert summary_module.software_versions()["aidd_commons_labs"] == PACKAGE_VERSION_FALLBACK
