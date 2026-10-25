"""The committed compact result reconciles with the cached archive."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.pkpd_translation_audit.protocol import (
    BOUNDARY,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
)
from aidd_commons.pkpd_translation_audit.summary import check_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/pkpd_translation_audit"
CACHE = ROOT / ".cache/az_clearance_system"


def test_committed_summary_counts_reconcile() -> None:
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert summary["protocol_id"] == PROTOCOL_ID
    assert summary["boundary"] == BOUNDARY
    assert summary["cohort"]["unique_admitted_parents"] == 1120
    assert summary["cohort"]["modelled_parents"] == len(summary["per_compound_results"])
    assert summary["cohort"]["not_modelled_parents"] == sum(summary["uncarried_reasons"].values())
    assert len(summary["per_compound_columns"]) == len(summary["per_compound_results"][0])


@pytest.mark.skipif(not CACHE.is_dir(), reason="the AZ clearance ChEMBL snapshot is not cached")
def test_committed_summary_recomputes_and_counts_reconcile() -> None:
    assert not check_summary(LAB / "protocol.json", CACHE, LAB / "summary.json")
