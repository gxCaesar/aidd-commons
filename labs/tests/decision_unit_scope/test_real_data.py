"""Integration checks against the real, cached ChEMBL 37 snapshot.

The snapshot lives in the git-ignored `.cache/decision_unit_scope/` and is not
distributed with the repository or the curated public release, so these tests
skip rather than fail when it is absent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from aidd_commons.decision_unit_scope.analysis import census_cohort
from aidd_commons.decision_unit_scope.data import load_cached_cohort
from aidd_commons.decision_unit_scope.protocol import COHORT_PARENTS

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/decision_unit_scope"
CACHE_DIR = ROOT / ".cache/decision_unit_scope"
SUMMARY_PATH = LAB / "summary.json"

pytestmark = pytest.mark.skipif(
    not (CACHE_DIR / "status.json").is_file(),
    reason="the real ChEMBL snapshot cache is not present; run "
    "'python labs/decision_unit_scope/run_lab.py download' to fetch it",
)


def test_the_cached_snapshot_reproduces_the_committed_public_summary() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    cohort = load_cached_cohort(CACHE_DIR)
    census = census_cohort(cohort)

    assert census.reported_row_count == summary["cohort"]["reported_row_count"]
    assert census.admitted_point_count == summary["cohort"]["admitted_point_count"]
    assert census.admitted_bound_count == summary["cohort"]["admitted_bound_count"]
    assert (
        census.independent_measurement_count
        == summary["cohort"]["independent_measurement_count"]
    )
    assert (
        census.independent_experiment_count
        == summary["cohort"]["independent_experiment_count"]
    )
    assert dict(census.exclusion_counts) == dict(summary["cohort"]["exclusion_counts"])

    by_id = {entry["parent_molecule_chembl_id"]: entry for entry in summary["cohort"]["parents"]}
    assert set(by_id) == set(COHORT_PARENTS)
    for item in census.parents:
        entry = by_id[item.parent_molecule_chembl_id]
        assert entry["reported_row_count"] == item.reported_row_count
        assert entry["admitted_point_count"] == item.admitted_point_count
        assert entry["admitted_bound_count"] == item.admitted_bound_count
        assert entry["independent_measurement_count"] == item.independent_measurement_count
        assert entry["distinct_assay_count"] == item.distinct_assay_count
        assert entry["salt_form_point_count"] == item.salt_form_point_count
        assert dict(entry["exclusion_counts"]) == dict(item.exclusion_counts)


def test_the_declared_seeds_really_do_collapse_onto_the_declared_parents() -> None:
    cohort = load_cached_cohort(CACHE_DIR)
    resolved = {record.parent_molecule_chembl_id for record in cohort.molecules.values()}
    assert resolved == set(COHORT_PARENTS)
    assert len(cohort.molecules) > len(resolved), (
        "the declared cohort must contain at least one salt that resolves onto a parent "
        "that is itself in the cohort"
    )
    multi_component = [
        record.pref_name
        for record in cohort.molecules.values()
        if record.fragment_count > 1
    ]
    assert multi_component, "the declared cohort must contain at least one multi-component entity"


def test_the_inspect_cli_show_and_check_run_cleanly_against_the_cache() -> None:
    for action in ("show", "check"):
        result = subprocess.run(
            [sys.executable, str(LAB / "inspect_decision_unit_scope.py"), action],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stderr
    assert "All checks passed" in result.stdout
