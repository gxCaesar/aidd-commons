"""Public summaries preserve the one declared policy and exclude local execution details."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.pool_budget_uncertainty_summary import (
    UncertaintySummaryContractError,
    build_public_uncertainty_summary,
)

ROOT = Path(__file__).resolve().parents[2]


def example_metrics():
    assays = {}
    for assay, counts, groups, q in (
        ("CHEMBL5736995", (90, 631, 181), (62, 97, 79), 31),
        ("CHEMBL3705421", (12, 130, 28), (10, 1, 12), 6),
    ):
        assays[assay] = {
            "partitions": {
                name: {"parents": parents, "groups": group_count}
                for name, parents, group_count in zip(
                    ("initial", "pool", "evaluation"), counts, groups, strict=True
                )
            },
            "budget": {
                "checkpoints": [0, q, 2 * q, 3 * q, 4 * q],
                "batch_size": q,
                "acquired_count": 4 * q,
                "original_pool_parent_count": counts[1],
                "actual_budget_fraction": 4 * q / counts[1],
            },
            "policy": {
                "name": "ensemble-variance-uncertainty",
                "recovery": [0.0, 0.1, 0.2, 0.3, 0.4],
                "scaffold_fraction": [0.0, 0.1, 0.2, 0.3, 0.4],
                "evaluation_mae": [0.5] * 5,
            },
        }
        # normalized_auc via the trapezoid rule over the declared recovery curve
        recovery = assays[assay]["policy"]["recovery"]
        assays[assay]["policy"]["normalized_auc"] = sum(
            (a + b) / 2 * q for a, b in zip(recovery, recovery[1:], strict=False)
        ) / (4 * q)
    return {
        "protocol_id": "chembl37-egfr-pool-budget-uncertainty-v1",
        "status": "completed",
        "completed_at": "2026-09-11T17:33:42.148035+00:00",
        "assays": assays,
        "software": {
            "python": "3.11.15",
            "numpy": "2.4.6",
            "rdkit": "2025.9.6",
            "scikit-learn": "1.9.0",
        },
    }


def test_export_preserves_the_curve_and_excludes_it_from_aliasing():
    metrics = example_metrics()
    summary = build_public_uncertainty_summary(metrics)
    assert summary["completed_on"] == "2026-09-11"
    assert summary["assays"] == metrics["assays"]
    metrics["assays"]["CHEMBL5736995"]["policy"]["recovery"][1] = 1
    assert summary["assays"]["CHEMBL5736995"]["policy"]["recovery"][1] != 1


def test_projection_does_not_copy_nested_private_fields():
    metrics = example_metrics()
    metrics["approval_receipt"] = "PRIVATE_SENTINEL"
    metrics["software"]["host"] = "PRIVATE_SENTINEL"
    assay = metrics["assays"]["CHEMBL5736995"]
    assay["parent_ids"] = ["PRIVATE_SENTINEL"]
    assay["policy"]["acquisition_order"] = ["PRIVATE_SENTINEL"]
    text = json.dumps(build_public_uncertainty_summary(metrics))
    assert "PRIVATE_SENTINEL" not in text
    assert "approval_receipt" not in text
    assert "parent_ids" not in text


@pytest.mark.parametrize(
    "mutation", ["incomplete", "wrong_protocol", "nan", "budget", "auc", "counts", "policy_name"]
)
def test_invalid_or_incomplete_result_cannot_be_exported(mutation):
    metrics = example_metrics()
    assay = metrics["assays"]["CHEMBL5736995"]
    if mutation == "incomplete":
        metrics["status"] = "started"
    elif mutation == "wrong_protocol":
        metrics["protocol_id"] = "chembl37-egfr-pool-budget-v1"
    elif mutation == "nan":
        assay["policy"]["evaluation_mae"][4] = float("nan")
    elif mutation == "budget":
        assay["budget"]["actual_budget_fraction"] = 0.2
    elif mutation == "auc":
        assay["policy"]["normalized_auc"] = 0.3
    elif mutation == "policy_name":
        assay["policy"]["name"] = "maxmin"
    else:
        assay["partitions"]["pool"]["parents"] = 630
    with pytest.raises(UncertaintySummaryContractError):
        build_public_uncertainty_summary(metrics)


def test_delivered_summary_matches_saved_aggregate_when_local_evidence_exists():
    path = ROOT / "labs/pool_budget/uncertainty-results/uncertainty-locked-metrics.json"
    if not path.exists():
        pytest.skip("local execution artifacts are not distributed")
    metrics = json.loads(path.read_text())
    delivered = json.loads((ROOT / "labs/pool_budget/uncertainty-summary.json").read_text())
    assert delivered == build_public_uncertainty_summary(copy.deepcopy(metrics))
