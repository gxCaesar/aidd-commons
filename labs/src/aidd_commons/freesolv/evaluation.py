from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import numpy as np


class EvaluationContractError(ValueError):
    """Raised when frozen evaluation inputs or outputs violate the protocol."""


@dataclass(frozen=True)
class PointMetrics:
    mae: float
    rmse: float


@dataclass(frozen=True)
class IntervalMetrics:
    coverage: float
    mean_width: float


def assert_finite_predictions(predictions: np.ndarray) -> None:
    if not np.isfinite(predictions).all():
        raise EvaluationContractError("non-finite predictions are not allowed")


def point_metrics(targets: np.ndarray, predictions: np.ndarray) -> PointMetrics:
    _validate_pair(targets, predictions)
    errors = np.abs(targets - predictions)
    return PointMetrics(
        mae=float(np.mean(errors)),
        rmse=float(np.sqrt(np.mean(np.square(errors)))),
    )


def conformal_radius(targets: np.ndarray, predictions: np.ndarray, coverage: float = 0.9) -> float:
    _validate_pair(targets, predictions)
    if not 0.0 < coverage < 1.0:
        raise EvaluationContractError("conformal coverage must be strictly between zero and one")
    rank = ceil((len(targets) + 1) * coverage)
    if rank > len(targets):
        raise EvaluationContractError(
            "validation partition is too small for a finite split-conformal radius"
        )
    residuals = np.sort(np.abs(targets - predictions))
    radius = float(residuals[rank - 1])
    if not np.isfinite(radius):
        raise EvaluationContractError("non-finite conformal radius")
    return radius


def interval_metrics(
    targets: np.ndarray, predictions: np.ndarray, radius: float
) -> IntervalMetrics:
    _validate_pair(targets, predictions)
    if not np.isfinite(radius) or radius < 0.0:
        raise EvaluationContractError("conformal radius must be finite and non-negative")
    covered = np.abs(targets - predictions) <= radius
    return IntervalMetrics(coverage=float(np.mean(covered)), mean_width=2.0 * radius)


def _validate_pair(targets: np.ndarray, predictions: np.ndarray) -> None:
    if targets.ndim != 1 or predictions.ndim != 1:
        raise EvaluationContractError("targets and predictions must be one-dimensional")
    if len(targets) == 0 or len(targets) != len(predictions):
        raise EvaluationContractError("targets and predictions must have equal non-zero length")
    if not np.isfinite(targets).all():
        raise EvaluationContractError("non-finite targets are not allowed")
    assert_finite_predictions(predictions)
