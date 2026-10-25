"""The committed public summary must be internally consistent, independent of
whether the local real-data cache that produced it is present."""

from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.az_clearance_system.analysis import SYSTEM_PAIRS
from aidd_commons.az_clearance_system.protocol import PROTOCOL_ID, SYSTEMS
from aidd_commons.az_clearance_system.summary import DIVERGENT_EXAMPLE_COUNT

ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = ROOT / "labs/az_clearance_system/summary.json"


def load_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_committed_summary_matches_the_frozen_protocol_and_system_ids() -> None:
    summary = load_summary()
    assert summary["protocol_id"] == PROTOCOL_ID
    assert set(summary["systems"]) == set(SYSTEMS)
    for assay_id, (name, species, matrix) in SYSTEMS.items():
        assert summary["systems"][assay_id]["name"] == name
        assert summary["systems"][assay_id]["species"] == species
        assert summary["systems"][assay_id]["matrix"] == matrix


def test_committed_summary_reports_exactly_the_declared_pairs() -> None:
    summary = load_summary()
    expected_keys = {f"{a}_vs_{b}" for a, b, _ in SYSTEM_PAIRS}
    assert set(summary["pairs"]) == expected_keys


def test_committed_summary_pair_counts_are_internally_consistent() -> None:
    summary = load_summary()
    for pair in summary["pairs"].values():
        assert 0 <= pair["clean_pair_count"] <= pair["overlap_count"]
        primary_admitted = summary["systems"][pair["primary_system"]]["admitted_parents"]
        secondary_admitted = summary["systems"][pair["secondary_system"]]["admitted_parents"]
        assert pair["overlap_count"] <= min(primary_admitted, secondary_admitted)
        assert pair["correlation"]["count"] == pair["overlap_count"]
        assert -1.0 <= pair["correlation"]["pearson_r"] <= 1.0
        assert -1.0 <= pair["correlation"]["spearman_rho"] <= 1.0


def test_committed_summary_carries_a_fixed_number_of_named_examples_each_way() -> None:
    summary = load_summary()
    for pair in summary["pairs"].values():
        examples = pair["divergent_examples"]
        assert len(examples["primary_selective"]) == DIVERGENT_EXAMPLE_COUNT
        assert len(examples["secondary_selective"]) == DIVERGENT_EXAMPLE_COUNT
        for example in examples["primary_selective"]:
            assert example["log_ratio"] > 0
        for example in examples["secondary_selective"]:
            assert example["log_ratio"] < 0


def test_committed_summary_excludes_raw_activity_rows_and_bulk_compound_lists() -> None:
    summary = load_summary()
    for system in summary["systems"].values():
        assert set(system["audit"]) == {
            "input_rows",
            "retained_rows",
            "parent_count",
            "duplicate_parent_count",
            "median_duplicate_range",
            "maximum_duplicate_range",
            "exclusion_counts",
        }
