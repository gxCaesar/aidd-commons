from __future__ import annotations

import json
import platform
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import numpy as np
import sklearn  # type: ignore[import-untyped]
from rdkit import rdBase

from aidd_commons.chembl_egfr.data import (
    AssayDataset,
    ParentActivityRecord,
    assert_parent_disjoint,
)
from aidd_commons.chembl_egfr.evaluation import regression_metrics
from aidd_commons.chembl_egfr.models import (
    MODEL_NAMES,
    TunedBaselines,
    predict_baselines,
    tune_baselines,
)
from aidd_commons.chembl_egfr.protocol import (
    EXPECTED_SCAFFOLD_COUNTS,
    EXTERNAL_ASSAY_ID,
    PRIMARY_ASSAY_ID,
    PROTOCOL_VERSION,
    execution_amendment_payload,
    protocol_payload,
)
from aidd_commons.chembl_egfr.splits import (
    ScaffoldSplitMembership,
    scaffold_split,
)

PRETEST_FILE_NAME = "pretest.json"
LOCKED_MARKER_FILE_NAME = "locked-evaluation.started.json"
LOCKED_METRICS_FILE_NAME = "locked-metrics.json"
LOCKED_OUTPUT_RELATIVE_PATH = Path("labs/chembl_egfr/results")
EVALUATION_COMMAND_PREFIX = (
    "env",
    "UV_CACHE_DIR=.cache/uv",
    "uv",
    "run",
    "python",
    "labs/chembl_egfr/run_lab.py",
    "evaluate-locked",
)


class PretestValidationError(ValueError):
    """Raised when development evidence differs from the frozen protocol."""


class LockedEvaluationError(ValueError):
    """Raised when the paired one-time evaluation boundary is violated."""


@dataclass(frozen=True)
class PretestArtifact:
    pretest_path: Path
    primary_split: str


@dataclass(frozen=True)
class _PreparedDevelopment:
    membership: ScaffoldSplitMembership
    models: TunedBaselines
    record_by_id: Mapping[str, ParentActivityRecord]
    train_records: tuple[ParentActivityRecord, ...]
    validation_records: tuple[ParentActivityRecord, ...]


def portable_locked_evaluation_command(cache_dir: Path, repository_root: Path) -> str:
    cache_argument = _repository_relative_path(cache_dir, repository_root)
    return shlex.join(
        (
            *EVALUATION_COMMAND_PREFIX,
            "--cache-dir",
            cache_argument,
            "--confirm-locked-evaluation",
        )
    )


def validate_frozen_scaffold_counts(primary: AssayDataset, external: AssayDataset) -> None:
    for dataset in (primary, external):
        membership = scaffold_split(dataset.records)
        observed = len(set(membership.grouping_keys.values()))
        expected = EXPECTED_SCAFFOLD_COUNTS.get(dataset.assay_chembl_id)
        if expected is None:
            raise PretestValidationError(
                f"assay is not part of the frozen scaffold contract: {dataset.assay_chembl_id}"
            )
        if observed != expected:
            raise PretestValidationError(
                f"assay {dataset.assay_chembl_id} has {observed} scaffold groups; "
                f"expected {expected}"
            )


def run_pretest(
    primary: AssayDataset,
    external: AssayDataset,
    output_dir: Path,
    *,
    planned_evaluation_command: str,
) -> PretestArtifact:
    output_dir.mkdir(parents=True, exist_ok=True)
    _validate_portable_command(planned_evaluation_command)
    _refuse_after_locked_evaluation(output_dir)
    payload = _build_pretest_payload(primary, external, planned_evaluation_command)
    pretest_path = output_dir / PRETEST_FILE_NAME
    if pretest_path.exists():
        stored = _read_json(pretest_path, PretestValidationError)
        if stored != payload:
            raise PretestValidationError(
                "existing pretest artifact differs from the current frozen development evidence"
            )
    else:
        _write_json(pretest_path, payload)
    return PretestArtifact(pretest_path=pretest_path, primary_split="scaffold")


