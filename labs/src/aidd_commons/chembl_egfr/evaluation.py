from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

SpearmanStatus = Literal[
    "defined",
    "undefined_constant_prediction",
    "undefined_constant_target",
]


class EvaluationContractError(ValueError):
    """Raised when regression metrics receive invalid locked-protocol inputs."""


@dataclass(frozen=True)
class RegressionMetrics:
    mae: float
    rmse: float
    spearman: float | None
    spearman_status: SpearmanStatus


def regression_metrics(targets: np.ndarray, predictions: np.ndarray) -> RegressionMetrics:
    _validate_pair(targets, predictions)
    errors = targets - predictions
    target_ranks = _average_ranks(targets)
    prediction_ranks = _average_ranks(predictions)
    if np.ptp(prediction_ranks) == 0.0:
        spearman = None
        spearman_status: SpearmanStatus = "undefined_constant_prediction"
    elif np.ptp(target_ranks) == 0.0:
        spearman = None
        spearman_status = "undefined_constant_target"
    else:
        coefficient = float(np.corrcoef(target_ranks, prediction_ranks)[0, 1])
        if not is_finite_number(coefficient):
            raise EvaluationContractError("Spearman correlation is not finite")
        spearman = float(np.clip(coefficient, -1.0, 1.0))
        spearman_status = "defined"
    return RegressionMetrics(
        mae=float(np.mean(np.abs(errors))),
        rmse=float(np.sqrt(np.mean(np.square(errors)))),
        spearman=spearman,
        spearman_status=spearman_status,
    )


def is_finite_number(value: float) -> bool:
    return bool(np.isfinite(value))


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    return ranks


def _validate_pair(targets: np.ndarray, predictions: np.ndarray) -> None:
    if targets.ndim != 1 or predictions.ndim != 1:
        raise EvaluationContractError("targets and predictions must be one-dimensional")
    if len(targets) == 0 or len(targets) != len(predictions):
        raise EvaluationContractError("targets and predictions must have equal non-zero length")
    if not np.isfinite(targets).all() or not np.isfinite(predictions).all():
        raise EvaluationContractError("targets and predictions must be finite")
