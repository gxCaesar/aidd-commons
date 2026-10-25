from __future__ import annotations

import json
from collections.abc import Callable
from math import isfinite
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.freesolv.data import MoleculeRecord, ParseReport
from aidd_commons.freesolv.pipeline import (
    PretestValidationError,
    _deterministic_memberships,
    _validate_memberships_against_pretest,
    _validate_pretest_identity,
    evaluate_test,
    portable_evaluation_command,
    run_pretest,
)


def synthetic_records() -> tuple[MoleculeRecord, ...]:
    return tuple(
        MoleculeRecord(
            source_id=f"mobley_{index:03d}",
            input_smiles="C" * index,
            canonical_smiles="C" * index,
            target_kcal_mol=-float(index) / 10.0,
        )
        for index in range(1, 91)
    )


def synthetic_report() -> ParseReport:
    return ParseReport(
        total_lines=92,
        noncomment_lines=90,
        parsed_rows=90,
        continuation_lines=0,
    )


def mutate_protocol(payload: dict[str, Any]) -> None:
    payload["protocol"]["ridge_alpha"] = 0.5


def mutate_radius(payload: dict[str, Any]) -> None:
    payload["splits"]["random"]["validation"]["conformal_radii"]["morgan_ridge"] = float("nan")


def mutate_model_names(payload: dict[str, Any]) -> None:
    payload["splits"]["random"]["validation"]["point_metrics"].pop("morgan_ridge")


def planned_command() -> str:
    return (
        "env UV_CACHE_DIR=.cache/uv uv run python labs/freesolv/run_lab.py "
        "evaluate-test --data-path .cache/freesolv/freesolv-v0.52-database.txt "
        "--output-dir labs/freesolv/results"
    )


def test_pretest_writes_portable_frozen_artifacts(tmp_path: Path) -> None:
    command = planned_command()
    artifact = run_pretest(
        synthetic_records(),
        synthetic_report(),
        tmp_path,
        planned_evaluation_command=command,
    )

    assert artifact.primary_split == "scaffold"
    pretest_text = (tmp_path / "pretest.json").read_text()
    payload = json.loads(pretest_text)
    assert payload["pretest_passed"] is True
    assert payload["planned_test_evaluation_command"] == command
    assert "/Users/" not in pretest_text
    assert payload["dataset"]["tag"] == "v0.52"
    assert payload["parse_report"]["parsed_rows"] == 90
    assert set(payload["splits"]) == {"random", "scaffold"}
    assert (tmp_path / "splits" / "random.csv").exists()
    assert (tmp_path / "splits" / "scaffold.csv").exists()


def test_evaluate_test_refuses_to_start_without_a_pretest_artifact(
    tmp_path: Path,
) -> None:
    with pytest.raises(PretestValidationError, match="pretest artifact"):
        evaluate_test(synthetic_records(), synthetic_report(), tmp_path, command="test command")


def test_portable_evaluation_command_uses_only_repository_relative_arguments() -> None:
    repository_root = Path(__file__).parents[3]
    command = portable_evaluation_command(
        data_path=repository_root / ".cache" / "freesolv" / "freesolv-v0.52-database.txt",
        output_dir=repository_root / "labs" / "freesolv" / "results",
        repository_root=repository_root,
    )

    assert "/Users/" not in command
    assert "UV_CACHE_DIR=.cache/uv" in command
    assert "--data-path .cache/freesolv/freesolv-v0.52-database.txt" in command
    with pytest.raises(PretestValidationError, match="repository-relative"):
        portable_evaluation_command(
            data_path=Path("/private/tmp/freesolv/database.txt"),
            output_dir=repository_root / "labs" / "freesolv" / "results",
            repository_root=repository_root,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            mutate_protocol,
            "frozen protocol",
        ),
        (
            mutate_radius,
            "validation radii",
        ),
        (
            mutate_model_names,
            "model names",
        ),
    ],
)
def test_pretest_identity_rejects_protocol_radii_and_model_mutations_before_test(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    run_pretest(synthetic_records(), synthetic_report(), tmp_path)
    payload = json.loads((tmp_path / "pretest.json").read_text())
    mutation(payload)

    with pytest.raises(PretestValidationError, match=message):
        _validate_pretest_identity(payload, synthetic_report())


def test_pretest_membership_identity_rejects_saved_fit_trace_outside_train(tmp_path: Path) -> None:
    records = synthetic_records()
    run_pretest(records, synthetic_report(), tmp_path)
    payload = json.loads((tmp_path / "pretest.json").read_text())
    payload["splits"]["random"]["fit_trace"]["feature_fit_ids"].append("outside-train")

    with pytest.raises(PretestValidationError, match="fit trace"):
        _validate_memberships_against_pretest(
            records,
            _deterministic_memberships(records),
            payload,
        )


def test_synthetic_one_time_evaluation_writes_complete_portable_metrics(tmp_path: Path) -> None:
    records = synthetic_records()
    command = planned_command()
    run_pretest(
        records,
        synthetic_report(),
        tmp_path,
        planned_evaluation_command=command,
    )

    metrics_path = evaluate_test(records, synthetic_report(), tmp_path, command=command)
    metrics_text = metrics_path.read_text()
    metrics = json.loads(metrics_text)

    assert metrics["primary_split"] == "scaffold"
    assert metrics["test_evaluation_complete"] is True
    assert metrics["evaluation_command"] == command
    assert "/Users/" not in metrics_text
    for split_payload in metrics["splits"].values():
        test_payload = split_payload["test"]
        assert set(test_payload["point_metrics"]) == {
            "train_mean",
            "morgan_ridge",
            "morgan_random_forest",
        }
        assert set(test_payload["interval_metrics"]) == {
            "morgan_ridge",
            "morgan_random_forest",
        }
        for values in test_payload["point_metrics"].values():
            assert isfinite(values["mae"])
            assert isfinite(values["rmse"])
        for values in test_payload["interval_metrics"].values():
            assert 0.0 <= values["coverage"] <= 1.0
            assert isfinite(values["mean_width"])
            assert values["mean_width"] >= 0.0
            assert isfinite(values["radius"])
            assert values["radius"] >= 0.0

    with pytest.raises(PretestValidationError, match="already claimed or completed"):
        evaluate_test(records, synthetic_report(), tmp_path, command=command)