def evaluate_locked(
    primary: AssayDataset,
    external: AssayDataset,
    output_dir: Path,
    *,
    command: str,
    confirmed: bool,
    repository_root: Path,
) -> Path:
    if not confirmed:
        raise LockedEvaluationError(
            "paired primary-test and replication evaluation requires explicit confirmation"
        )
    canonical_output_dir = repository_root.resolve() / LOCKED_OUTPUT_RELATIVE_PATH
    if output_dir.resolve() != canonical_output_dir:
        raise LockedEvaluationError(
            "locked evaluation must use the canonical output directory "
            f"{LOCKED_OUTPUT_RELATIVE_PATH.as_posix()}"
        )
    _validate_portable_command(command)
    _refuse_after_locked_evaluation(output_dir)
    pretest_path = output_dir / PRETEST_FILE_NAME
    if not pretest_path.exists():
        raise LockedEvaluationError("a passed pretest artifact is required before evaluation")
    stored_pretest = _read_json(pretest_path, LockedEvaluationError)
    prepared = _prepare_development(primary)
    expected_pretest = _build_pretest_payload(primary, external, command, prepared=prepared)
    if stored_pretest != expected_pretest:
        raise LockedEvaluationError(
            "pretest identity differs from the recomputed frozen development evidence"
        )

    primary_test = _records_for_ids(
        prepared.record_by_id,
        prepared.membership.test_ids,
    )
    _claim_locked_evaluation(output_dir, command)
    primary_predictions = predict_baselines(prepared.models, primary_test)
    external_predictions = predict_baselines(prepared.models, external.records)

    payload = {
        "schema_version": "aidd-commons.chembl-egfr-locked-results.v1",
        "execution_amendment": execution_amendment_payload(),
        "protocol_version": PROTOCOL_VERSION,
        "evaluation_command": command,
        "locked_evaluation_complete": True,
        "results": {
            "primary_test": _locked_result_payload(primary_test, primary_predictions),
            "assay_replication": _locked_result_payload(
                external.records,
                external_predictions,
            ),
        },
        "selected_alphas": dict(sorted(prepared.models.selected_alphas.items())),
        "software": _software_payload(),
    }
    metrics_path = output_dir / LOCKED_METRICS_FILE_NAME
    _write_json(metrics_path, payload)
    return metrics_path


def development_summary(pretest_path: Path) -> dict[str, object]:
    payload = _read_json(pretest_path, PretestValidationError)
    if payload.get("pretest_passed") is not True:
        raise PretestValidationError("cannot review a pretest artifact that did not pass")
    development = _mapping(payload.get("development"), "missing development evidence")
    data = _mapping(development.get("data"), "missing development data audit")
    membership = _mapping(development.get("membership"), "missing development split membership")
    validation = _mapping(development.get("validation"), "missing validation evidence")
    return {
        "schema_version": "aidd-commons.chembl-egfr-development-summary.v1",
        "artifact_type": "reviewed-development-summary",
        "protocol_version": payload.get("protocol_version"),
        "reviewed_on": "2026-09-05",
        "data": {
            "primary": data.get("primary"),
            "replication": data.get("replication"),
            "parent_overlap": data.get("parent_overlap"),
        },
        "split": {
            "actual_counts": membership.get("actual_counts"),
            "scaffold_counts": membership.get("scaffold_counts"),
            "target_counts": membership.get("target_counts"),
        },
        "selection": {
            "grid_scores": validation.get("grid_scores"),
            "metrics": validation.get("metrics"),
            "selected_alphas": validation.get("selected_alphas"),
        },
        "software": payload.get("software"),
        "locked_evaluations": payload.get("locked_evaluations"),
        "limitations": [
            "Validation metrics are model-selection evidence, not primary-test performance.",
            "The primary scaffold-disjoint test and assay-level replication have not run.",
            "Repeated parent measurements are aggregated by the frozen median rule "
            "and expose assay noise.",
        ],
    }


def write_development_summary(pretest_path: Path, summary_path: Path) -> Path:
    _write_json(summary_path, development_summary(pretest_path))
    return summary_path


