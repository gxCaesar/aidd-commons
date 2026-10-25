from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.chembl_egfr.data import ParentActivityRecord
from aidd_commons.chembl_egfr.evaluation import EvaluationContractError, regression_metrics
from aidd_commons.chembl_egfr.features import build_descriptor_matrix, build_morgan_matrix
from aidd_commons.chembl_egfr.models import (
    MODEL_NAMES,
    ModelContractError,
    predict_baselines,
    select_alpha,
    tune_baselines,
)
from aidd_commons.chembl_egfr.protocol import RIDGE_ALPHAS, descriptor_names


def record(index: int, smiles: str, target: float) -> ParentActivityRecord:
    return ParentActivityRecord(
        assay_chembl_id="CHEMBL5736995",
        parent_molecule_chembl_id=f"CHEMBL_MODEL_{index}",
        canonical_smiles=smiles,
        target_pchembl=target,
        activity_ids=(index,),
        replicate_count=1,
        pchembl_range=0.0,
    )


def model_records() -> tuple[ParentActivityRecord, ...]:
    smiles = (
        "c1ccccc1",
        "C1CCCCC1",
        "c1ccncc1",
        "c1ccoc1",
        "c1ccsc1",
        "C1CCCC1",
        "C1CCC1",
        "C1CC1",
        "c1ncncc1",
        "O1CCOCC1",
        "N1CCNCC1",
        "c1ccc2ccccc2c1",
    )
    return tuple(record(index, value, 6.0 + 0.2 * index) for index, value in enumerate(smiles, 1))


def test_feature_builders_are_target_independent_and_match_frozen_dimensions() -> None:
    records = model_records()[:3]
    shifted = tuple(
        record(index + 20, item.canonical_smiles, item.target_pchembl + 50.0)
        for index, item in enumerate(records)
    )

    descriptors = build_descriptor_matrix(records)
    shifted_descriptors = build_descriptor_matrix(shifted)
    morgan = build_morgan_matrix(records)
    shifted_morgan = build_morgan_matrix(shifted)

    assert descriptors.names == descriptor_names()
    assert descriptors.values.shape == (3, 214)
    assert morgan.values.shape == (3, 2048)
    np.testing.assert_allclose(descriptors.values, shifted_descriptors.values, equal_nan=True)
    np.testing.assert_array_equal(morgan.values, shifted_morgan.values)
    assert set(np.unique(morgan.values)).issubset({0, 1})


def test_baseline_tuning_is_train_only_deterministic_and_covers_the_frozen_grid() -> None:
    records = model_records()
    train = records[:9]
    validation = records[9:]

    first = tune_baselines(train, validation)
    second = tune_baselines(train, validation)
    predictions = predict_baselines(first, validation)
    train_ids = tuple(record.parent_molecule_chembl_id for record in train)

    assert first.selected_alphas == second.selected_alphas
    assert first.fit_trace.descriptor_preprocessor_fit_ids == train_ids
    assert set(first.fit_trace.model_fit_ids) == set(MODEL_NAMES)
    assert all(ids == train_ids for ids in first.fit_trace.model_fit_ids.values())
    assert set(first.grid_scores) == {"descriptor_ridge", "morgan_ridge"}
    assert all(
        tuple(score.alpha for score in scores) == RIDGE_ALPHAS
        for scores in first.grid_scores.values()
    )
    assert set(predictions) == set(MODEL_NAMES)
    assert all(
        values.shape == (3,) and np.isfinite(values).all() for values in predictions.values()
    )


def test_alpha_selection_uses_validation_mae_then_smaller_alpha() -> None:
    scores = {alpha: 0.9 for alpha in RIDGE_ALPHAS}
    scores.update({0.1: 0.5, 1.0: 0.4, 10.0: 0.4})
    assert select_alpha(scores) == 1.0
    with pytest.raises(ModelContractError, match="frozen Ridge grid"):
        select_alpha({0.1: 0.5})


def test_metrics_include_tied_rank_spearman_and_explicit_constant_status() -> None:
    metrics = regression_metrics(
        np.array([1.0, 2.0, 3.0]),
        np.array([3.0, 1.0, 2.0]),
    )
    assert metrics.mae == pytest.approx(4.0 / 3.0)
    assert metrics.rmse == pytest.approx(np.sqrt(2.0))
    assert metrics.spearman == pytest.approx(-0.5)
    assert metrics.spearman_status == "defined"

    constant = regression_metrics(np.array([1.0, 2.0]), np.array([4.0, 4.0]))
    assert constant.spearman is None
    assert constant.spearman_status == "undefined_constant_prediction"

    with pytest.raises(EvaluationContractError, match="finite"):
        regression_metrics(np.array([1.0, np.nan]), np.array([1.0, 2.0]))
