from __future__ import annotations

import csv
import json
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np

from aidd_commons.freesolv.data import (
    MoleculeRecord,
    ParseReport,
    parse_freesolv_v052,
)
from aidd_commons.freesolv.evaluation import (
    EvaluationContractError,
    assert_finite_predictions,
    conformal_radius,
    interval_metrics,
    point_metrics,
)
from aidd_commons.freesolv.models import (
    FitTrace,
    ModelContractError,
    assert_training_only_fit,
    fit_frozen_models,
    predict_models,
)
from aidd_commons.freesolv.splits import (
    SplitContractError,
    SplitMembership,
    assert_no_canonical_overlap,
    assert_scaffold_isolation,
    random_split,
    scaffold_split,
)

DATASET_TAG = "v0.52"
DATASET_URL = "https://raw.githubusercontent.com/MobleyLab/FreeSolv/v0.52/database.txt"
RELEASE_DOI = "10.5281/zenodo.1161245"
PRIMARY_SPLIT = "scaffold"
MODEL_NAMES = ("train_mean", "morgan_ridge", "morgan_random_forest")
CONFORMAL_MODEL_NAMES = ("morgan_ridge", "morgan_random_forest")
DATA_FILE_NAME = "freesolv-v0.52-database.txt"
PRETEST_FILE_NAME = "pretest.json"
METRICS_FILE_NAME = "metrics.json"
TEST_EVALUATION_MARKER_NAME = "test-evaluation.started.json"
EVALUATION_COMMAND_PREFIX = (
    "env",
    "UV_CACHE_DIR=.cache/uv",
    "uv",
    "run",
    "python",
    "labs/freesolv/run_lab.py",
    "evaluate-test",
)
DEFAULT_PLANNED_EVALUATION_COMMAND = " ".join(EVALUATION_COMMAND_PREFIX)


class PretestValidationError(ValueError):
    """Raised when a required pre-test protocol assertion fails."""


class DataDownloadError(RuntimeError):
    """Raised when the pinned FreeSolv file cannot be obtained."""


@dataclass(frozen=True)
class PretestArtifact:
    output_dir: Path
    primary_split: str


def validate_split_pretest(records: Sequence[MoleculeRecord], membership: SplitMembership) -> None:
    """Verify membership coverage and isolation before any test predictions exist."""
    try:
        assert_no_canonical_overlap(membership)
        expected_ids = {record.canonical_smiles for record in records}
        observed_ids = set(membership.train_ids + membership.validation_ids + membership.test_ids)
        if observed_ids != expected_ids:
            raise SplitContractError("split membership does not cover the canonical molecule set")
        if membership.split_kind == "scaffold":
            assert_scaffold_isolation(membership)
    except SplitContractError as error:
        raise PretestValidationError(str(error)) from error


def validate_model_pretest(
    train_ids: tuple[str, ...],
    fit_trace: FitTrace,
    validation_predictions: Mapping[str, np.ndarray],
    conformal_radii: Mapping[str, float],
) -> None:
    """Verify train-only fitting and finite validation-only uncertainty artifacts."""
    try:
        assert_training_only_fit(fit_trace, train_ids)
        if set(fit_trace.model_fit_ids) != set(MODEL_NAMES):
            raise ModelContractError("fit trace does not cover every frozen model")
        for model_name in MODEL_NAMES:
            try:
                predictions = validation_predictions[model_name]
            except KeyError as error:
                raise EvaluationContractError(
                    f"missing validation predictions for {model_name}"
                ) from error
            assert_finite_predictions(predictions)
        for model_name in CONFORMAL_MODEL_NAMES:
            try:
                radius = conformal_radii[model_name]
            except KeyError as error:
                raise EvaluationContractError(
                    f"missing conformal radius for {model_name}"
                ) from error
            if not np.isfinite(radius) or radius < 0.0:
                raise EvaluationContractError("non-finite conformal radius")
    except (EvaluationContractError, ModelContractError) as error:
        raise PretestValidationError(str(error)) from error


