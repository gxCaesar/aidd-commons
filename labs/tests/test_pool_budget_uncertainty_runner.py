"""Run the uncertainty orchestration exclusively against authored, in-memory assays."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from aidd_commons import pool_budget_uncertainty_runner as runner
from aidd_commons.chembl_egfr.data import CachedDatasets
from aidd_commons.pool_budget_uncertainty import UncertaintyContractError

from .test_pool_budget_campaign import artificial_assay

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project(tmp_path):
    for relative in (
        "labs/pool_budget/uncertainty-protocol.json",
        "labs/pool_budget/real-protocol.json",
        "labs/chembl_egfr/protocol.json",
        "pyproject.toml",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def forbid_cache(*args, **kwargs):
    raise AssertionError("real cache must not be read")


def test_data_free_validation_and_confirmation_guard(project, monkeypatch):
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    assert (
        runner.validate_uncertainty_protocol(project)["protocol_id"]
        == "chembl37-egfr-pool-budget-uncertainty-v1"
    )
    with pytest.raises(UncertaintyContractError, match="confirmation"):
        runner.run_locked_uncertainty_campaign(project, confirmed=False)
    assert not (project / "labs/pool_budget/uncertainty-results").exists()


@pytest.mark.parametrize("mutation", ["protocol_id", "frozen_reference", "output_dir", "policy"])
def test_known_bad_protocol_is_rejected_before_cache(project, monkeypatch, mutation):
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    path = project / "labs/pool_budget/uncertainty-protocol.json"
    protocol = json.loads(path.read_text())
    if mutation == "protocol_id":
        protocol["protocol_id"] = "something-else"
    elif mutation == "frozen_reference":
        protocol["frozen_reference"]["protocol_id"] = "wrong-reference"
    elif mutation == "output_dir":
        protocol["output_contract"]["directory"] = "labs/pool_budget/results/"
    else:
        protocol["new_policy"]["name"] = "different-policy"
    path.write_text(json.dumps(protocol))
    with pytest.raises(UncertaintyContractError):
        runner.run_locked_uncertainty_campaign(project, confirmed=True)
    assert not (project / "labs/pool_budget/uncertainty-results").exists()


def test_full_run_scores_both_assays_and_refuses_a_rerun(project, monkeypatch):
    datasets = CachedDatasets(
        {}, {}, artificial_assay(), artificial_assay("CHEMBL3705421", "EXTERNAL")
    )
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", lambda cache: datasets)
    monkeypatch.setattr(runner, "validate_frozen_scaffold_counts", lambda *args: None)

    result = runner.run_locked_uncertainty_campaign(project, confirmed=True)

    assert set(result["assays"]) == {"CHEMBL5736995", "CHEMBL3705421"}
    for assay in result["assays"].values():
        assert assay["policy"]["name"] == "ensemble-variance-uncertainty"
        assert len(assay["policy"]["recovery"]) == 5
        assert assay["policy"]["recovery"][0] == 0.0
    output = project / "labs/pool_budget/uncertainty-results"
    details = json.loads((output / "uncertainty-locked-details.json").read_text())
    assert len(details["assays"]["CHEMBL5736995"]["acquisition_order"]) == 8
    assert json.loads((output / "uncertainty-locked-metrics.json").read_text()) == result
    assert (output / "uncertainty-locked-evaluation.started.json").is_file()
    # Never touches, and in this isolated tmp_path project cannot possibly touch,
    # the completed campaign's own output directory.
    assert not (project / "labs/pool_budget/results").exists()

    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    with pytest.raises(UncertaintyContractError, match="already"):
        runner.run_locked_uncertainty_campaign(project, confirmed=True)


def test_failed_load_leaves_one_time_marker(project, monkeypatch):
    def failed_load(cache):
        raise ValueError("artificial ingestion failure")

    monkeypatch.setattr(runner, "load_cached_frozen_datasets", failed_load)
    with pytest.raises(ValueError, match="artificial ingestion failure"):
        runner.run_locked_uncertainty_campaign(project, confirmed=True)
    output = project / "labs/pool_budget/uncertainty-results"
    assert (output / "uncertainty-locked-evaluation.started.json").is_file()
    assert not (output / "uncertainty-locked-metrics.json").exists()
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    with pytest.raises(UncertaintyContractError, match="already"):
        runner.run_locked_uncertainty_campaign(project, confirmed=True)


def test_output_symlink_is_refused_before_cache(project, monkeypatch):
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    (project / "labs/pool_budget/uncertainty-results").symlink_to(project, target_is_directory=True)
    with pytest.raises(UncertaintyContractError, match="symlink"):
        runner.run_locked_uncertainty_campaign(project, confirmed=True)


@pytest.mark.parametrize(
    "arguments,expected,code",
    [
        (["validate-protocol"], '"assay_data": "not_read"', 0),
        (["evaluate-locked"], "confirmation is required", 1),
    ],
)
def test_cli_data_free_and_guarded_paths(project, arguments, expected, code):
    script = project / "labs/pool_budget/run_uncertainty_campaign.py"
    shutil.copyfile(ROOT / "labs/pool_budget/run_uncertainty_campaign.py", script)
    result = subprocess.run(
        [sys.executable, str(script), *arguments], capture_output=True, text=True, check=False
    )
    assert result.returncode == code, result.stderr
    assert expected in result.stdout + result.stderr
    if arguments == ["validate-protocol"]:
        assert json.loads(result.stdout)["campaign_execution"] == "not_requested"
    assert not (project / "labs/pool_budget/uncertainty-results").exists()
