"""Completed teaching summaries preserve negative results without private records."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.locked_result_summaries import (
    SummaryContractError,
    chembl_locked_summary,
    export_locked_summary,
    rmd17_locked_summary,
)

ROOT = Path(__file__).resolve().parents[2]
REVIEWED_ON = "2026-09-08"


def chembl_result():
    def scores(mae, rmse, rho, status="defined"):
        return {"mae": mae, "rmse": rmse, "spearman": rho, "spearman_status": status}

    return {
        "schema_version": "aidd-commons.chembl-egfr-locked-results.v1",
        "protocol_version": "chembl37-egfr-representation-v1",
        "locked_evaluation_complete": True,
        "selected_alphas": {"descriptor_ridge": 1000, "morgan_ridge": 1},
        "software": {
            "python": "3.11.15",
            "numpy": "2.4.6",
            "rdkit": "2025.09.6",
            "scikit_learn": "1.9.0",
        },
        "results": {
            name: {
                "count": count,
                "metrics": {
                    "train_mean": scores(1.0, 1.2, None, "undefined_constant_prediction"),
                    "descriptor_ridge": scores(0.8, 1.0, 0.2),
                    "morgan_ridge": scores(3.0, 3.2, -0.1),
                },
                "predictions": [{"parent_molecule_chembl_id": "PRIVATE_SENTINEL"}],
            }
            for name, count in (("primary_test", 132), ("assay_replication", 170))
        },
    }


def rmd17_result():
    return {
        "schema_version": "aidd-commons.rmd17-system-state-locked-metrics.v1",
        "protocol_id": "rmd17-system-state-v1",
        "selected_alpha": 100.0,
        "software": {"python": "3.11.15", "numpy": "2.4.6", "scikit_learn": "1.9.0"},
        "results": {
            "benzene": {
                "train_mean": {"mae": 2.0, "rmse": 2.5, "target_range": 10.0},
                "ridge": {"mae": 1.0, "rmse": 1.5, "target_range": 10.0},
            },
            "uracil": {
                "train_mean": {"mae": 4.0, "rmse": 4.5, "target_range": 20.0},
                "ridge": {"mae": 3.0, "rmse": 3.5, "target_range": 20.0},
            },
        },
    }


def rmd17_protocol():
    return json.loads((ROOT / "labs/rmd17_system_state/protocol.json").read_text())


def test_chembl_projection_retains_bad_morgan_scores_and_undefined_correlation():
    source = chembl_result()
    source["approval_receipt"] = "PRIVATE_SENTINEL"
    source["software"]["host"] = "PRIVATE_SENTINEL"
    source["results"]["primary_test"]["metrics"]["morgan_ridge"]["fit_rows"] = "PRIVATE_SENTINEL"
    summary = chembl_locked_summary(source, reviewed_on=REVIEWED_ON)
    assert summary["results"]["assay_replication"]["metrics"]["morgan_ridge"] == {
        "mae": 3.0,
        "rmse": 3.2,
        "spearman": -0.1,
        "spearman_status": "defined",
    }
    assert summary["results"]["primary_test"]["metrics"]["train_mean"]["spearman"] is None
    assert summary["status"] == "completed"
    assert summary["reviewed_on"] == REVIEWED_ON
    assert "PRIVATE_SENTINEL" not in json.dumps(summary)
    source["results"]["assay_replication"]["metrics"]["morgan_ridge"]["mae"] = 0.01
    assert summary["results"]["assay_replication"]["metrics"]["morgan_ridge"]["mae"] == 3.0


@pytest.mark.parametrize(
    "mutation",
    ["incomplete", "missing_model", "missing_assay", "count", "alpha", "nan", "rho", "null_status"],
)
def test_chembl_projection_rejects_incomplete_or_invalid_aggregates(mutation):
    source = chembl_result()
    primary = source["results"]["primary_test"]
    if mutation == "incomplete":
        source["locked_evaluation_complete"] = False
    elif mutation == "missing_model":
        del primary["metrics"]["morgan_ridge"]
    elif mutation == "missing_assay":
        del source["results"]["assay_replication"]
    elif mutation == "count":
        primary["count"] = 131
    elif mutation == "alpha":
        source["selected_alphas"]["morgan_ridge"] = 10
    elif mutation == "nan":
        primary["metrics"]["morgan_ridge"]["mae"] = float("nan")
    elif mutation == "rho":
        primary["metrics"]["morgan_ridge"]["spearman"] = 1.1
    else:
        primary["metrics"]["train_mean"]["spearman_status"] = "defined"
    with pytest.raises(SummaryContractError):
        chembl_locked_summary(source, reviewed_on=REVIEWED_ON)


def test_rmd17_projection_aggregates_two_systems_not_frames_and_strips_private_fields():
    source = rmd17_result()
    source["membership"] = "PRIVATE_SENTINEL"
    source["software"]["host"] = "PRIVATE_SENTINEL"
    source["results"]["benzene"]["ridge"]["predictions"] = "PRIVATE_SENTINEL"
    summary = rmd17_locked_summary(source, rmd17_protocol(), reviewed_on=REVIEWED_ON)
    assert summary["system_count"] == 2
    assert summary["partitions_per_system"] == {"train": 600, "validation": 200, "evaluation": 200}
    assert summary["aggregates"] == {
        "train_mean": {"median_mae": 3.0, "mae_range": 2.0},
        "ridge": {"median_mae": 2.0, "mae_range": 2.0},
    }
    assert summary["results"]["benzene"]["ridge"] == {"mae": 1.0, "rmse": 1.5, "target_range": 10.0}
    assert "PRIVATE_SENTINEL" not in json.dumps(summary)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_system",
        "extra_system",
        "alpha",
        "negative",
        "rmse",
        "range",
        "split",
        "system_role",
    ],
)
def test_rmd17_projection_rejects_invalid_results_or_wrong_protocol(mutation):
    source = rmd17_result()
    protocol = rmd17_protocol()
    if mutation == "missing_system":
        del source["results"]["uracil"]
    elif mutation == "extra_system":
        source["results"]["ethanol"] = source["results"]["benzene"]
    elif mutation == "alpha":
        source["selected_alpha"] = 1
    elif mutation == "negative":
        source["results"]["benzene"]["ridge"]["mae"] = -1
    elif mutation == "rmse":
        source["results"]["benzene"]["ridge"]["rmse"] = 0
    elif mutation == "range":
        source["results"]["benzene"]["ridge"]["target_range"] = 11
    elif mutation == "split":
        protocol["sampling"]["partitions"]["evaluation"] = 201
    else:
        protocol["systems"][2]["role"] = "development"
    with pytest.raises(SummaryContractError):
        rmd17_locked_summary(source, protocol, reviewed_on=REVIEWED_ON)


@pytest.mark.parametrize("kind", ["chembl", "rmd17"])
def test_export_is_idempotent_and_refuses_to_overwrite_a_different_summary(tmp_path, kind):
    (tmp_path / "results").mkdir()
    source = tmp_path / "results/locked-metrics.json"
    source.write_text(json.dumps(chembl_result() if kind == "chembl" else rmd17_result()))
    if kind == "rmd17":
        (tmp_path / "protocol.json").write_text(json.dumps(rmd17_protocol()))
    original = source.read_text()
    target = export_locked_summary(tmp_path, kind=kind, reviewed_on=REVIEWED_ON)
    assert target.name == "locked-summary.json"
    summary = json.loads(target.read_text())
    if kind == "chembl":
        assert summary["results"]["assay_replication"]["count"] == 170
    else:
        assert summary["system_count"] == 2
    assert export_locked_summary(tmp_path, kind=kind, reviewed_on=REVIEWED_ON) == target
    assert source.read_text() == original
    target.write_text("{}")
    with pytest.raises(SummaryContractError, match="differs"):
        export_locked_summary(tmp_path, kind=kind, reviewed_on=REVIEWED_ON)
    assert target.read_text() == "{}"


@pytest.mark.parametrize("location", ["source", "target"])
def test_export_rejects_symlinks(tmp_path, location):
    (tmp_path / "results").mkdir()
    source = tmp_path / "results/locked-metrics.json"
    if location == "source":
        original = tmp_path / "original.json"
        original.write_text(json.dumps(chembl_result()))
        source.symlink_to(original)
    else:
        source.write_text(json.dumps(chembl_result()))
        (tmp_path / "locked-summary.json").symlink_to(tmp_path / "elsewhere.json")
    with pytest.raises(SummaryContractError, match="symlink"):
        export_locked_summary(tmp_path, kind="chembl", reviewed_on=REVIEWED_ON)


@pytest.mark.parametrize("lab,kind", [("chembl_egfr", "chembl"), ("rmd17_system_state", "rmd17")])
def test_delivered_summary_preserves_all_saved_metrics_when_local_results_exist(lab, kind):
    directory = ROOT / "labs" / lab
    source = directory / "results/locked-metrics.json"
    if not source.exists():
        pytest.skip("local execution artifacts are not distributed")
    raw = json.loads(source.read_text())
    delivered = json.loads((directory / "locked-summary.json").read_text())
    expected = (
        chembl_locked_summary(copy.deepcopy(raw), reviewed_on=REVIEWED_ON)
        if kind == "chembl"
        else rmd17_locked_summary(copy.deepcopy(raw), rmd17_protocol(), reviewed_on=REVIEWED_ON)
    )
    assert delivered == expected
    bad = copy.deepcopy(raw)
    if kind == "chembl":
        bad["results"]["primary_test"]["metrics"]["morgan_ridge"]["mae"] = float("nan")
        with pytest.raises(SummaryContractError):
            chembl_locked_summary(bad, reviewed_on=REVIEWED_ON)
    else:
        bad["results"]["benzene"]["ridge"]["rmse"] = 0
        with pytest.raises(SummaryContractError):
            rmd17_locked_summary(bad, rmd17_protocol(), reviewed_on=REVIEWED_ON)
