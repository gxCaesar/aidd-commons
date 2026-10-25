from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]

from aidd_commons.chembl_egfr.data import ParentActivityRecord
from aidd_commons.chembl_egfr.evaluation import RegressionMetrics, regression_metrics
from aidd_commons.chembl_egfr.features import (
    FeatureMatrix,
    build_descriptor_matrix,
    build_morgan_matrix,
)
from aidd_commons.chembl_egfr.protocol import (
    RIDGE_ALPHAS,
    RIDGE_MAX_ITERATIONS,
    RIDGE_SOLVER,
    RIDGE_TOLERANCE,
)

MODEL_NAMES = ("train_mean", "descriptor_ridge", "morgan_ridge")


class ModelContractError(ValueError):
    """Raised when fitting or selection differs from the frozen baseline contract."""


@dataclass(frozen=True)
class DescriptorTransform:
    names: tuple[str, ...]
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    fit_ids: tuple[str, ...]

    def transform(self, matrix: FeatureMatrix) -> np.ndarray:
        if matrix.names != self.names:
            raise ModelContractError("descriptor columns differ from the fitted transform")
        if matrix.values.ndim != 2 or matrix.values.shape[1] != len(self.names):
            raise ModelContractError("descriptor matrix has invalid dimensions")
        finite = np.isfinite(matrix.values)
        imputed = np.where(finite, matrix.values, self.medians)
        transformed = (imputed - self.means) / self.scales
        if not np.isfinite(transformed).all():
            raise ModelContractError("descriptor transform produced non-finite features")
        return np.asarray(transformed, dtype=float)


@dataclass(frozen=True)
class FitTrace:
    descriptor_preprocessor_fit_ids: tuple[str, ...]
    model_fit_ids: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class ValidationScore:
    alpha: float
    metrics: RegressionMetrics


@dataclass(frozen=True)
class TunedBaselines:
    train_mean: float
    descriptor_ridge: Ridge
    morgan_ridge: Ridge
    descriptor_transform: DescriptorTransform
    selected_alphas: Mapping[str, float]
    grid_scores: Mapping[str, tuple[ValidationScore, ...]]
    fit_trace: FitTrace


def fit_descriptor_transform(
    matrix: FeatureMatrix, fit_ids: tuple[str, ...]
) -> DescriptorTransform:
    if matrix.values.ndim != 2 or matrix.values.shape != (len(fit_ids), len(matrix.names)):
        raise ModelContractError("descriptor fit matrix and IDs have incompatible dimensions")
    if not fit_ids:
        raise ModelContractError("descriptor preprocessing requires a non-empty training set")
    medians = np.empty(matrix.values.shape[1], dtype=float)
    for column_index in range(matrix.values.shape[1]):
        column = matrix.values[:, column_index]
        finite_values = column[np.isfinite(column)]
        medians[column_index] = float(np.median(finite_values)) if len(finite_values) else 0.0
    imputed = np.where(np.isfinite(matrix.values), matrix.values, medians)
    means = np.mean(imputed, axis=0)
    scales = np.std(imputed, axis=0, ddof=0)
    scales = np.where(scales == 0.0, 1.0, scales)
    if (
        not np.isfinite(medians).all()
        or not np.isfinite(means).all()
        or not np.isfinite(scales).all()
    ):
        raise ModelContractError("descriptor preprocessing statistics must be finite")
    return DescriptorTransform(
        names=matrix.names,
        medians=medians,
        means=means,
        scales=scales,
        fit_ids=fit_ids,
    )


