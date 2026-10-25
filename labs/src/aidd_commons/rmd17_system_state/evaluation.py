from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np


class EvaluationContractError(ValueError):
    """Raised when energy metrics receive invalid protocol inputs."""


@dataclass(frozen=True)
class EnergyMetrics:
    mae: float
    rmse: float
    target_range: float


@dataclass(frozen=True)
class SystemMAEAggregate:
    median_mae: float
    mae_range: float


def energy_metrics(targets: np.ndarray, predictions: np.ndarray) -> EnergyMetrics:
    _validate_pair(targets, predictions)
    safe_targets = _as_safe_float64("targets", targets)
    safe_predictions = _as_safe_float64("predictions", predictions)
    with np.errstate(over="ignore", invalid="ignore"):
        errors = safe_targets - safe_predictions
        target_range = float(np.max(safe_targets) - np.min(safe_targets))
    if not bool(np.all(np.isfinite(errors))) or not np.isfinite(target_range):
        raise EvaluationContractError(
            "targets and predictions must have finite float64 differences"
        )
    absolute_errors = np.abs(errors)
    error_scale = float(np.max(absolute_errors))
    if error_scale == 0.0:
        mae = 0.0
        rmse = 0.0
    else:
        normalized_errors = errors / error_scale
        mae = error_scale * float(np.mean(np.abs(normalized_errors)))
        rmse = error_scale * float(np.sqrt(np.mean(np.square(normalized_errors))))
    return EnergyMetrics(
        mae=mae,
        rmse=rmse,
        target_range=target_range,
    )


def aggregate_system_maes(per_system_mae: Mapping[str, float]) -> SystemMAEAggregate:
    if not per_system_mae:
        raise EvaluationContractError("at least one per-system MAE is required")
    values = np.asarray(tuple(per_system_mae.values()), dtype=float)
    if not bool(np.all(np.isfinite(values))):
        raise EvaluationContractError("per-system MAEs must be finite")
    return SystemMAEAggregate(
        median_mae=float(np.median(values)),
        mae_range=float(np.max(values) - np.min(values)),
    )


def _validate_pair(targets: np.ndarray, predictions: np.ndarray) -> None:
    if targets.ndim != 1 or predictions.ndim != 1:
        raise EvaluationContractError("targets and predictions must be one-dimensional")
    if targets.shape[0] == 0 or targets.shape != predictions.shape:
        raise EvaluationContractError("targets and predictions must have equal non-zero length")
    if not _is_real_numeric_dtype(targets.dtype) or not _is_real_numeric_dtype(predictions.dtype):
        raise EvaluationContractError(
            "targets and predictions must use real integer or floating dtypes"
        )
    if not bool(np.all(np.isfinite(targets))) or not bool(np.all(np.isfinite(predictions))):
        raise EvaluationContractError("targets and predictions must be finite")


def _as_safe_float64(name: str, values: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore", invalid="ignore"):
        converted = np.asarray(values, dtype=np.float64)
    if not bool(np.all(np.isfinite(converted))):
        raise EvaluationContractError(f"{name} must be representable as finite float64 values")
    return converted


def _is_real_numeric_dtype(dtype: np.dtype[np.generic]) -> bool:
    return np.issubdtype(dtype, np.integer) or np.issubdtype(dtype, np.floating)
