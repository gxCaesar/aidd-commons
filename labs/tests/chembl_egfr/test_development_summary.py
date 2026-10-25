from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.chembl_egfr.pipeline import development_summary

REPOSITORY_ROOT = Path(__file__).parents[3]
SUMMARY_PATH = REPOSITORY_ROOT / "labs" / "chembl_egfr" / "development-summary.json"
PRETEST_PATH = REPOSITORY_ROOT / "labs" / "chembl_egfr" / "results" / "pretest.json"


def all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(all_keys(item) for item in value), set())
    return set()


def test_reviewed_development_summary_is_aggregate_and_keeps_locked_results_absent() -> None:
    text = SUMMARY_PATH.read_text(encoding="utf-8")
    summary = json.loads(text)

    assert summary["artifact_type"] == "reviewed-development-summary"
    assert summary["locked_evaluations"] == {
        "primary": "not_run",
        "replication": "not_run",
    }
    assert summary["split"]["actual_counts"] == {
        "train": 634,
        "validation": 136,
        "test": 132,
    }
    assert all_keys(summary).isdisjoint(
        {
            "command",
            "evaluation_command",
            "fit_trace",
            "grouping_keys",
            "ids",
            "membership",
            "parent_molecule_chembl_id",
            "predictions",
            "pretest_passed",
            "target_pchembl",
        }
    )
    assert "primary_test" not in text
    assert "assay_replication" not in text


def test_reviewed_summary_matches_canonical_pretest_when_available() -> None:
    if not PRETEST_PATH.exists():
        pytest.skip("full pretest evidence is intentionally absent from the public release")

    reviewed = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    assert reviewed == development_summary(PRETEST_PATH)