def tune_baselines(
    train_records: Sequence[ParentActivityRecord],
    validation_records: Sequence[ParentActivityRecord],
) -> TunedBaselines:
    train_ids = _validate_partition(train_records, "training")
    _validate_partition(validation_records, "validation")
    train_targets = _targets(train_records)
    validation_targets = _targets(validation_records)

    descriptor_train = build_descriptor_matrix(train_records)
    descriptor_validation = build_descriptor_matrix(validation_records)
    descriptor_transform = fit_descriptor_transform(descriptor_train, train_ids)
    descriptor_train_values = descriptor_transform.transform(descriptor_train)
    descriptor_validation_values = descriptor_transform.transform(descriptor_validation)

    morgan_train_values = build_morgan_matrix(train_records).values.astype(float)
    morgan_validation_values = build_morgan_matrix(validation_records).values.astype(float)

    descriptor_scores, descriptor_models = _score_grid(
        descriptor_train_values,
        train_targets,
        descriptor_validation_values,
        validation_targets,
    )
    morgan_scores, morgan_models = _score_grid(
        morgan_train_values,
        train_targets,
        morgan_validation_values,
        validation_targets,
    )
    descriptor_alpha = select_alpha({score.alpha: score.metrics.mae for score in descriptor_scores})
    morgan_alpha = select_alpha({score.alpha: score.metrics.mae for score in morgan_scores})

    fit_trace = FitTrace(
        descriptor_preprocessor_fit_ids=descriptor_transform.fit_ids,
        model_fit_ids={name: train_ids for name in MODEL_NAMES},
    )
    assert_training_only_fit(fit_trace, train_ids)
    return TunedBaselines(
        train_mean=float(np.mean(train_targets)),
        descriptor_ridge=descriptor_models[descriptor_alpha],
        morgan_ridge=morgan_models[morgan_alpha],
        descriptor_transform=descriptor_transform,
        selected_alphas={
            "descriptor_ridge": descriptor_alpha,
            "morgan_ridge": morgan_alpha,
        },
        grid_scores={
            "descriptor_ridge": descriptor_scores,
            "morgan_ridge": morgan_scores,
        },
        fit_trace=fit_trace,
    )


def predict_baselines(
    models: TunedBaselines, records: Sequence[ParentActivityRecord]
) -> dict[str, np.ndarray]:
    if not records:
        return {name: np.empty(0, dtype=float) for name in MODEL_NAMES}
    descriptor_values = models.descriptor_transform.transform(build_descriptor_matrix(records))
    morgan_values = build_morgan_matrix(records).values.astype(float)
    predictions = {
        "train_mean": np.full(len(records), models.train_mean, dtype=float),
        "descriptor_ridge": np.asarray(
            models.descriptor_ridge.predict(descriptor_values), dtype=float
        ),
        "morgan_ridge": np.asarray(models.morgan_ridge.predict(morgan_values), dtype=float),
    }
    if any(not np.isfinite(values).all() for values in predictions.values()):
        raise ModelContractError("baseline prediction contains a non-finite value")
    return predictions


def select_alpha(validation_mae: Mapping[float, float]) -> float:
    if set(validation_mae) != set(RIDGE_ALPHAS):
        raise ModelContractError("validation scores do not cover the frozen Ridge grid")
    if any(not np.isfinite(value) for value in validation_mae.values()):
        raise ModelContractError("validation MAE must be finite")
    return min(RIDGE_ALPHAS, key=lambda alpha: (validation_mae[alpha], alpha))


def assert_training_only_fit(trace: FitTrace, train_ids: tuple[str, ...]) -> None:
    if trace.descriptor_preprocessor_fit_ids != train_ids:
        raise ModelContractError("descriptor preprocessing was fitted outside train")
    if set(trace.model_fit_ids) != set(MODEL_NAMES):
        raise ModelContractError("fit trace does not cover every frozen baseline")
    for name, fit_ids in trace.model_fit_ids.items():
        if fit_ids != train_ids:
            raise ModelContractError(f"{name} was fitted outside train")


def _score_grid(
    train_values: np.ndarray,
    train_targets: np.ndarray,
    validation_values: np.ndarray,
    validation_targets: np.ndarray,
) -> tuple[tuple[ValidationScore, ...], dict[float, Ridge]]:
    scores: list[ValidationScore] = []
    models: dict[float, Ridge] = {}
    for alpha in RIDGE_ALPHAS:
        model = Ridge(
            alpha=alpha,
            fit_intercept=True,
            solver=RIDGE_SOLVER,
            tol=RIDGE_TOLERANCE,
            max_iter=RIDGE_MAX_ITERATIONS,
        )
        model.fit(train_values, train_targets)
        predictions = np.asarray(model.predict(validation_values), dtype=float)
        scores.append(
            ValidationScore(
                alpha=alpha,
                metrics=regression_metrics(validation_targets, predictions),
            )
        )
        models[alpha] = model
    return tuple(scores), models


def _validate_partition(records: Sequence[ParentActivityRecord], name: str) -> tuple[str, ...]:
    if not records:
        raise ModelContractError(f"{name} partition must not be empty")
    ids = tuple(record.parent_molecule_chembl_id for record in records)
    if len(ids) != len(set(ids)):
        raise ModelContractError(f"{name} partition contains duplicate parent molecules")
    targets = _targets(records)
    if not np.isfinite(targets).all():
        raise ModelContractError(f"{name} partition contains non-finite targets")
    return ids


def _targets(records: Sequence[ParentActivityRecord]) -> np.ndarray:
    return np.asarray([record.target_pchembl for record in records], dtype=float)
