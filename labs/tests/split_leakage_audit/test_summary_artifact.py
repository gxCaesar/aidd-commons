"""The committed summary is a bounded count artifact, not activity data."""

from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.split_leakage_audit.protocol import ROUTES, UNTESTABLE
from aidd_commons.split_leakage_audit.summary import validate_summary

ROOT = Path(__file__).resolve().parents[3]
SUMMARY = ROOT / "labs/split_leakage_audit/summary.json"


def test_summary_counts_and_scope() -> None:
    raw = SUMMARY.read_text(encoding="utf-8")
    summary = json.loads(raw)
    assert validate_summary(summary) == []
    assert summary["admitted_point_row_count"] == 488
    assert summary["admitted_measurement_count"] == 486
    assert set(summary["routes"]) == set(ROUTES)
    assert summary["untestable_routes"] == UNTESTABLE
    assert summary["aggregate"]["contributing_routes"] == sum(
        item["test_rows_with_train_group"] > 0 for item in summary["routes"].values()
    )
    assert summary["aggregate"]["contaminated_test_rows"] >= max(
        item["test_rows_with_train_group"] for item in summary["routes"].values()
    )
    assert '"activities"' not in raw
    assert "canonical_smiles" not in raw
    assert len(raw) < 20_000
