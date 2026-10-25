"""Integration checks against the real, cached ChEMBL snapshot.

The snapshot lives in the git-ignored `.cache/az_clearance_system/` and is
not distributed with the repository or the curated public release, so these
tests skip rather than fail when it is absent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from aidd_commons.az_clearance_system.analysis import correlation_summary, overlap_records
from aidd_commons.az_clearance_system.data import load_cached_systems
from aidd_commons.az_clearance_system.protocol import SYSTEMS

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/az_clearance_system"
CACHE_DIR = ROOT / ".cache/az_clearance_system"
SUMMARY_PATH = LAB / "summary.json"

pytestmark = pytest.mark.skipif(
    not (CACHE_DIR / "status.json").is_file(),
    reason="the real ChEMBL snapshot cache is not present; run "
    "'python labs/az_clearance_system/run_lab.py download' to fetch it",
)


def test_cached_snapshot_reproduces_the_committed_public_summary() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    datasets = load_cached_systems(CACHE_DIR)

    for assay_id in SYSTEMS:
        assert len(datasets[assay_id].records) == summary["systems"][assay_id]["admitted_parents"]

    for pair_key, pair in summary["pairs"].items():
        overlap = overlap_records(
            datasets[pair["primary_system"]], datasets[pair["secondary_system"]]
        )
        clean = tuple(r for r in overlap if r.is_clean_single_pair)
        assert len(overlap) == pair["overlap_count"], pair_key
        assert len(clean) == pair["clean_pair_count"], pair_key
        correlation = correlation_summary(overlap)
        assert correlation.spearman_rho == pytest.approx(
            pair["correlation"]["spearman_rho"], abs=1e-9
        ), pair_key


def test_inspect_cli_show_and_check_run_cleanly_against_the_cache() -> None:
    for action in ("show", "check"):
        result = subprocess.run(
            [sys.executable, str(LAB / "inspect_az_clearance_system.py"), action],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
    assert "All checks passed" in result.stdout
