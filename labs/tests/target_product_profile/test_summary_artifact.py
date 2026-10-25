"""The committed small summary agrees with the cached source snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.target_product_profile.protocol import load_protocol_document
from aidd_commons.target_product_profile.summary import build_summary, check_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/target_product_profile"


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_committed_summary_matches_sources() -> None:
    load_protocol_document(LAB / "protocol.json")
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    check_summary(committed, build_summary(ROOT / ".cache"))
    assert committed["unmeasured_requirements"] == ["clinical_response", "immunogenicity"]
    assert committed["counts"]["profile_satisfying_compound_count"] == 0
    assert "profiles" not in committed
