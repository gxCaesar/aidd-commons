"""The committed summary must be internally consistent on its own terms.

The committed `summary.json` is what a reader without the cache sees, so it
has to close on itself: the counts must partition, the survival ratios must
be the ratios of the numbers printed beside them, the examples must be the
ends of the distribution they claim to be, and the file must carry no raw
rows and no per-perturbation values.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.rosetta_cross_modality.protocol import load_contract
from aidd_commons.rosetta_cross_modality.summary import COMMITTED_FIELDS

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/rosetta_cross_modality"
SUMMARY_PATH = LAB / "summary.json"
CONTRACT_PATH = LAB / "protocol.json"


def load_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_the_committed_summary_carries_the_frozen_protocol_and_its_date() -> None:
    summary = load_summary()
    contract = load_contract(CONTRACT_PATH)
    assert summary["protocol_id"] == contract.protocol_id
    assert summary["schema_version"] == "aidd-commons.rosetta-cross-modality-summary.v1"
    assert summary["computed_on"] >= "2026-10-21"
    assert set(summary["software"]) == {"python", "numpy"}


def test_the_committed_summary_carries_only_the_committed_fields() -> None:
    summary = load_summary()
    assert set(summary) == set(COMMITTED_FIELDS)


def test_the_committed_counts_partition_every_row_of_both_readouts() -> None:
    summary = load_summary()
    counts = summary["counts"]
    for modality in ("transcriptome", "imaging"):
        block = counts[modality]
        assert block["control_rows"] + block["treated_rows"] == block["input_rows"]
        assert block["distinct_wells"] == block["input_rows"]
        assert block["perturbations"] > 0
        assert block["plates"] > 0
    assert counts["imaging"]["batches"] == 2
    assert (
        counts["batch_pure_perturbations"] + counts["batch_mixed_perturbations"]
        == counts["admitted_perturbations"]
    )
    assert counts["admitted_perturbations"] == counts["transcriptome"]["perturbations"]
    assert counts["admitted_perturbations"] <= counts["imaging"]["perturbations"]


def test_the_committed_feature_counts_match_the_declared_naming_rules() -> None:
    summary = load_summary()
    assert summary["features"]["transcriptome"] == 978
    assert summary["features"]["imaging"] == 291


def test_the_committed_variance_attribution_closes() -> None:
    summary = load_summary()
    for block in summary["variance_attribution"].values():
        assert block["between"] + block["within"] == pytest.approx(1.0)
        assert 0.0 <= block["between"] <= 1.0


def test_every_committed_evaluation_reports_a_bounded_agreement() -> None:
    summary = load_summary()
    evaluations = summary["evaluations"]
    assert set(evaluations) == {
        "apparent",
        "null_within_batch_permuted",
        "batch_blocked",
        "size_matched_random_batch",
        "plate_blocked_imaging",
        "size_matched_random_imaging_plate",
        "plate_blocked_transcriptome",
        "size_matched_random_transcriptome_plate",
    }
    for block in evaluations.values():
        assert block["folds"] >= 1
        assert block["tested_perturbations"] > 0
        assert -1.0 <= block["perturbation_r"] <= 1.0
        assert -1.0 <= block["feature_r"] <= 1.0
        assert len(block["train_sizes"]) == block["folds"]
        assert len(block["test_sizes"]) == block["folds"]
        assert len(block["alphas"]) == block["folds"]
        assert all(alpha > 0 for alpha in block["alphas"])


def test_the_blocked_evaluations_are_read_against_their_size_matched_control() -> None:
    summary = load_summary()
    evaluations = summary["evaluations"]
    for blocked, control in (
        ("batch_blocked", "size_matched_random_batch"),
        ("plate_blocked_imaging", "size_matched_random_imaging_plate"),
        ("plate_blocked_transcriptome", "size_matched_random_transcriptome_plate"),
    ):
        assert evaluations[blocked]["train_sizes"] == evaluations[control]["train_sizes"]
        assert evaluations[blocked]["test_sizes"] == evaluations[control]["test_sizes"]


def test_the_committed_survival_ratios_recompute_from_the_committed_numbers() -> None:
    summary = load_summary()
    evaluations = summary["evaluations"]
    survival = summary["survival"]
    apparent = evaluations["apparent"]["feature_r"]
    null = evaluations["null_within_batch_permuted"]["feature_r"]
    assert null < apparent
    for blocked, key in (
        ("batch_blocked", "batch_blocked_feature_r_survival"),
        ("plate_blocked_imaging", "plate_blocked_imaging_feature_r_survival"),
        ("plate_blocked_transcriptome", "plate_blocked_transcriptome_feature_r_survival"),
    ):
        expected = (evaluations[blocked]["feature_r"] - null) / (apparent - null)
        assert survival[key] == pytest.approx(expected, abs=1e-12)
    for blocked, control, key in (
        (
            "batch_blocked",
            "size_matched_random_batch",
            "batch_blocked_minus_size_matched_random_feature_r",
        ),
        (
            "plate_blocked_imaging",
            "size_matched_random_imaging_plate",
            "plate_blocked_imaging_minus_size_matched_random_feature_r",
        ),
        (
            "plate_blocked_transcriptome",
            "size_matched_random_transcriptome_plate",
            "plate_blocked_transcriptome_minus_size_matched_random_feature_r",
        ),
    ):
        expected = evaluations[blocked]["feature_r"] - evaluations[control]["feature_r"]
        assert survival[key] == pytest.approx(expected, abs=1e-12)


def test_the_permuted_null_is_near_zero_while_the_agreement_is_not() -> None:
    summary = load_summary()
    evaluations = summary["evaluations"]
    assert abs(evaluations["null_within_batch_permuted"]["feature_r"]) < 0.1
    assert evaluations["apparent"]["feature_r"] > 0.5
    free = summary["model_free_check"]
    assert free["neighbourhood_concordance"] > 0.3
    assert abs(free["neighbourhood_concordance_permuted_null"]) < 0.1


def test_the_committed_examples_are_the_ends_of_the_distribution() -> None:
    summary = load_summary()
    examples = summary["examples"]
    contract = load_contract(CONTRACT_PATH)
    for key in ("most_agreeable", "least_agreeable"):
        assert len(examples[key]) == contract.example_count
        for example in examples[key]:
            assert example["allele"]
            assert example["gene_symbol"]
            assert example["perturbation"]
            assert -1.0 <= example["perturbation_r"] <= 1.0
    highest = [example["perturbation_r"] for example in examples["most_agreeable"]]
    lowest = [example["perturbation_r"] for example in examples["least_agreeable"]]
    assert min(highest) > max(lowest)


def test_the_committed_summary_carries_no_raw_rows_and_no_per_perturbation_values() -> None:
    summary = load_summary()
    assert "per_perturbation_agreement" not in summary
    for key in ("counts", "features", "variance_attribution", "evaluations", "survival",
                "model_free_check", "examples", "source"):
        assert "rows" not in json.dumps(summary[key]).replace("input_rows", "").replace(
            "treated_rows", ""
        ).replace("control_rows", "").replace("distinct_wells", "").replace(
            "test_sizes", ""
        ).replace("train_sizes", "")
    assert len(summary["examples"]["most_agreeable"]) <= 3
    assert len(summary["examples"]["least_agreeable"]) <= 3
