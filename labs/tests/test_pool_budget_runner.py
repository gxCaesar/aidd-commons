"""Run the real orchestration exclusively against authored, in-memory assays."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from aidd_commons import pool_budget_runner as runner
from aidd_commons.chembl_egfr.data import CachedDatasets
from aidd_commons.pool_budget_campaign import CampaignContractError

from .test_pool_budget_campaign import artificial_assay

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project(tmp_path):
    for relative in (
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
    assert runner.validate_real_protocol(project)["protocol_id"] == "chembl37-egfr-pool-budget-v1"
    with pytest.raises(CampaignContractError, match="confirmation"):
        runner.run_locked_campaign(project, confirmed=False)
    assert not (project / "labs/pool_budget/results").exists()


@pytest.mark.parametrize("mutation", ["alpha", "seeds", "capacity", "filter"])
def test_known_bad_protocol_is_rejected_before_cache(project, monkeypatch, mutation):
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    path = project / "labs/pool_budget/real-protocol.json"
    protocol = json.loads(path.read_text())
    if mutation == "alpha":
        protocol["prediction_contract"]["model"]["alpha"] = 10
    elif mutation == "seeds":
        protocol["acquisition_contract"]["policies"]["random"]["seeds"] = [0, 1]
    elif mutation == "capacity":
        protocol["partition_contract"]["real_target_capacities"]["pool"] = "0.60 * N"
    else:
        protocol["frozen_t05_reference"]["label_contract"]["filters"]["standard_units"] = "uM"
    path.write_text(json.dumps(protocol))
    with pytest.raises(CampaignContractError):
        runner.run_locked_campaign(project, confirmed=True)
    assert not (project / "labs/pool_budget/results").exists()


def test_paired_predictions_precede_any_scoring_and_rerun_is_refused(project, monkeypatch):
    datasets = CachedDatasets(
        {}, {}, artificial_assay(), artificial_assay("CHEMBL3705421", "EXTERNAL")
    )
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", lambda cache: datasets)
    monkeypatch.setattr(runner, "validate_frozen_scaffold_counts", lambda *args: None)
    events = []
    freeze, score = runner.freeze_predictions, runner.score_campaign

    def tracked_freeze(prepared):
        result = freeze(prepared)
        events.append("freeze")
        return result

    def tracked_score(prepared, frozen):
        assert events[:2] == ["freeze", "freeze"]
        events.append("score")
        return score(prepared, frozen)

    monkeypatch.setattr(runner, "freeze_predictions", tracked_freeze)
    monkeypatch.setattr(runner, "score_campaign", tracked_score)
    result = runner.run_locked_campaign(project, confirmed=True)
    assert events == ["freeze", "freeze", "score", "score"]
    assert set(result["assays"]) == {"CHEMBL5736995", "CHEMBL3705421"}
    output = project / "labs/pool_budget/results"
    details = json.loads((output / "locked-details.json").read_text())
    assert len(details["assays"]["CHEMBL5736995"]["parent_ids"]) == 60
    assert json.loads((output / "locked-metrics.json").read_text()) == result
    assert (output / "locked-evaluation.started.json").is_file()
    assert not (project / "site").exists()
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    with pytest.raises(CampaignContractError, match="already"):
        runner.run_locked_campaign(project, confirmed=True)


def test_failed_load_leaves_one_time_marker(project, monkeypatch):
    def failed_load(cache):
        raise ValueError("artificial ingestion failure")

    monkeypatch.setattr(runner, "load_cached_frozen_datasets", failed_load)
    with pytest.raises(ValueError, match="artificial ingestion failure"):
        runner.run_locked_campaign(project, confirmed=True)
    output = project / "labs/pool_budget/results"
    assert (output / "locked-evaluation.started.json").is_file()
    assert not (output / "locked-metrics.json").exists()
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    with pytest.raises(CampaignContractError, match="already"):
        runner.run_locked_campaign(project, confirmed=True)


def test_output_symlink_is_refused_before_cache(project, monkeypatch):
    monkeypatch.setattr(runner, "load_cached_frozen_datasets", forbid_cache)
    (project / "labs/pool_budget/results").symlink_to(project, target_is_directory=True)
    with pytest.raises(CampaignContractError, match="symlink"):
        runner.run_locked_campaign(project, confirmed=True)


@pytest.mark.parametrize(
    "arguments,expected,code",
    [
        (["validate-protocol"], '"assay_data": "not_read"', 0),
        (["evaluate-locked"], "confirmation is required", 1),
        (["evaluate-locked", "--output-dir", "elsewhere"], "unrecognized arguments", 2),
    ],
)
def test_cli_data_free_and_guarded_paths(project, arguments, expected, code):
    script = project / "labs/pool_budget/run_real_campaign.py"
    shutil.copyfile(ROOT / "labs/pool_budget/run_real_campaign.py", script)
    result = subprocess.run(
        [sys.executable, str(script), *arguments], capture_output=True, text=True, check=False
    )
    assert result.returncode == code, result.stderr
    assert expected in result.stdout + result.stderr
    if arguments == ["validate-protocol"]:
        assert json.loads(result.stdout)["campaign_execution"] == "not_requested"
    assert not (project / "labs/pool_budget/results").exists()
