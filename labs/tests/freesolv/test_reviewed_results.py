from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).parents[3]
REVIEWED_PATH = REPOSITORY_ROOT / "labs" / "freesolv" / "reviewed-results.json"
CANONICAL_PATH = REPOSITORY_ROOT / "labs" / "freesolv" / "results" / "metrics.json"


def _aggregate_results(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        split_name: {
            "counts": split["membership"]["actual_counts"],
            "interval_metrics": split["test"]["interval_metrics"],
            "point_metrics": split["test"]["point_metrics"],
        }
        for split_name, split in metrics["splits"].items()
    }


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_reviewed_results_are_aggregate_only() -> None:
    reviewed_text = REVIEWED_PATH.read_text(encoding="utf-8")
    reviewed = json.loads(reviewed_text)

    assert reviewed["artifact_type"] == "reviewed-aggregate-results"
    assert reviewed["primary_split"] == "scaffold"
    assert set(reviewed["splits"]) == {"random", "scaffold"}
    assert set(reviewed["splits"]["scaffold"]["counts"]) == {
        "train",
        "validation",
        "test",
    }
    assert _all_keys(reviewed).isdisjoint(
        {
            "canonical_smiles",
            "command",
            "evaluation_command",
            "fit_trace",
            "grouping_key",
            "ids",
            "membership",
            "planned_test_evaluation_command",
            "pretest_passed",
            "source_id",
            "test_evaluation_complete",
        }
    )
    assert "mobley_" not in reviewed_text


def test_reviewed_results_match_the_canonical_result_when_available() -> None:
    if not CANONICAL_PATH.exists():
        pytest.skip("canonical run artifact is intentionally absent from the public release")

    reviewed = json.loads(REVIEWED_PATH.read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))

    assert reviewed["dataset"] == canonical["dataset"]
    assert reviewed["primary_split"] == canonical["primary_split"] == "scaffold"
    assert reviewed["splits"] == _aggregate_results(canonical)
