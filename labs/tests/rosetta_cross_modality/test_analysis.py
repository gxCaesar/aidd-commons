"""The analysis: the ridge map, the splits, the null and the statistics.

These are literal oracles on small matrices. A plant the map must recover,
a fold that must be refused, a permutation that must destroy the pairing and
a variance decomposition that must close are all checked against numbers
that can be worked out by hand.
"""

from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.rosetta_cross_modality.analysis import (
    AnalysisContractError,
    Fold,
    batch_blocked_folds,
    evaluate,
    fit_ridge,
    neighbourhood_concordance,
    permute_within_group,
    plate_blocked_folds,
    predict,
    random_folds,
    select_alpha,
    size_matched_partition_folds,
    size_matched_random_folds,
    variance_shares,
)

ALPHAS = (1.0, 10.0, 100.0)


def _planted(seed: int = 3, rows: int = 40, features: int = 6) -> tuple:
    state = np.random.RandomState(seed)
    x = state.normal(size=(rows, features))
    weights = state.normal(size=(features, 3))
    y = x @ weights + 0.5 * state.normal(size=(rows, 3))
    return x, y


def test_the_ridge_map_recovers_a_planted_linear_relationship() -> None:
    x, y = _planted()
    model = fit_ridge(x, y, 1e-8)
    predicted = predict(model, x)
    assert predicted.shape == y.shape
    residual = float(np.mean((predicted - y) ** 2))
    assert residual < 0.05 * float(np.mean(y**2))


def test_the_ridge_map_standardises_with_the_training_rows_only() -> None:
    x, y = _planted()
    model = fit_ridge(x, y, 10.0)
    assert np.allclose(model.mean, x.mean(axis=0))
    assert np.allclose(model.scale, np.where(x.std(axis=0) > 0, x.std(axis=0), 1.0))


def test_the_ridge_map_refuses_a_single_training_row() -> None:
    with pytest.raises(AnalysisContractError, match="at least two training rows"):
        fit_ridge(np.zeros((1, 3)), np.zeros((1, 2)), 1.0)


def test_a_fold_may_not_put_the_same_entity_on_both_sides() -> None:
    x, y = _planted()
    overlapping = Fold(train=np.array([0, 1, 2]), test=np.array([2, 3]))
    with pytest.raises(AnalysisContractError, match="same entity on both"):
        evaluate("bad", x, y, (overlapping,), ALPHAS, 2, 7)


def test_a_random_split_partitions_the_entities() -> None:
    folds = random_folds(20, 4, 20261021)
    assert len(folds) == 4
    tested = np.concatenate([fold.test for fold in folds])
    assert sorted(tested.tolist()) == list(range(20))
    for fold in folds:
        assert not set(fold.train.tolist()) & set(fold.test.tolist())
        assert len(fold.train) + len(fold.test) == 20


def test_a_random_split_is_reproducible_from_its_seed() -> None:
    first = random_folds(20, 4, 20261021)
    second = random_folds(20, 4, 20261021)
    assert [fold.test.tolist() for fold in first] == [fold.test.tolist() for fold in second]
    other = random_folds(20, 4, 20261022)
    assert [fold.test.tolist() for fold in first] != [fold.test.tolist() for fold in other]


def test_a_batch_blocked_fold_holds_out_one_batch_and_leaves_mixed_rows_out() -> None:
    batches = ("a", "a", "b", "b", None, None)
    folds = batch_blocked_folds(batches, ("a", "b"))
    assert len(folds) == 2
    assert folds[0].test.tolist() == [0, 1]
    assert folds[0].train.tolist() == [2, 3]
    assert folds[1].test.tolist() == [2, 3]
    assert folds[1].train.tolist() == [0, 1]


def test_a_plate_blocked_fold_tests_the_entities_on_the_plate_and_trains_on_the_rest() -> None:
    membership = (frozenset({"p1"}), frozenset({"p2"}), frozenset({"p1", "p2"}))
    folds = plate_blocked_folds(membership, ("p1", "p2"))
    assert folds[0].test.tolist() == [0, 2]
    assert folds[0].train.tolist() == [1]
    assert folds[1].test.tolist() == [1, 2]
    assert folds[1].train.tolist() == [0]