def _build_pretest_payload(
    primary: AssayDataset,
    external: AssayDataset,
    planned_evaluation_command: str,
    *,
    prepared: _PreparedDevelopment | None = None,
) -> dict[str, object]:
    if primary.assay_chembl_id != PRIMARY_ASSAY_ID:
        raise PretestValidationError("primary dataset has the wrong assay ID")
    if external.assay_chembl_id != EXTERNAL_ASSAY_ID:
        raise PretestValidationError("replication dataset has the wrong assay ID")
    assert_parent_disjoint(primary, external)
    if prepared is None:
        prepared = _prepare_development(primary)
    validation_predictions = predict_baselines(
        prepared.models,
        prepared.validation_records,
    )
    validation_targets = _targets(prepared.validation_records)
    validation_metrics = {
        name: asdict(regression_metrics(validation_targets, predictions))
        for name, predictions in validation_predictions.items()
    }
    validation_rows = []
    for index, record in enumerate(prepared.validation_records):
        validation_rows.append(
            {
                "parent_molecule_chembl_id": record.parent_molecule_chembl_id,
                "target_pchembl": record.target_pchembl,
                "predictions": {
                    name: float(values[index])
                    for name, values in sorted(validation_predictions.items())
                },
            }
        )
    primary_scaffolds = len(set(prepared.membership.grouping_keys.values()))
    external_membership = scaffold_split(external.records)
    external_scaffolds = len(set(external_membership.grouping_keys.values()))
    return {
        "schema_version": "aidd-commons.chembl-egfr-pretest.v1",
        "protocol_version": PROTOCOL_VERSION,
        "pretest_passed": True,
        "planned_locked_evaluation_command": planned_evaluation_command,
        "protocol": protocol_payload(),
        "development": {
            "data": {
                "primary": _audit_payload(primary, include_label_noise=True),
                "replication": _audit_payload(external, include_label_noise=False),
                "parent_overlap": 0,
            },
            "membership": {
                **_membership_payload(prepared.membership),
                "scaffold_counts": {
                    "primary": primary_scaffolds,
                    "replication": external_scaffolds,
                },
            },
            "fit_trace": {
                "descriptor_preprocessor_fit_ids": list(
                    prepared.models.fit_trace.descriptor_preprocessor_fit_ids
                ),
                "model_fit_ids": {
                    name: list(ids)
                    for name, ids in sorted(prepared.models.fit_trace.model_fit_ids.items())
                },
            },
            "validation": {
                "grid_scores": {
                    name: [
                        {"alpha": score.alpha, "metrics": asdict(score.metrics)} for score in scores
                    ]
                    for name, scores in sorted(prepared.models.grid_scores.items())
                },
                "metrics": dict(sorted(validation_metrics.items())),
                "records": validation_rows,
                "selected_alphas": dict(sorted(prepared.models.selected_alphas.items())),
            },
        },
        "locked_evaluations": {"primary": "not_run", "replication": "not_run"},
        "software": _software_payload(),
    }


def _prepare_development(primary: AssayDataset) -> _PreparedDevelopment:
    membership = scaffold_split(primary.records)
    record_by_id = {record.parent_molecule_chembl_id: record for record in primary.records}
    train_records = _records_for_ids(record_by_id, membership.train_ids)
    validation_records = _records_for_ids(record_by_id, membership.validation_ids)
    if not membership.test_ids:
        raise PretestValidationError("locked primary test partition must not be empty")
    models = tune_baselines(train_records, validation_records)
    return _PreparedDevelopment(
        membership=membership,
        models=models,
        record_by_id=record_by_id,
        train_records=train_records,
        validation_records=validation_records,
    )


def _records_for_ids(
    record_by_id: Mapping[str, ParentActivityRecord], ids: Sequence[str]
) -> tuple[ParentActivityRecord, ...]:
    try:
        return tuple(record_by_id[parent_id] for parent_id in ids)
    except KeyError as error:
        raise PretestValidationError(
            f"split membership references an unknown parent molecule: {error.args[0]}"
        ) from error


def _membership_payload(membership: ScaffoldSplitMembership) -> dict[str, object]:
    return {
        "actual_counts": {
            "train": len(membership.train_ids),
            "validation": len(membership.validation_ids),
            "test": len(membership.test_ids),
        },
        "target_counts": asdict(membership.targets),
        "ids": {
            "train": list(membership.train_ids),
            "validation": list(membership.validation_ids),
            "test": list(membership.test_ids),
        },
        "grouping_keys": dict(sorted(membership.grouping_keys.items())),
    }