def download_freesolv_v052(cache_dir: Path) -> Path:
    """Download the pinned data file into a caller-selected, non-repository cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    data_path = cache_dir / DATA_FILE_NAME
    if data_path.exists():
        return data_path
    try:
        with urlopen(DATASET_URL, timeout=30) as response:
            contents = response.read()
    except URLError as error:
        raise DataDownloadError(
            f"could not download pinned FreeSolv v0.52 data: {error}"
        ) from error
    data_path.write_bytes(contents)
    return data_path


def load_freesolv_v052(data_path: Path) -> tuple[tuple[MoleculeRecord, ...], ParseReport]:
    """Parse a pinned v0.52 file, including its exact header contract."""
    return parse_freesolv_v052(data_path.read_text(encoding="utf-8"))


def portable_evaluation_command(data_path: Path, output_dir: Path, repository_root: Path) -> str:
    """Build a reproducible command without embedding a machine-local absolute path."""
    data_argument = _repository_relative_path(data_path, repository_root)
    output_argument = _repository_relative_path(output_dir, repository_root)
    return shlex.join(
        (
            *EVALUATION_COMMAND_PREFIX,
            "--data-path",
            data_argument,
            "--output-dir",
            output_argument,
        )
    )


def run_pretest(
    records: Sequence[MoleculeRecord],
    parse_report: ParseReport,
    output_dir: Path,
    *,
    planned_evaluation_command: str = DEFAULT_PLANNED_EVALUATION_COMMAND,
) -> PretestArtifact:
    """Run and persist every protocol gate that precedes test-set prediction."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _refuse_after_test_evaluation(output_dir)
    _validate_portable_evaluation_command(planned_evaluation_command)

    memberships = _deterministic_memberships(records)
    record_by_id = {record.canonical_smiles: record for record in records}
    split_payloads: dict[str, dict[str, object]] = {}
    for split_kind, membership in memberships.items():
        validate_split_pretest(records, membership)
        train_records = _records_for_ids(record_by_id, membership.train_ids)
        validation_records = _records_for_ids(record_by_id, membership.validation_ids)
        models = fit_frozen_models(train_records)
        validation_predictions = predict_models(models, validation_records)
        validation_targets = _targets(validation_records)
        conformal_radii = {
            model_name: conformal_radius(validation_targets, validation_predictions[model_name])
            for model_name in CONFORMAL_MODEL_NAMES
        }
        validate_model_pretest(
            train_ids=membership.train_ids,
            fit_trace=models.fit_trace,
            validation_predictions=validation_predictions,
            conformal_radii=conformal_radii,
        )
        _write_membership_csv(output_dir / "splits" / f"{split_kind}.csv", record_by_id, membership)
        split_payloads[split_kind] = _pretest_split_payload(
            membership,
            validation_targets,
            validation_predictions,
            conformal_radii,
            models.fit_trace,
        )

    payload = {
        "dataset": {
            "tag": DATASET_TAG,
            "raw_url": DATASET_URL,
            "release_doi": RELEASE_DOI,
        },
        "parse_report": asdict(parse_report),
        "planned_test_evaluation_command": planned_evaluation_command,
        "primary_split": PRIMARY_SPLIT,
        "pretest_passed": True,
        "protocol": _protocol_payload(),
        "splits": split_payloads,
    }
    _write_json(output_dir / PRETEST_FILE_NAME, payload)
    return PretestArtifact(output_dir=output_dir, primary_split=PRIMARY_SPLIT)


def evaluate_test(
    records: Sequence[MoleculeRecord],
    parse_report: ParseReport,
    output_dir: Path,
    *,
    command: str,
) -> Path:
    """Run the frozen final evaluation once, after a successful persisted pre-test gate."""
    pretest_payload = _load_pretest_payload(output_dir)
    if pretest_payload.get("pretest_passed") is not True:
        raise PretestValidationError("pretest artifact does not record a passed pre-test gate")
    _validate_pretest_identity(pretest_payload, parse_report)
    if pretest_payload["planned_test_evaluation_command"] != command:
        raise PretestValidationError("final command differs from the audited pretest command")
    _validate_portable_evaluation_command(command)
    _refuse_after_test_evaluation(output_dir)

    memberships = _deterministic_memberships(records)
    _validate_memberships_against_pretest(records, memberships, pretest_payload)
    record_by_id = {record.canonical_smiles: record for record in records}
    _claim_test_evaluation(output_dir, command)

    split_payloads: dict[str, dict[str, object]] = {}
    for split_kind, membership in memberships.items():
        train_records = _records_for_ids(record_by_id, membership.train_ids)
        test_records = _records_for_ids(record_by_id, membership.test_ids)
        models = fit_frozen_models(train_records)
        test_predictions = predict_models(models, test_records)
        test_targets = _targets(test_records)
        validation_radii = _read_validation_radii(pretest_payload, split_kind)
        for predictions in test_predictions.values():
            assert_finite_predictions(predictions)
        split_payloads[split_kind] = _test_split_payload(
            membership,
            test_targets,
            test_predictions,
            validation_radii,
            models.fit_trace,
        )

    payload = {
        "dataset": {
            "tag": DATASET_TAG,
            "raw_url": DATASET_URL,
            "release_doi": RELEASE_DOI,
        },
        "evaluation_command": command,
        "parse_report": asdict(parse_report),
        "primary_split": PRIMARY_SPLIT,
        "protocol": _protocol_payload(),
        "splits": split_payloads,
        "test_evaluation_complete": True,
    }
    metrics_path = output_dir / METRICS_FILE_NAME
    _write_json(metrics_path, payload)
    return metrics_path


