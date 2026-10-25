from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.chembl_egfr.data import AssayDataset, normalise_activity_rows
from aidd_commons.chembl_egfr.pipeline import (
    LockedEvaluationError,
    evaluate_locked,
    portable_locked_evaluation_command,
    run_pretest,
)

PRIMARY_SMILES = (
    "c1ccccc1",
    "C1CCCCC1",
    "c1ccncc1",
    "c1ccoc1",
    "c1ccsc1",
    "C1CCCC1",
    "C1CCC1",
    "C1CC1",
    "c1ncncc1",
    "O1CCOCC1",
    "N1CCNCC1",
    "c1ccc2ccccc2c1",
)
EXTERNAL_SMILES = ("c1ccc2ncccc2c1", "c1ccc2[nH]ccc2c1", "C1CCOC1")


def dataset(assay_id: str, smiles_values: tuple[str, ...], offset: int = 0) -> AssayDataset:
    rows: list[dict[str, object]] = []
    for index, smiles in enumerate(smiles_values, start=1):
        pchembl = 6.0 + 0.1 * index
        rows.append(
            {
                "activity_id": offset + index,
                "assay_chembl_id": assay_id,
                "canonical_smiles": smiles,
                "data_validity_comment": None,
                "molecule_chembl_id": f"CHEMBL_PIPELINE_{offset + index}",
                "parent_molecule_chembl_id": f"CHEMBL_PIPELINE_{offset + index}",
                "pchembl_value": f"{pchembl:.2f}",
                "potential_duplicate": 0,
                "standard_flag": 1,
                "standard_relation": "=",
                "standard_type": "IC50",
                "standard_units": "nM",
                "standard_value": f"{10 ** (9.0 - pchembl):.8f}",
            }
        )
    return normalise_activity_rows(rows, assay_id)


def planned_command(repository_root: Path) -> str:
    return portable_locked_evaluation_command(
        cache_dir=repository_root / ".cache" / "chembl_egfr",
        repository_root=repository_root,
    )


def test_pretest_contains_development_evidence_but_no_locked_metrics(tmp_path: Path) -> None:
    repository_root = Path(__file__).parents[3]
    output_dir = tmp_path / "results"
    command = planned_command(repository_root)
    artifact = run_pretest(
        dataset("CHEMBL5736995", PRIMARY_SMILES),
        dataset("CHEMBL3705421", EXTERNAL_SMILES, offset=100),
        output_dir,
        planned_evaluation_command=command,
    )

    payload = json.loads(artifact.pretest_path.read_text(encoding="utf-8"))
    text = artifact.pretest_path.read_text(encoding="utf-8")

    assert payload["pretest_passed"] is True
    assert payload["locked_evaluations"] == {"primary": "not_run", "replication": "not_run"}
    assert payload["planned_locked_evaluation_command"] == command
    assert set(payload["development"]["validation"]["metrics"]) == {
        "descriptor_ridge",
        "morgan_ridge",
        "train_mean",
    }
    assert "primary_test_metrics" not in text
    assert "replication_metrics" not in text
    assert "locked_predictions" not in text
    assert not (output_dir / "locked-evaluation.started.json").exists()
    assert not (output_dir / "locked-metrics.json").exists()


