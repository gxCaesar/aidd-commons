from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from .evaluation import energy_metrics
from .protocol import DEVELOPMENT_SYSTEM_IDS, FROZEN_ALPHAS


class ModelContractError(ValueError):
    """Raised when a learned baseline diverges from the frozen fitting contract."""


@dataclass(frozen=True)
class FittedSystemRidge:
    scaler: StandardScaler
    model: Ridge
    energy_mean: float
    fit_row_ids: tuple[str, ...]
    alpha: float


@dataclass(frozen=True)
class SystemDevelopmentData:
    system_id: str
    train_features: np.ndarray
    train_energies: np.ndarray
    train_row_ids: tuple[str, ...]
    validation_features: np.ndarray
    validation_energies: np.ndarray


@dataclass(frozen=True)
class SharedAlphaSelection:
    selected_alpha: float
    median_validation_mae: Mapping[float, float]
    models: tuple[FittedSystemRidge, ...]


def fit_system_ridge(
    train_features: np.ndarray,
    train_energies: np.ndarray,
    train_row_ids: tuple[str, ...],
    *,
    alpha: float,
) -> FittedSystemRidge:
    if alpha not in FROZEN_ALPHAS:
        raise ModelContractError("alpha is outside the frozen Ridge grid")
    _validate_training_data(train_features, train_energies, train_row_ids)
    scaler = StandardScaler().fit(train_features)
    scaled_features = np.asarray(scaler.transform(train_features), dtype=float)
    energy_mean = float(np.mean(train_energies))
    model = Ridge(alpha=alpha, fit_intercept=False, solver="lsqr")
    model.fit(scaled_features, train_energies - energy_mean)
    return FittedSystemRidge(
        scaler=scaler,
        model=model,
        energy_mean=energy_mean,
        fit_row_ids=train_row_ids,
        alpha=alpha,
    )


def predict_system_ridge(fitted: FittedSystemRidge, features: np.ndarray) -> np.ndarray:
    if features.ndim != 2 or features.shape[0] == 0:
        raise ModelContractError("prediction features must be a non-empty two-dimensional matrix")
    if not bool(np.all(np.isfinite(features))):
        raise ModelContractError("prediction features must be finite")
    try:
        scaled_features = fitted.scaler.transform(features)
    except ValueError as error:
        raise ModelContractError("prediction features do not match the training columns") from error
    predictions = (
        np.asarray(fitted.model.predict(scaled_features), dtype=float) + fitted.energy_mean
    )
    if not bool(np.all(np.isfinite(predictions))):
        raise ModelContractError("Ridge predictions must be finite")
    return predictions


def train_mean_predictions(train_energies: np.ndarray, *, row_count: int) -> np.ndarray:
    if train_energies.ndim != 1 or train_energies.shape[0] == 0:
        raise ModelContractError("train mean requires a non-empty one-dimensional energy vector")
    if not bool(np.all(np.isfinite(train_energies))) or row_count < 0:
        raise ModelContractError("train mean inputs must be finite with a non-negative row count")
    return np.full(row_count, float(np.mean(train_energies)), dtype=float)


def select_shared_alpha(
    development_systems: Sequence[SystemDevelopmentData],
) -> SharedAlphaSelection:
    systems = tuple(development_systems)
    if tuple(system.system_id for system in systems) != DEVELOPMENT_SYSTEM_IDS:
        raise ModelContractError(
            "shared alpha selection requires ethanol then malonaldehyde development data"
        )

    scores: dict[float, float] = {}
    fitted_by_alpha: dict[float, tuple[FittedSystemRidge, ...]] = {}
    for alpha in FROZEN_ALPHAS:
        per_system_mae: list[float] = []
        fitted_models: list[FittedSystemRidge] = []
        for system in systems:
            fitted = fit_system_ridge(
                system.train_features,
                system.train_energies,
                system.train_row_ids,
                alpha=alpha,
            )
            predictions = predict_system_ridge(fitted, system.validation_features)
            per_system_mae.append(energy_metrics(system.validation_energies, predictions).mae)
            fitted_models.append(fitted)
        scores[alpha] = float(np.median(np.asarray(per_system_mae, dtype=float)))
        fitted_by_alpha[alpha] = tuple(fitted_models)

    selected_alpha = select_alpha_from_scores(scores)
    return SharedAlphaSelection(
        selected_alpha=selected_alpha,
        median_validation_mae=dict(scores),
        models=fitted_by_alpha[selected_alpha],
    )


def select_alpha_from_scores(validation_mae: Mapping[float, float]) -> float:
    if set(validation_mae) != set(FROZEN_ALPHAS):
        raise ModelContractError("validation scores must cover the frozen Ridge grid")
    if not all(np.isfinite(value) for value in validation_mae.values()):
        raise ModelContractError("validation scores must be finite")
    return min(FROZEN_ALPHAS, key=lambda alpha: (validation_mae[alpha], -alpha))


def _validate_training_data(
    features: np.ndarray, energies: np.ndarray, row_ids: tuple[str, ...]
) -> None:
    if features.ndim != 2 or features.shape[0] == 0:
        raise ModelContractError("training features must be a non-empty two-dimensional matrix")
    if energies.ndim != 1 or energies.shape[0] != features.shape[0]:
        raise ModelContractError("training energies must align with feature rows")
    if len(row_ids) != features.shape[0] or len(set(row_ids)) != len(row_ids):
        raise ModelContractError("training row IDs must be unique and align with feature rows")
    if not bool(np.all(np.isfinite(features))) or not bool(np.all(np.isfinite(energies))):
        raise ModelContractError("training features and energies must be finite")
