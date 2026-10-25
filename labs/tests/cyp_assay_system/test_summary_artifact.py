"""The committed public summary must be internally consistent, independent of
whether the local real-data cache that produced it is present."""

from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.cyp_assay_system.protocol import PROTOCOL_ID, TARGETS
from aidd_commons.cyp_assay_system.summary import DIVERGENT_EXAMPLE_COUNT

ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = ROOT / "labs/cyp_assay_system/summary.json"


def load_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_committed_summary_matches_the_frozen_protocol_and_target_ids() -> None:
    summary = load_summary()
    assert summary["protocol_id"] == PROTOCOL_ID
    assert set(summary["targets"]) == set(TARGETS)
    for target_id, name in TARGETS.items():
        assert summary["targets"][target_id]["name"] == name


def test_committed_summary_overlap_counts_are_internally_consistent() -> None:
    summary = load_summary()
    overlap = summary["overlap"]
    assert (
        0
        <= overlap["clean_pair_count"]
        <= overlap["shares_document_count"]
        <= overlap["full_count"]
    )
    primary_id, secondary_id = TARGETS
    assert overlap["full_count"] <= min(
        summary["targets"][primary_id]["admitted_parents"],
        summary["targets"][secondary_id]["admitted_parents"],
    )


def test_committed_summary_correlation_counts_match_declared_overlap() -> None:
    summary = load_summary()
    assert summary["correlation"]["full"]["count"] == summary["overlap"]["full_count"]
    assert (
        summary["correlation"]["clean_pairs_only"]["count"]
        == summary["overlap"]["clean_pair_count"]
    )
    for key in ("full", "clean_pairs_only"):
        assert -1.0 <= summary["correlation"][key]["pearson_r"] <= 1.0
        assert -1.0 <= summary["correlation"][key]["spearman_rho"] <= 1.0


def test_committed_summary_carries_a_fixed_number_of_named_examples_each_way() -> None:
    summary = load_summary()
    examples = summary["divergent_examples"]
    assert len(examples["primary_selective"]) == DIVERGENT_EXAMPLE_COUNT
    assert len(examples["secondary_selective"]) == DIVERGENT_EXAMPLE_COUNT
    for example in examples["primary_selective"]:
        assert example["difference"] > 0
    for example in examples["secondary_selective"]:
        assert example["difference"] < 0


def test_committed_summary_excludes_raw_activity_rows_and_bulk_compound_lists() -> None:
    summary = load_summary()
    audits = [summary["targets"][t]["audit"] for t in TARGETS]
    for audit in audits:
        assert set(audit) == {
            "input_rows",
            "retained_rows",
            "parent_count",
            "duplicate_parent_count",
            "median_duplicate_range",
            "maximum_duplicate_range",
            "exclusion_counts",
        }