def test_locked_evaluation_requires_confirmation_and_is_atomic_and_one_time(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    primary = dataset("CHEMBL5736995", PRIMARY_SMILES)
    external = dataset("CHEMBL3705421", EXTERNAL_SMILES, offset=100)
    output_dir = repository_root / "labs" / "chembl_egfr" / "results"
    command = planned_command(repository_root)
    run_pretest(primary, external, output_dir, planned_evaluation_command=command)

    with pytest.raises(LockedEvaluationError, match="explicit confirmation"):
        evaluate_locked(
            primary,
            external,
            output_dir,
            command=command,
            confirmed=False,
            repository_root=repository_root,
        )

    metrics_path = evaluate_locked(
        primary,
        external,
        output_dir,
        command=command,
        confirmed=True,
        repository_root=repository_root,
    )
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    assert metrics["locked_evaluation_complete"] is True
    assert set(metrics["results"]) == {"primary_test", "assay_replication"}
    assert set(metrics["results"]["primary_test"]["metrics"]) == {
        "descriptor_ridge",
        "morgan_ridge",
        "train_mean",
    }
    assert set(metrics["results"]["assay_replication"]["metrics"]) == {
        "descriptor_ridge",
        "morgan_ridge",
        "train_mean",
    }
    assert (output_dir / "locked-evaluation.started.json").exists()

    with pytest.raises(LockedEvaluationError, match="already claimed or completed"):
        evaluate_locked(
            primary,
            external,
            output_dir,
            command=command,
            confirmed=True,
            repository_root=repository_root,
        )


def test_locked_reconstruction_runs_once_and_preserves_original_evidence(tmp_path, monkeypatch):
    from aidd_commons.chembl_egfr import pipeline

    primary = dataset("CHEMBL5736995", PRIMARY_SMILES)
    external = dataset("CHEMBL3705421", EXTERNAL_SMILES, offset=100)
    output_dir = tmp_path / "labs" / "chembl_egfr" / "results"
    command = planned_command(tmp_path)
    artifact = run_pretest(primary, external, output_dir, planned_evaluation_command=command)
    original = artifact.pretest_path.read_text()
    original_payload = json.loads(original)
    original_tune = pipeline.tune_baselines
    reconstructions = []

    def counted_tune(train, validation):
        reconstructions.append(tuple(row.parent_molecule_chembl_id for row in train))
        return original_tune(train, validation)

    monkeypatch.setattr(pipeline, "tune_baselines", counted_tune)
    result_path = evaluate_locked(
        primary, external, output_dir, command=command, confirmed=True, repository_root=tmp_path
    )
    assert len(reconstructions) == 1
    assert artifact.pretest_path.read_text() == original
    result = json.loads(result_path.read_text())
    assert (
        result["selected_alphas"]
        == original_payload["development"]["validation"]["selected_alphas"]
    )
    assert result["execution_amendment"]["id"] == "chembl37-egfr-execution-v1.1"


def test_locked_evaluation_rejects_an_alternate_repository_output(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    primary = dataset("CHEMBL5736995", PRIMARY_SMILES)
    external = dataset("CHEMBL3705421", EXTERNAL_SMILES, offset=100)
    alternate_output = repository_root / "labs" / "chembl_egfr" / "alternate-results"
    command = planned_command(repository_root)
    run_pretest(
        primary,
        external,
        alternate_output,
        planned_evaluation_command=command,
    )

    with pytest.raises(LockedEvaluationError, match="canonical output directory"):
        evaluate_locked(
            primary,
            external,
            alternate_output,
            command=command,
            confirmed=True,
            repository_root=repository_root,
        )


def test_portable_command_rejects_paths_outside_the_repository(tmp_path: Path) -> None:
    repository_root = Path(__file__).parents[3]
    command = planned_command(repository_root)

    assert "/Users/" not in command
    assert "evaluate-locked" in command
    assert "--confirm-locked-evaluation" in command
    assert "--output-dir" not in command
    with pytest.raises(LockedEvaluationError, match="repository-relative"):
        portable_locked_evaluation_command(
            cache_dir=tmp_path / "cache",
            repository_root=repository_root,
        )


@pytest.mark.parametrize("changed_field", ["selected_alpha", "prediction", "membership"])
def test_changed_pretest_cannot_reach_locked_scoring(tmp_path, changed_field):
    primary = dataset("CHEMBL5736995", PRIMARY_SMILES)
    external = dataset("CHEMBL3705421", EXTERNAL_SMILES, offset=100)
    output_dir = tmp_path / "labs" / "chembl_egfr" / "results"
    command = planned_command(tmp_path)
    artifact = run_pretest(primary, external, output_dir, planned_evaluation_command=command)
    stored = json.loads(artifact.pretest_path.read_text())
    development = stored["development"]
    if changed_field == "selected_alpha":
        development["validation"]["selected_alphas"]["morgan_ridge"] = 123.0
    elif changed_field == "prediction":
        development["validation"]["records"][0]["predictions"]["morgan_ridge"] += 1.0
    else:
        development["membership"]["unexpected_partition"] = ["invented-parent"]
    artifact.pretest_path.write_text(json.dumps(stored))
    with pytest.raises(LockedEvaluationError, match="pretest identity differs"):
        evaluate_locked(
            primary, external, output_dir, command=command, confirmed=True, repository_root=tmp_path
        )
    assert not (output_dir / "locked-evaluation.started.json").exists()
    assert not (output_dir / "locked-metrics.json").exists()
