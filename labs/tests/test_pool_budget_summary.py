"""Public summaries preserve every policy and exclude local execution details."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.pool_budget_summary import SummaryContractError, build_public_summary

ROOT = Path(__file__).resolve().parents[2]


def example_metrics():
    assays = {}
    for assay, counts, groups, q, top in (
        ("CHEMBL5736995", (90, 631, 181), (62, 97, 79), 31, 64),
        ("CHEMBL3705421", (12, 130, 28), (10, 1, 12), 6, 13),
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
                "top_decile_size": top,
            },
            "policies": [
                {
                    "name": name,
                    "recovery": [0.0] * 5,
                    "normalized_auc": 0.0,
                    "scaffold_fraction": [0.0, 1.0, 1.0, 1.0, 1.0]
                    if groups[1] == 1
                    else [0.0, 0.1, 0.2, 0.3, 0.4],
                    "evaluation_mae": [0.5] * 5,
                }
                for name in ("maxmin", "random-0", "random-1", "random-2", "random-3", "random-4")
            ],
        }
    return {
        "protocol_id": "chembl37-egfr-pool-budget-v1",
        "status": "completed",
        "completed_at": "2026-09-08T08:08:15.994097+00:00",
        "assays": assays,
        "software": {
            "python": "3.11.15",
            "numpy": "2.4.6",
            "rdkit": "2025.9.6",
            "scikit-learn": "1.9.0",
        },
    }


def test_export_preserves_zero_results_and_every_declared_policy_and_round():
    metrics = example_metrics()
    summary = build_public_summary(metrics)
    assert summary["completed_on"] == "2026-09-08"
    assert summary["assays"] == metrics["assays"]
    assert summary["assays"]["CHEMBL3705421"]["policies"][0]["normalized_auc"] == 0
    metrics["assays"]["CHEMBL5736995"]["policies"][0]["recovery"][1] = 1
    assert summary["assays"]["CHEMBL5736995"]["policies"][0]["recovery"][1] == 0


def test_projection_does_not_copy_nested_private_fields():
    metrics = example_metrics()
    metrics["approval_receipt"] = "PRIVATE_SENTINEL"
    metrics["software"]["host"] = "PRIVATE_SENTINEL"
    assay = metrics["assays"]["CHEMBL5736995"]
    assay["parent_ids"] = ["PRIVATE_SENTINEL"]
    assay["partitions"]["evaluation"]["members"] = ["PRIVATE_SENTINEL"]
    assay["budget"]["run_id"] = "PRIVATE_SENTINEL"
    assay["policies"][0]["predictions"] = ["PRIVATE_SENTINEL"]
    text = json.dumps(build_public_summary(metrics))
    assert "PRIVATE_SENTINEL" not in text
    assert "approval_receipt" not in text
    assert "parent_ids" not in text


@pytest.mark.parametrize(
    "mutation", ["incomplete", "missing_seed", "missing_round", "nan", "budget", "auc", "counts"]
)
def test_invalid_or_incomplete_result_cannot_be_exported(mutation):
    metrics = example_metrics()
    assay = metrics["assays"]["CHEMBL5736995"]
    if mutation == "incomplete":
        metrics["status"] = "started"
    elif mutation == "missing_seed":
        assay["policies"].pop()
    elif mutation == "missing_round":
        assay["policies"][0]["evaluation_mae"].pop()
    elif mutation == "nan":
        assay["policies"][0]["evaluation_mae"][4] = float("nan")
    elif mutation == "budget":
        assay["budget"]["actual_budget_fraction"] = 0.2
    elif mutation == "auc":
        assay["policies"][0]["normalized_auc"] = 0.3
    else:
        assay["partitions"]["pool"]["parents"] = 630
    with pytest.raises(SummaryContractError):
        build_public_summary(metrics)


def test_delivered_summary_matches_saved_aggregate_when_local_evidence_exists():
    path = ROOT / "labs/pool_budget/results/locked-metrics.json"
    if not path.exists():
        pytest.skip("local execution artifacts are not distributed")
    metrics = json.loads(path.read_text())
    delivered = json.loads((ROOT / "labs/pool_budget/real-summary.json").read_text())
    assert delivered == build_public_summary(copy.deepcopy(metrics))
