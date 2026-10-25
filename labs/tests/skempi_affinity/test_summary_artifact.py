"""The committed artifact agrees with a fresh computation from the cached source."""

import json
from pathlib import Path

import pytest
from aidd_commons.skempi_affinity.analysis import analyze, check_invariants
from aidd_commons.skempi_affinity.data import load_cached

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/skempi_affinity"
CACHE = ROOT / ".cache/skempi_affinity"


def test_observed_counts_and_committed_summary():
    if not CACHE.is_dir():
        pytest.skip("snapshot download has not run")
    result = analyze(load_cached(CACHE))
    artifact = json.loads((LAB / "summary.json").read_text())
    assert result["rows"] == 7085
    assert result["classes"]["AB/AG"]["rows"] == 830
    assert result["classes"]["AB/AG"]["complexes"] == 51
    assert result["classes"]["AB/AG"]["complete_pairs"] == 719
    assert result["classes"]["AB/AG"]["top_five_rows"] == 347
    assert result["classes"]["Pr/PI"]["top_five_share"] == pytest.approx(0.8401559454191033)
    assert result["classes"]["TCR/pMHC"]["complete_pairs"] == 2
    assert artifact["counts"]["rows"] == result["rows"]
    assert artifact["counts"]["field_counts"] == result["field_counts"]
    assert artifact["row_split_diagnostic"] == result["row_split_diagnostic"]
    assert artifact["complex_holdout"] == result["complex_holdout"]
    assert check_invariants(load_cached(CACHE), result) == []
