from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.freesolv.data import MoleculeRecord
from aidd_commons.freesolv.evaluation import (
    EvaluationContractError,
    assert_finite_predictions,
    conformal_radius,
    point_metrics,
)
from aidd_commons.freesolv.models import (
    FeatureContractError,
    FitTrace,
    ModelContractError,
    assert_training_only_fit,
    build_morgan_features,
    fit_frozen_models,
    predict_models,
)


def records() -> tuple[MoleculeRecord, ...]:
    smiles = ("CCO", "CCN", "CCC", "CCCl", "CCBr", "CCF")
    return tuple(
        MoleculeRecord(
            source_id=f"mobley_fixture_{index}",
            input_smiles=smile,
            canonical_smiles=smile,
            target_kcal_mol=float(index) - 3.0,
        )
        for index, smile in enumerate(smiles)
    )


def test_morgan_features_are_numeric_and_reject_target_leakage() -> None:
    feature_matrix = build_morgan_features(records())

    assert feature_matrix.shape == (6, 2048)
    assert feature_matrix.dtype.kind in {"f", "i", "u"}
    with pytest.raises(FeatureContractError, match="target"):
        build_morgan_features(records(), feature_sources=("canonical_smiles", "target_kcal_mol"))


def test_frozen_models_capture_train_only_fit_trace_and_fixed_hyperparameters() -> None:
    train_records = records()[:4]
    fitted = fit_frozen_models(train_records)
    predictions = predict_models(fitted, records()[4:])

    assert fitted.ridge.alpha == 1.0
    assert fitted.random_forest.n_estimators == 500
    assert fitted.random_forest.max_features == "sqrt"
    assert fitted.random_forest.min_samples_leaf == 1
    assert fitted.random_forest.random_state == 20_260_904
    assert fitted.random_forest.n_jobs == 1
    assert_training_only_fit(
        fitted.fit_trace, tuple(record.canonical_smiles for record in train_records)
    )
    assert set(predictions) == {"train_mean", "morgan_ridge", "morgan_random_forest"}
    for values in predictions.values():
        assert_finite_predictions(values)


def test_training_only_trace_rejects_preprocessing_fitted_outside_train() -> None:
    trace = FitTrace(
        model_fit_ids={
            "train_mean": ("train",),
            "morgan_ridge": ("train", "validation"),
            "morgan_random_forest": ("train",),
        },
        feature_fit_ids=("train", "validation"),
    )

    with pytest.raises(ModelContractError, match="outside train"):
        assert_training_only_fit(trace, ("train",))


def test_finite_prediction_guard_and_metric_formulas() -> None:
    with pytest.raises(EvaluationContractError, match="non-finite"):
        assert_finite_predictions(np.array([0.0, np.nan]))

    metrics = point_metrics(np.array([0.0, 2.0, 4.0]), np.array([1.0, 2.0, 1.0]))
    assert metrics.mae == pytest.approx(4.0 / 3.0)
    assert metrics.rmse == pytest.approx(np.sqrt(10.0 / 3.0))


def test_split_conformal_uses_finite_sample_correction() -> None:
    targets = np.arange(1.0, 11.0)
    predictions = np.zeros(10)

    assert conformal_radius(targets, predictions, coverage=0.9) == 10.0
