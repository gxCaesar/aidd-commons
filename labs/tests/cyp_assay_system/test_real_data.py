"""Integration checks against the real, cached ChEMBL snapshot.

The snapshot lives in the git-ignored `.cache/cyp_assay_system/` and is not
distributed with the repository or the curated public release, so these tests
skip rather than fail when it is absent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from aidd_commons.cyp_assay_system.analysis import correlation_summary, overlap_records
from aidd_commons.cyp_assay_system.data import load_cached_targets
from aidd_commons.cyp_assay_system.protocol import TARGETS

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/cyp_assay_system"
CACHE_DIR = ROOT / ".cache/cyp_assay_system"
SUMMARY_PATH = LAB / "summary.json"

pytestmark = pytest.mark.skipif(
    not (CACHE_DIR / "status.json").is_file(),
    reason="the real ChEMBL snapshot cache is not present; run "
    "'python labs/cyp_assay_system/run_lab.py download' to fetch it",
)


def test_cached_snapshot_reproduces_the_committed_public_summary() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    datasets = load_cached_targets(CACHE_DIR)
    primary_id, secondary_id = TARGETS
    primary, secondary = datasets[primary_id], datasets[secondary_id]

    assert len(primary.records) == summary["targets"][primary_id]["admitted_parents"]
    assert len(secondary.records) == summary["targets"][secondary_id]["admitted_parents"]

    overlap = overlap_records(primary, secondary)
    clean = tuple(r for r in overlap if r.is_clean_single_pair)
    assert len(overlap) == summary["overlap"]["full_count"]
    assert len(clean) == summary["overlap"]["clean_pair_count"]

    full_correlation = correlation_summary(overlap)
    assert full_correlation.spearman_rho == pytest.approx(
        summary["correlation"]["full"]["spearman_rho"], abs=1e-9
    )
    assert full_correlation.pearson_r == pytest.approx(
        summary["correlation"]["full"]["pearson_r"], abs=1e-9
    )


def test_inspect_cli_show_and_check_run_cleanly_against_the_cache() -> None:
    for action in ("show", "check"):
        result = subprocess.run(
            [sys.executable, str(LAB / "inspect_cyp_assay_system.py"), action],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
    assert "All checks passed" in result.stdout
