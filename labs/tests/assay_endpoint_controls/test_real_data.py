"""Integration checks against the real, cached PubChem BioAssay archive.

The archive lives in the git-ignored `.cache/assay_endpoint_controls/` and is
not distributed with the repository or the curated public release, so these
tests skip rather than fail when it is absent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from aidd_commons.assay_endpoint_controls.analysis import assay_profile, relation_mix
from aidd_commons.assay_endpoint_controls.data import load_cached_assays
from aidd_commons.assay_endpoint_controls.pipeline import (
    load_protocol,
    validate_protocol_contract,
)
from aidd_commons.assay_endpoint_controls.protocol import DECLARED_ASSAYS, SPLIT_SEED

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/assay_endpoint_controls"
CACHE_DIR = ROOT / ".cache/assay_endpoint_controls"
SUMMARY_PATH = LAB / "summary.json"

pytestmark = pytest.mark.skipif(
    not (CACHE_DIR / "aid548.csv").is_file(),
    reason="the real PubChem BioAssay archive is not present; run "
    "'python labs/assay_endpoint_controls/run_lab.py download' to fetch it",
)


def test_the_cached_archive_reproduces_the_committed_public_summary() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    datasets = load_cached_assays(CACHE_DIR)
    for aid in DECLARED_ASSAYS:
        profile = assay_profile(datasets[aid], seed=SPLIT_SEED)
        committed = summary["assays"][str(aid)]
        assert profile.admitted_compounds == committed["audit"]["admitted_compounds"]
        assert profile.retained_rows == committed["audit"]["retained_rows"]
        assert dict(profile.relation_mix.counts) == committed["relation_mix"]["counts"]
    assert dict(relation_mix(datasets).counts) == summary["relation_mix"]["counts"]


def test_the_frozen_protocol_still_matches_the_frozen_contract() -> None:
    validate_protocol_contract(load_protocol(ROOT))


def test_the_inspect_cli_show_and_check_run_cleanly_against_the_cache() -> None:
    for action in ("show", "check"):
        result = subprocess.run(
            [sys.executable, str(LAB / "inspect_assay_endpoint_controls.py"), action],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, result.stderr
    assert "All checks passed" in result.stdout


def test_the_pipeline_writes_one_report_and_nothing_else(tmp_path: Path) -> None:
    from aidd_commons.assay_endpoint_controls.pipeline import run_pipeline

    output = tmp_path / "results"
    run_pipeline(ROOT, cache_dir=CACHE_DIR, output_dir=output)
    written = sorted(path.name for path in output.iterdir())
    assert written == ["report.json"]
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert set(report["assays"]) == {str(aid) for aid in DECLARED_ASSAYS}


def test_the_download_does_not_refetch_a_valid_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second download must reuse the cache rather than read the container."""
    from aidd_commons.assay_endpoint_controls import data as data_module

    def forbid_network(url: str, start: int, end: int) -> bytes:
        raise AssertionError(f"a valid cache must not be downloaded again, but {url} was read")

    monkeypatch.setattr(data_module, "_fetch_range", forbid_network)
    paths = data_module.download_and_cache_assays(CACHE_DIR)
    assert len(paths) == 2 * len(DECLARED_ASSAYS)
