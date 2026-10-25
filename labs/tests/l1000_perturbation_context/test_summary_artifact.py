"""The committed public summary must be internally consistent, independent of
whether the local real-data cache that produced it is present."""

from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.l1000_perturbation_context.protocol import CELL_LINE_A, CELL_LINE_B, PROTOCOL_ID
from aidd_commons.l1000_perturbation_context.summary import DIVERGENT_EXAMPLE_COUNT

ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = ROOT / "labs/l1000_perturbation_context/summary.json"


def load_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_committed_summary_matches_the_frozen_protocol_and_cell_lines() -> None:
    summary = load_summary()
    assert summary["protocol_id"] == PROTOCOL_ID
    assert set(summary["cell_lines"]) == {CELL_LINE_A, CELL_LINE_B}


def test_committed_summary_shared_count_is_internally_consistent() -> None:
    summary = load_summary()
    shared = summary["shared_compound_count"]
    assert shared == summary["matched"]["count"] == summary["null_mismatched"]["count"]
    assert shared <= min(
        summary["cell_lines"][CELL_LINE_A]["admitted_entity_count"],
        summary["cell_lines"][CELL_LINE_B]["admitted_entity_count"],
    )


def test_committed_summary_rank_sum_test_consumed_the_full_samples() -> None:
    summary = load_summary()
    comparison = summary["rank_sum_comparison"]
    assert comparison["matched_count"] == summary["matched"]["count"]
    assert comparison["null_count"] == summary["null_mismatched"]["count"]
    assert 0.0 <= comparison["p_value"] <= 1.0


def test_committed_summary_distributions_are_bounded() -> None:
    summary = load_summary()
    for key in ("matched", "null_mismatched"):
        assert -1.0 <= summary[key]["median"] <= 1.0
        assert -1.0 <= summary[key]["mean"] <= 1.0
        assert 0.0 <= summary[key]["fraction_positive"] <= 1.0


def test_committed_summary_carries_a_fixed_number_of_named_examples_each_way() -> None:
    summary = load_summary()
    examples = summary["examples"]
    assert len(examples["most_reproducible"]) == DIVERGENT_EXAMPLE_COUNT
    assert len(examples["most_divergent"]) == DIVERGENT_EXAMPLE_COUNT
    reproducible_rhos = [e["spearman_rho"] for e in examples["most_reproducible"]]
    divergent_rhos = [e["spearman_rho"] for e in examples["most_divergent"]]
    assert reproducible_rhos == sorted(reproducible_rhos, reverse=True)
    assert divergent_rhos == sorted(divergent_rhos)


def test_committed_summary_excludes_raw_expression_vectors_and_bulk_lists() -> None:
    summary = load_summary()
    for cell_line in summary["cell_lines"].values():
        assert set(cell_line) == {
            "input_rows",
            "retained_rows",
            "admitted_entity_count",
            "duplicate_entity_count",
            "exclusion_counts",
        }
