import json
from pathlib import Path

import numpy as np
import pytest
from aidd_commons.pool_budget import (
    budget_checkpoints,
    campaign_summary,
    group_partition,
    maxmin_order,
    recovery_curve,
    synthetic_library,
)


def test_budget_uses_original_pool_and_reports_rounding():
    assert budget_checkpoints(42) == (0, 2, 4, 6, 8)
    assert budget_checkpoints(631) == (0, 31, 62, 93, 124)
    for invalid in (0, 19, -1):
        with pytest.raises(ValueError):
            budget_checkpoints(invalid)


def test_maxmin_literal_tanimoto_and_ties():
    features = np.array([[1, 0, 0], [1, 1, 0], [0, 0, 1], [0, 1, 0]])
    # Initial row 0; rows 2 and 3 both distance 1: choose row 2 by stable order.
    assert maxmin_order(features, (0,), (1, 2, 3), 3) == (2, 3, 1)
    with pytest.raises(ValueError):
        maxmin_order(features, (0,), (0, 1), 1)
    with pytest.raises(ValueError):
        maxmin_order(features, (0,), (1,), 2)


def test_scaffold_groups_never_cross_partitions():
    groups = tuple(["ring-a"] * 10 + ["ring-b"] * 10 + [f"g{i}" for i in range(40)])
    parts = group_partition(groups)
    assert sorted(i for part in parts for i in part) == list(range(60))
    group_sets = [{groups[i] for i in part} for part in parts]
    assert all(group_sets[i].isdisjoint(group_sets[j]) for i, j in ((0, 1), (0, 2), (1, 2)))
    assert tuple(map(len, parts)) == (6, 42, 12)
    with pytest.raises(ValueError):
        group_partition(("one",) * 60)


def test_recovery_auc_is_hand_computable_and_rejects_invalid_orders():
    # Top decile has exactly two of twenty entries. Ties favor smaller row index.
    labels = np.array([9.0, 9.0] + [0.0] * 18)
    recovery, auc = recovery_curve(labels, (0, 2, 1, 3), (0, 1, 2, 3, 4))
    assert recovery == (0.0, 0.5, 0.5, 1.0, 1.0)
    assert auc == pytest.approx(0.625)
    with pytest.raises(ValueError):
        recovery_curve(labels, (0, 0), (0, 1, 2))
    with pytest.raises(ValueError):
        recovery_curve(labels, (0, 1), (0, 2, 1))


def test_demo_is_deterministic_aggregate_only_and_keeps_evaluation_outside_selection():
    features, groups, labels = synthetic_library()
    initial, pool, evaluation = group_partition(groups)
    count = budget_checkpoints(len(pool))[-1]
    picks = maxmin_order(features, initial, pool, count)
    # Selector has no label argument and excluded evaluation rows are never candidates.
    assert set(picks).isdisjoint(evaluation)
    assert maxmin_order(features, initial, pool, count) == picks
    first = campaign_summary()
    assert first == campaign_summary()
    assert first["data_kind"] == "synthetic-teaching-example"
    assert first["real_campaign"] == "not_run"
    assert len(first["random_runs"]) == 5
    assert len(labels) == 60
    assert not {"smiles", "ids", "membership", "predictions"}.intersection(first)


def test_delivered_summary_matches_execution():
    path = Path(__file__).parents[1] / "pool_budget" / "demo-summary.json"
    assert json.loads(path.read_text()) == campaign_summary()


def test_labels_change_scoring_not_label_blind_selection():
    features = np.eye(21, dtype=int)
    picks = maxmin_order(features, (20,), tuple(range(20)), 4)
    assert picks == (0, 1, 2, 3)
    labels = np.arange(20, dtype=float)
    original = recovery_curve(labels, picks, (0, 1, 2, 3, 4))
    permuted = recovery_curve(labels[::-1], picks, (0, 1, 2, 3, 4))
    assert original != permuted
    assert maxmin_order(features, (20,), tuple(range(20)), 4) == picks


@pytest.mark.parametrize("features", [np.array([[float("nan")]]), np.array([[2]])])
def test_selector_rejects_nonbinary_features(features):
    with pytest.raises(ValueError):
        maxmin_order(features, (0,), (), 0)