def _deterministic_memberships(
    records: Sequence[MoleculeRecord],
) -> dict[str, SplitMembership]:
    memberships: dict[str, SplitMembership] = {}
    for split_kind, splitter in (("random", random_split), ("scaffold", scaffold_split)):
        first = splitter(records)
        second = splitter(records)
        if first != second:
            raise PretestValidationError(
                f"{split_kind} split is not deterministic for the frozen seed"
            )
        validate_split_pretest(records, first)
        memberships[split_kind] = first
    return memberships


def _records_for_ids(
    record_by_id: Mapping[str, MoleculeRecord], ids: Sequence[str]
) -> tuple[MoleculeRecord, ...]:
    try:
        return tuple(record_by_id[canonical_smiles] for canonical_smiles in ids)
    except KeyError as error:
        raise PretestValidationError(
            f"split membership references an unknown canonical molecule: {error.args[0]}"
        ) from error


def _targets(records: Sequence[MoleculeRecord]) -> np.ndarray:
    return np.asarray([record.target_kcal_mol for record in records], dtype=float)


def _pretest_split_payload(
    membership: SplitMembership,
    validation_targets: np.ndarray,
    validation_predictions: Mapping[str, np.ndarray],
    conformal_radii: Mapping[str, float],
    fit_trace: FitTrace,
) -> dict[str, object]:
    return {
        "fit_trace": _fit_trace_payload(fit_trace),
        "grouping_keys": dict(sorted(membership.grouping_keys.items())),
        "membership": _membership_payload(membership),
        "validation": {
            "conformal_radii": dict(sorted(conformal_radii.items())),
            "point_metrics": {
                model_name: asdict(point_metrics(validation_targets, predictions))
                for model_name, predictions in validation_predictions.items()
            },
        },
    }


def _test_split_payload(
    membership: SplitMembership,
    test_targets: np.ndarray,
    test_predictions: Mapping[str, np.ndarray],
    validation_radii: Mapping[str, float],
    fit_trace: FitTrace,
) -> dict[str, object]:
    point_metrics_payload = {
        model_name: asdict(point_metrics(test_targets, predictions))
        for model_name, predictions in test_predictions.items()
    }
    interval_metrics_payload = {
        model_name: {
            **asdict(interval_metrics(test_targets, test_predictions[model_name], radius)),
            "radius": radius,
        }
        for model_name, radius in validation_radii.items()
    }
    return {
        "fit_trace": _fit_trace_payload(fit_trace),
        "membership": _membership_payload(membership),
        "test": {
            "interval_metrics": interval_metrics_payload,
            "point_metrics": point_metrics_payload,
        },
    }


def _membership_payload(membership: SplitMembership) -> dict[str, object]:
    return {
        "actual_counts": {
            "test": len(membership.test_ids),
            "train": len(membership.train_ids),
            "validation": len(membership.validation_ids),
        },
        "ids": {
            "test": list(membership.test_ids),
            "train": list(membership.train_ids),
            "validation": list(membership.validation_ids),
        },
        "target_counts": asdict(membership.targets),
    }


def _fit_trace_payload(fit_trace: FitTrace) -> dict[str, object]:
    return {
        "feature_fit_ids": list(fit_trace.feature_fit_ids),
        "model_fit_ids": {
            model_name: list(ids) for model_name, ids in sorted(fit_trace.model_fit_ids.items())
        },
    }


def _write_membership_csv(
    path: Path,
    record_by_id: Mapping[str, MoleculeRecord],
    membership: SplitMembership,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("source_id", "canonical_smiles", "grouping_key", "split"))
        for split_name in ("train", "validation", "test"):
            for canonical_smiles in membership.ids(split_name):
                writer.writerow(
                    (
                        record_by_id[canonical_smiles].source_id,
                        canonical_smiles,
                        membership.grouping_keys[canonical_smiles],
                        split_name,
                    )
                )


