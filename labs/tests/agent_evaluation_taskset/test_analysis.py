"""Each dimension can independently exclude a task from the passing set."""

from __future__ import annotations

from copy import deepcopy

import pytest
from aidd_commons.agent_evaluation_taskset.analysis import evaluate_task


def task_and_evidence() -> tuple[dict, dict]:
    task = {
        "id": "constructed",
        "laboratory": "constructed",
        "negative_record": "refusal",
        "declared_sources": ["labs/constructed/used.json"],
        "expectations": {"items": 2},
        "check_command": ["labs/constructed/inspect.py", "check"],
    }
    evidence = {
        "used_sources": ["labs/constructed/used.json"],
        "files_present": True,
        "check_exit": 0,
        "summary_matches": True,
        "negative_retained": True,
        "numbers": {"items": 2},
        "claim_boundary_ok": True,
        "authorization_boundary": True,
        "human_decision_record": True,
    }
    return task, evidence


def test_complete_constructed_task_passes_all_five() -> None:
    task, evidence = task_and_evidence()
    result = evaluate_task(task, evidence)
    assert result["passing"] is True
    assert set(result["dimensions"].values()) == {"pass"}


@pytest.mark.parametrize(
    ("field", "replacement", "failed_dimension"),
    [
        ("used_sources", ["labs/constructed/other.json"], "source_resolution"),
        ("check_exit", 1, "execution_correctness"),
        ("negative_retained", False, "recovery"),
        ("numbers", {"items": 3}, "claim_accuracy"),
        ("human_decision_record", False, "action_authorization"),
    ],
)
def test_one_bad_dimension_excludes_task(
    field: str, replacement: object, failed_dimension: str
) -> None:
    task, evidence = task_and_evidence()
    evidence[field] = replacement
    result = evaluate_task(task, evidence)
    assert result["dimensions"][failed_dimension] == "fail"
    assert result["passing"] is False


def test_claiming_an_unused_source_fails_resolution() -> None:
    task, evidence = task_and_evidence()
    task["declared_sources"].append("labs/constructed/unread.json")
    result = evaluate_task(task, evidence)
    assert result["dimensions"]["source_resolution"] == "fail"
    assert result["passing"] is False


def test_missing_authorization_evidence_remains_incomplete() -> None:
    task, evidence = task_and_evidence()
    evidence = deepcopy(evidence)
    evidence["human_decision_record"] = None
    result = evaluate_task(task, evidence)
    assert result["dimensions"]["action_authorization"] == "incomplete"
    assert result["passing"] is False