def _audit_payload(dataset: AssayDataset, *, include_label_noise: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "assay_chembl_id": dataset.assay_chembl_id,
        "input_rows": dataset.audit.input_rows,
        "retained_rows": dataset.audit.retained_rows,
        "parent_count": dataset.audit.parent_count,
        "duplicate_parent_count": dataset.audit.duplicate_parent_count,
        "exclusion_counts": dict(sorted(dataset.audit.exclusion_counts.items())),
    }
    if include_label_noise:
        payload["median_duplicate_range"] = dataset.audit.median_duplicate_range
        payload["maximum_duplicate_range"] = dataset.audit.maximum_duplicate_range
    return payload


def _locked_result_payload(
    records: Sequence[ParentActivityRecord],
    predictions: Mapping[str, np.ndarray],
) -> dict[str, object]:
    targets = _targets(records)
    if set(predictions) != set(MODEL_NAMES):
        raise LockedEvaluationError("locked predictions omit a frozen baseline")
    return {
        "count": len(records),
        "metrics": {
            name: asdict(regression_metrics(targets, values))
            for name, values in sorted(predictions.items())
        },
        "predictions": [
            {
                "parent_molecule_chembl_id": record.parent_molecule_chembl_id,
                "target_pchembl": record.target_pchembl,
                "predictions": {
                    name: float(values[index]) for name, values in sorted(predictions.items())
                },
            }
            for index, record in enumerate(records)
        ],
    }


def _targets(records: Sequence[ParentActivityRecord]) -> np.ndarray:
    return np.asarray([record.target_pchembl for record in records], dtype=float)


def _software_payload() -> dict[str, str]:
    return {
        "numpy": np.__version__,
        "python": platform.python_version(),
        "rdkit": rdBase.rdkitVersion,
        "scikit_learn": sklearn.__version__,
    }


def _claim_locked_evaluation(output_dir: Path, command: str) -> None:
    marker_path = output_dir / LOCKED_MARKER_FILE_NAME
    try:
        with marker_path.open("x", encoding="utf-8") as handle:
            json.dump(
                {"command": command, "status": "started"},
                handle,
                sort_keys=True,
            )
            handle.write("\n")
    except FileExistsError as error:
        raise LockedEvaluationError(
            "paired locked evaluation was already claimed or completed"
        ) from error


def _refuse_after_locked_evaluation(output_dir: Path) -> None:
    if (output_dir / LOCKED_MARKER_FILE_NAME).exists() or (
        output_dir / LOCKED_METRICS_FILE_NAME
    ).exists():
        raise LockedEvaluationError("paired locked evaluation was already claimed or completed")


def _repository_relative_path(path: Path, repository_root: Path) -> str:
    root = repository_root.resolve()
    candidate = path if path.is_absolute() else root / path
    try:
        return candidate.resolve().relative_to(root).as_posix()
    except ValueError as error:
        raise LockedEvaluationError(
            "evaluation cache and output paths must be repository-relative"
        ) from error


def _validate_portable_command(command: str) -> None:
    tokens = shlex.split(command)
    expected_length = len(EVALUATION_COMMAND_PREFIX) + 3
    if (
        len(tokens) != expected_length
        or tuple(tokens[: len(EVALUATION_COMMAND_PREFIX)]) != EVALUATION_COMMAND_PREFIX
        or tokens[len(EVALUATION_COMMAND_PREFIX)] != "--cache-dir"
        or tokens[-1] != "--confirm-locked-evaluation"
    ):
        raise LockedEvaluationError("locked command does not use the frozen invocation")
    if any(token.startswith("/") for token in tokens):
        raise LockedEvaluationError("locked command must not contain an absolute path")


def _read_json(
    path: Path, error_type: type[PretestValidationError] | type[LockedEvaluationError]
) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise error_type(f"could not read JSON artifact {path}: {error}") from error
    if not isinstance(payload, Mapping):
        raise error_type(f"JSON artifact is not an object: {path}")
    return cast(Mapping[str, object], payload)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _mapping(value: object, message: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise PretestValidationError(message)
    return cast(Mapping[str, object], value)