def test_the_size_matched_control_covers_the_same_population_as_the_blocked_evaluation() -> None:
    pool = np.arange(10, dtype=np.int64)
    folds = size_matched_partition_folds(pool, ((6, 4), (4, 6)), 20261021)
    assert len(folds) == 2
    assert folds[0].test.size == 4 and folds[0].train.size == 6
    assert folds[1].test.size == 6 and folds[1].train.size == 4
    tested = np.concatenate([fold.test for fold in folds])
    assert sorted(tested.tolist()) == list(range(10))
    for fold in folds:
        assert not set(fold.train.tolist()) & set(fold.test.tolist())


def test_the_size_matched_control_draws_random_folds_of_the_requested_sizes() -> None:
    pool = np.arange(20, dtype=np.int64)
    folds = size_matched_random_folds(pool, ((15, 5), (15, 5)), 20261021)
    assert [fold.test.size for fold in folds] == [5, 5]
    assert [fold.train.size for fold in folds] == [15, 15]


def test_the_permutation_keeps_the_batches_and_destroys_the_pairing() -> None:
    state = np.random.RandomState(1)
    y = state.normal(size=(20, 4))
    groups = ("a",) * 10 + ("b",) * 10
    permuted = permute_within_group(y, groups, 20261021)
    assert permuted.shape == y.shape
    for index in range(10):
        assert any(
            np.allclose(permuted[index], y[other]) for other in range(10)
        )
    assert not np.allclose(permuted, y)
    for index in range(10, 20):
        assert any(
            np.allclose(permuted[index], y[other]) for other in range(10, 20)
        )


def test_the_permutation_is_reproducible_from_its_seed() -> None:
    state = np.random.RandomState(1)
    y = state.normal(size=(12, 3))
    groups = ("a",) * 6 + ("b",) * 6
    first = permute_within_group(y, groups, 20261021)
    second = permute_within_group(y, groups, 20261021)
    assert np.array_equal(first, second)


def test_the_model_free_concordance_sees_a_planted_structure_and_not_a_permuted_one() -> None:
    state = np.random.RandomState(5)
    signal = state.normal(size=(30, 4))
    directions = state.normal(size=(4, 6))
    x = 3.0 * signal @ directions + 0.05 * state.normal(size=(30, 6))
    y = 3.0 * signal @ directions[:, :5] + 0.05 * state.normal(size=(30, 5))
    planted = neighbourhood_concordance(x, y)
    groups = ("a",) * 15 + ("b",) * 15
    null = neighbourhood_concordance(x, permute_within_group(y, groups, 20261021))
    assert planted > 0.9
    assert abs(null) < 0.3
    assert planted > null


def test_the_variance_decomposition_closes_and_reads_a_pure_group_effect() -> None:
    values = np.array([[0.0, 0.0], [0.0, 0.0], [10.0, 10.0], [10.0, 10.0]])
    groups = ("a", "a", "b", "b")
    shares = variance_shares(values, groups)
    assert shares["between"] + shares["within"] == pytest.approx(1.0)
    assert shares["between"] > 0.9
    mixed = variance_shares(
        np.array([[0.0], [1.0], [2.0], [3.0]]), ("a", "b", "a", "b")
    )
    assert mixed["between"] + mixed["within"] == pytest.approx(1.0)


def test_the_penalty_is_selected_inside_the_training_rows_only() -> None:
    x, y = _planted(rows=60, features=8)
    folds = random_folds(60, 3, 20261021)
    alpha = select_alpha(x[folds[0].train], y[folds[0].train], ALPHAS, 3, 20261021)
    assert alpha in ALPHAS
    with pytest.raises(AnalysisContractError, match="too few training rows"):
        select_alpha(x[:2], y[:2], ALPHAS, 5, 20261021)


def test_an_evaluation_reports_both_agreement_statistics() -> None:
    x, y = _planted(rows=60, features=8)
    folds = random_folds(60, 3, 20261021)
    result = evaluate("planted", x, y, folds, ALPHAS, 3, 20261021)
    assert result.folds == 3
    assert result.tested_perturbations == 60
    assert result.perturbation_r > 0.9
    assert result.feature_r > 0.9
    assert len(result.alphas) == 3
    assert result.train_sizes == (40, 40, 40)