def _protocol_payload() -> dict[str, object]:
    return {
        "conformal_coverage": 0.9,
        "global_seed": 20_260_904,
        "morgan_bits": 2048,
        "morgan_chirality": True,
        "morgan_radius": 2,
        "random_forest": {
            "max_features": "sqrt",
            "min_samples_leaf": 1,
            "n_estimators": 500,
            "n_jobs": 1,
            "random_state": 20_260_904,
        },
        "ridge_alpha": 1.0,
        "target_field": "fourth semicolon-delimited field, experimental kcal/mol",
    }


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_pretest_payload(output_dir: Path) -> Mapping[str, object]:
    pretest_path = output_dir / PRETEST_FILE_NAME
    if not pretest_path.exists():
        raise PretestValidationError("pretest artifact is required before final test evaluation")
    try:
        payload = json.loads(pretest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PretestValidationError("pretest artifact is not valid JSON") from error
    if not isinstance(payload, dict):
        raise PretestValidationError("pretest artifact is not a JSON object")
    return payload


def _validate_pretest_identity(
    pretest_payload: Mapping[str, object], parse_report: ParseReport
) -> None:
    dataset = pretest_payload.get("dataset")
    if not isinstance(dataset, Mapping) or dataset.get("tag") != DATASET_TAG:
        raise PretestValidationError("pretest artifact does not match the frozen dataset tag")
    if dataset.get("raw_url") != DATASET_URL or dataset.get("release_doi") != RELEASE_DOI:
        raise PretestValidationError("pretest artifact does not match the frozen dataset source")
    if pretest_payload.get("parse_report") != asdict(parse_report):
        raise PretestValidationError("pretest artifact does not match the parsed data report")
    if pretest_payload.get("primary_split") != PRIMARY_SPLIT:
        raise PretestValidationError("pretest artifact does not match the frozen primary split")
    if pretest_payload.get("protocol") != _protocol_payload():
        raise PretestValidationError("pretest artifact does not match the frozen protocol")
    planned_command = pretest_payload.get("planned_test_evaluation_command")
    if not isinstance(planned_command, str):
        raise PretestValidationError("pretest artifact does not record a portable test command")
    _validate_portable_evaluation_command(planned_command)
    _validate_stored_validation_artifacts(pretest_payload)


def _validate_memberships_against_pretest(
    records: Sequence[MoleculeRecord],
    memberships: Mapping[str, SplitMembership],
    pretest_payload: Mapping[str, object],
) -> None:
    stored_splits = pretest_payload.get("splits")
    if not isinstance(stored_splits, Mapping):
        raise PretestValidationError("pretest artifact does not contain split memberships")
    for split_kind, membership in memberships.items():
        validate_split_pretest(records, membership)
        stored_split = stored_splits.get(split_kind)
        if not isinstance(stored_split, Mapping):
            raise PretestValidationError(f"pretest artifact is missing the {split_kind} split")
        stored_membership = stored_split.get("membership")
        if stored_membership != _membership_payload(membership):
            raise PretestValidationError(
                f"pretest artifact membership differs from deterministic {split_kind} split"
            )
        _validate_stored_fit_trace_membership(stored_split, membership, split_kind)


def _read_validation_radii(
    pretest_payload: Mapping[str, object], split_kind: str
) -> dict[str, float]:
    stored_splits = _as_mapping(
        pretest_payload.get("splits"), "pretest artifact does not contain split artifacts"
    )
    split_payload = _as_mapping(
        stored_splits.get(split_kind),
        f"pretest artifact is missing validation radii for the {split_kind} split",
    )
    validation = _as_mapping(
        split_payload.get("validation"),
        f"pretest artifact is missing validation radii for the {split_kind} split",
    )
    raw_radii = _as_mapping(
        validation.get("conformal_radii"),
        f"pretest artifact has invalid validation radii for the {split_kind} split",
    )
    radii: dict[str, float] = {}
    for model_name in CONFORMAL_MODEL_NAMES:
        value = raw_radii.get(model_name)
        if not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0.0:
            raise PretestValidationError(
                f"pretest artifact has a non-finite validation radius for {model_name}"
            )
        radii[model_name] = float(value)
    return radii


def _refuse_after_test_evaluation(output_dir: Path) -> None:
    marker_path = output_dir / TEST_EVALUATION_MARKER_NAME
    metrics_path = output_dir / METRICS_FILE_NAME
    if marker_path.exists() or metrics_path.exists():
        raise PretestValidationError("final test evaluation was already claimed or completed")


def _claim_test_evaluation(output_dir: Path, command: str) -> None:
    marker_path = output_dir / TEST_EVALUATION_MARKER_NAME
    try:
        with marker_path.open("x", encoding="utf-8") as handle:
            json.dump({"command": command, "status": "started"}, handle, sort_keys=True)
            handle.write("\n")
    except FileExistsError as error:
        raise PretestValidationError(
            "final test evaluation was already claimed or completed"
        ) from error


def _repository_relative_path(path: Path, repository_root: Path) -> str:
    root = repository_root.resolve()
    candidate = path if path.is_absolute() else root / path
    try:
        return candidate.resolve().relative_to(root).as_posix()
    except ValueError as error:
        raise PretestValidationError(
            "evaluation data and output paths must be repository-relative"
        ) from error


def _validate_portable_evaluation_command(command: str) -> None:
    tokens = shlex.split(command)
    if tuple(tokens[: len(EVALUATION_COMMAND_PREFIX)]) != EVALUATION_COMMAND_PREFIX:
        raise PretestValidationError("test command does not use the frozen portable invocation")
    if any(token.startswith("/") for token in tokens):
        raise PretestValidationError("test command must not record an absolute local path")


def _validate_stored_validation_artifacts(pretest_payload: Mapping[str, object]) -> None:
    stored_splits = _as_mapping(
        pretest_payload.get("splits"), "pretest artifact does not contain split artifacts"
    )
    if set(stored_splits) != {"random", "scaffold"}:
        raise PretestValidationError("pretest artifact has invalid split names")
    for split_kind in ("random", "scaffold"):
        split_payload = _as_mapping(
            stored_splits.get(split_kind), f"pretest artifact is missing the {split_kind} split"
        )
        validation = _as_mapping(
            split_payload.get("validation"),
            f"pretest artifact is missing validation artifacts for the {split_kind} split",
        )
        _validate_stored_radii(validation, split_kind)
        _validate_stored_point_metrics(validation, split_kind)
        _validate_stored_fit_trace(split_payload, split_kind)


def _validate_stored_radii(validation: Mapping[str, object], split_kind: str) -> None:
    radii = _as_mapping(
        validation.get("conformal_radii"),
        f"pretest artifact has invalid validation radii for the {split_kind} split",
    )
    if set(radii) != set(CONFORMAL_MODEL_NAMES):
        raise PretestValidationError(
            f"pretest artifact has invalid validation radii for the {split_kind} split"
        )
    for value in radii.values():
        if not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0.0:
            raise PretestValidationError(
                f"pretest artifact has invalid validation radii for the {split_kind} split"
            )


def _validate_stored_point_metrics(validation: Mapping[str, object], split_kind: str) -> None:
    stored_metrics = _as_mapping(
        validation.get("point_metrics"),
        f"pretest artifact has invalid validation model names for the {split_kind} split",
    )
    if set(stored_metrics) != set(MODEL_NAMES):
        raise PretestValidationError(
            f"pretest artifact has invalid validation model names for the {split_kind} split"
        )
    for metric in stored_metrics.values():
        values = _as_mapping(
            metric,
            f"pretest artifact has invalid validation point metrics for the {split_kind} split",
        )
        if set(values) != {"mae", "rmse"} or any(
            not isinstance(value, (int, float)) or not np.isfinite(value)
            for value in values.values()
        ):
            raise PretestValidationError(
                f"pretest artifact has invalid validation point metrics for the {split_kind} split"
            )


def _validate_stored_fit_trace(split_payload: Mapping[str, object], split_kind: str) -> None:
    fit_trace = _as_mapping(
        split_payload.get("fit_trace"),
        f"pretest artifact has invalid fit trace for the {split_kind} split",
    )
    model_fit_ids = _as_mapping(
        fit_trace.get("model_fit_ids"),
        f"pretest artifact has invalid model names for the {split_kind} split",
    )
    if set(model_fit_ids) != set(MODEL_NAMES):
        raise PretestValidationError(
            f"pretest artifact has invalid model names for the {split_kind} split"
        )


def _validate_stored_fit_trace_membership(
    split_payload: Mapping[str, object], membership: SplitMembership, split_kind: str
) -> None:
    fit_trace = _as_mapping(
        split_payload.get("fit_trace"),
        f"pretest artifact has invalid fit trace for the {split_kind} split",
    )
    expected_ids = list(membership.train_ids)
    if fit_trace.get("feature_fit_ids") != expected_ids:
        raise PretestValidationError(
            f"pretest artifact fit trace is not training-only for the {split_kind} split"
        )
    model_fit_ids = _as_mapping(
        fit_trace.get("model_fit_ids"),
        f"pretest artifact has invalid fit trace for the {split_kind} split",
    )
    for model_name in MODEL_NAMES:
        if model_fit_ids.get(model_name) != expected_ids:
            raise PretestValidationError(
                f"pretest artifact fit trace is not training-only for the {split_kind} split"
            )


def _as_mapping(value: object, message: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise PretestValidationError(message)
    return cast(Mapping[str, object], value)
