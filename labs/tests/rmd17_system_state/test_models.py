from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.rmd17_system_state.evaluation import (
    aggregate_system_maes,
    energy_metrics,
)
from aidd_commons.rmd17_system_state.models import (
    SystemDevelopmentData,
    fit_system_ridge,
    predict_system_ridge,
    select_alpha_from_scores,
    select_shared_alpha,
    train_mean_predictions,
)


def test_system_ridge_uses_train_only_scaling_and_energy_centering() -> None:
    train_features = np.array([[0.0], [1.0], [2.0]])
    train_energies = np.array([10.0, 11.0, 12.0])
    fitted = fit_system_ridge(
        train_features,
        train_energies,
        ("ethanol:0", "ethanol:1", "ethanol:2"),
        alpha=1.0,
    )

    assert fitted.fit_row_ids == ("ethanol:0", "ethanol:1", "ethanol:2")
    assert fitted.energy_mean == pytest.approx(11.0)
    assert fitted.scaler.mean_.tolist() == pytest.approx([1.0])
    assert fitted.model.fit_intercept is False
    predictions = predict_system_ridge(fitted, np.array([[3.0]]))
    assert predictions.shape == (1,)
    assert np.isfinite(predictions).all()


def test_train_mean_control_uses_only_training_energies() -> None:
    predictions = train_mean_predictions(np.array([10.0, 11.0, 12.0]), row_count=2)

    assert np.array_equal(predictions, np.array([11.0, 11.0]))


def test_shared_alpha_selection_uses_median_over_systems_without_validation_refit() -> None:
    development_systems = (
        SystemDevelopmentData(
            system_id="ethanol",
            train_features=np.array([[0.0], [1.0], [2.0]]),
            train_energies=np.array([0.0, 1.0, 2.0]),
            train_row_ids=("ethanol:0", "ethanol:1", "ethanol:2"),
            validation_features=np.array([[3.0], [4.0]]),
            validation_energies=np.array([3.0, 4.0]),
        ),
        SystemDevelopmentData(
            system_id="malonaldehyde",
            train_features=np.array([[0.0], [2.0], [4.0]]),
            train_energies=np.array([1.0, 3.0, 5.0]),
            train_row_ids=("malonaldehyde:0", "malonaldehyde:1", "malonaldehyde:2"),
            validation_features=np.array([[6.0], [8.0]]),
            validation_energies=np.array([7.0, 9.0]),
        ),
    )

    selection = select_shared_alpha(development_systems)

    assert set(selection.median_validation_mae) == {
        0.001,
        0.01,
        0.1,
        1.0,
        10.0,
        100.0,
        1000.0,
    }
    assert selection.selected_alpha in selection.median_validation_mae
    assert all(
        fitted.fit_row_ids == system.train_row_ids
        for system, fitted in zip(development_systems, selection.models, strict=True)
    )


def test_exact_alpha_ties_choose_larger_alpha() -> None:
    scores = {0.001: 1.0, 0.01: 1.0, 0.1: 1.0, 1.0: 1.0, 10.0: 1.0, 100.0: 1.0, 1000.0: 1.0}

    assert select_alpha_from_scores(scores) == 1000.0


def test_literal_energy_metrics_and_per_system_aggregation_do_not_pool_frames() -> None:
    metrics = energy_metrics(np.array([1.0, 3.0]), np.array([2.0, 1.0]))
    aggregate = aggregate_system_maes({"ethanol": 1.0, "malonaldehyde": 5.0})

    assert metrics.mae == pytest.approx(1.5)
    assert metrics.rmse == pytest.approx(np.sqrt(2.5))
    assert metrics.target_range == pytest.approx(2.0)
    assert aggregate.median_mae == pytest.approx(3.0)
    assert aggregate.mae_range == pytest.approx(4.0)


def test_energy_metrics_promote_extreme_int64_before_difference_and_square() -> None:
    maximum = np.iinfo(np.int64).max
    minimum = np.iinfo(np.int64).min
    targets = np.array([minimum, maximum], dtype=np.int64)
    predictions = np.array([maximum, minimum], dtype=np.int64)

    metrics = energy_metrics(targets, predictions)

    expected_error = float(maximum) - float(minimum)
    assert metrics.mae == pytest.approx(expected_error)
    assert metrics.rmse == pytest.approx(expected_error)
    assert metrics.target_range == pytest.approx(expected_error)
