"""Integration checks against the real, cached LINCS L1000 snapshot.

The snapshot lives in the git-ignored `.cache/l1000_perturbation_context/`
and is not distributed with the repository or the curated public release,
so these tests skip rather than fail when it is absent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from aidd_commons.l1000_perturbation_context.analysis import (
    compare_matched_to_null,
    matched_pairs,
    null_pairs,
    shared_compounds,
    summarize,
)
from aidd_commons.l1000_perturbation_context.data import load_cached_cell_lines
from aidd_commons.l1000_perturbation_context.protocol import CELL_LINE_A, CELL_LINE_B, FILES

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/l1000_perturbation_context"
CACHE_DIR = ROOT / ".cache/l1000_perturbation_context"
SUMMARY_PATH = LAB / "summary.json"

_inst_filename, _ = FILES["inst_info"]

pytestmark = pytest.mark.skipif(
    not (CACHE_DIR / _inst_filename).is_file(),
    reason="the real LINCS L1000 snapshot cache is not present; run "
    "'python labs/l1000_perturbation_context/run_lab.py download' to fetch it",
)


def test_cached_snapshot_reproduces_the_committed_public_summary() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    datasets = load_cached_cell_lines(CACHE_DIR)
    a, b = datasets[CELL_LINE_A], datasets[CELL_LINE_B]

    assert len(a.signatures) == summary["cell_lines"][CELL_LINE_A]["admitted_entity_count"]
    assert len(b.signatures) == summary["cell_lines"][CELL_LINE_B]["admitted_entity_count"]
    assert len(shared_compounds(a, b)) == summary["shared_compound_count"]

    matched = matched_pairs(a, b)
    null = null_pairs(a, b)
    matched_summary = summarize(matched)
    null_summary = summarize(null)
    assert matched_summary.median == pytest.approx(summary["matched"]["median"], abs=1e-9)
    assert null_summary.median == pytest.approx(summary["null_mismatched"]["median"], abs=1e-9)
    comparison = compare_matched_to_null(matched, null)
    assert comparison.p_value == pytest.approx(summary["rank_sum_comparison"]["p_value"], rel=1e-6)


def test_inspect_cli_show_and_check_run_cleanly_against_the_cache() -> None:
    for action in ("show", "check"):
        result = subprocess.run(
            [sys.executable, str(LAB / "inspect_l1000_perturbation_context.py"), action],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stderr
    assert "All checks passed" in result.stdout
