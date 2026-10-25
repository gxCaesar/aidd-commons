"""The committed report must agree with the retained local source snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.free_energy_network_audit.protocol import load_protocol
from aidd_commons.free_energy_network_audit.summary import check_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/free_energy_network_audit"
CACHE = ROOT / ".cache/free_energy_network_audit"


def test_committed_summary_counts_reconcile() -> None:
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    protocol = load_protocol(LAB / "protocol.json")
    assert summary["protocol_id"] == protocol["protocol_id"]
    assert summary["endpoint_kind"] == "relative binding free energy"
    assert summary["totals"]["systems"] == 8
    assert sum(row["edge_count"] for row in summary["systems"]) == summary["totals"]["edges"]
    assert (
        sum(row["estimate_count"] for row in summary["systems"]) == summary["totals"]["estimates"]
    )
    assert all(
        row["cycle_count"] == row["closed_cycle_count"] + row["failed_cycle_count"]
        for row in summary["systems"]
    )


@pytest.mark.skipif(not CACHE.is_dir(), reason="the free-energy source archives are not cached")
def test_committed_summary_matches_archive() -> None:
    assert check_summary(LAB, CACHE, LAB / "summary.json") == []
