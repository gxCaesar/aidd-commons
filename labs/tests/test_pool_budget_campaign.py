"""Artificial assays only; no ChEMBL cache or locked records are loaded."""

from dataclasses import replace

import numpy as np
import pytest
from aidd_commons.chembl_egfr.data import AssayDataset, normalise_activity_rows
from aidd_commons.pool_budget_campaign import (
    CampaignContractError,
    fit_checkpoint,
    freeze_predictions,
    prepare_campaign,
    score_campaign,
)


def artificial_assay(assay_id="CHEMBL5736995", prefix="PRIMARY") -> AssayDataset:
    smiles = [
        "C" * length + suffix
        for length in range(1, 11)
        for suffix in ("O", "N", "F", "C(=O)O", "c1ccccc1", "C1CCCCC1")
    ]
    rows = []
    for index, value in enumerate(smiles):
        target = 5.0 + ((index * 17) % 61) / 20
        parent = f"{prefix}_{index:03d}"
        rows.append(
            {
                "activity_id": index + 1,
                "assay_chembl_id": assay_id,
                "canonical_smiles": value,
                "data_validity_comment": None,
                "molecule_chembl_id": parent,
                "parent_molecule_chembl_id": parent,
                "pchembl_value": target,
                "potential_duplicate": 0,
                "standard_flag": 1,
                "standard_relation": "=",
                "standard_type": "IC50",
                "standard_units": "nM",
                "standard_value": 10 ** (9 - target),
            }
        )
    return normalise_activity_rows(rows, assay_id)


def test_plan_is_label_free_sorted_and_equal_budget_for_every_policy():
    source = artificial_assay()
    prepared = prepare_campaign(source)
    reordered = prepare_campaign(replace(source, records=source.records[::-1]))
    assert prepared.plan == reordered.plan
    assert prepared.library.parent_ids == tuple(sorted(prepared.library.parent_ids))
    assert not hasattr(prepared.library, "labels")
    assert tuple(
        map(len, (prepared.plan.initial, prepared.plan.pool, prepared.plan.evaluation))
    ) == (6, 42, 12)
    assert prepared.plan.checkpoints == (0, 2, 4, 6, 8)
    assert tuple(policy.name for policy in prepared.plan.policies) == (
        "maxmin",
        "random-0",
        "random-1",
        "random-2",
        "random-3",
        "random-4",
    )
    for policy in prepared.plan.policies:
        assert len(policy.picks) == len(set(policy.picks)) == 8
        assert set(policy.picks).issubset(prepared.plan.pool)
        assert set(policy.picks).isdisjoint(prepared.plan.evaluation)


def test_scoring_labels_are_inaccessible_until_every_prediction_is_frozen():
    prepared = prepare_campaign(artificial_assay())
    with pytest.raises(CampaignContractError, match="frozen"):
        prepared.oracle.evaluation_targets()
    with pytest.raises(CampaignContractError, match="frozen"):
        prepared.oracle.pool_targets()
    frozen = freeze_predictions(prepared)
    assert len(frozen.values) == 6
    assert all(len(checkpoints) == 5 for checkpoints in frozen.values)
    assert all(len(vector) == 12 for checkpoints in frozen.values for vector in checkpoints)
    assert len(prepared.oracle.evaluation_targets()) == 12
    for policy, checkpoints in zip(prepared.plan.policies, frozen.fit_rows, strict=True):
        for acquired_count, rows in zip(prepared.plan.checkpoints, checkpoints, strict=True):
            assert rows == tuple(sorted(prepared.plan.initial + policy.picks[:acquired_count]))
            assert set(rows).isdisjoint(prepared.plan.evaluation)


def test_only_evaluation_label_changes_cannot_change_picks_or_predictions():
    source = artificial_assay()
    original = prepare_campaign(source)
    evaluation_ids = {original.library.parent_ids[i] for i in original.plan.evaluation}
    changed = replace(
        source,
        records=tuple(
            replace(record, target_pchembl=record.target_pchembl + 20)
            if record.parent_molecule_chembl_id in evaluation_ids
            else record
            for record in source.records
        ),
    )
    other = prepare_campaign(changed)
    left = freeze_predictions(original)
    right = freeze_predictions(other)
    assert original.plan == other.plan
    assert left.values == right.values
    left_scores = score_campaign(original, left)
    right_scores = score_campaign(other, right)
    assert left_scores["policies"][0]["recovery"] == right_scores["policies"][0]["recovery"]
    assert (
        left_scores["policies"][0]["evaluation_mae"]
        != right_scores["policies"][0]["evaluation_mae"]
    )


def test_fixed_ridge_intercept_has_a_hand_computable_zero_feature_oracle():
    features = np.zeros((4, 2))
    assert fit_checkpoint(features, (0, 1), np.array([2.0, 4.0]), (2, 3)) == pytest.approx(
        (3.0, 3.0)
    )
    with pytest.raises(CampaignContractError):
        fit_checkpoint(features, (0, 1), np.array([2.0, 4.0]), (1, 3))
    with pytest.raises(CampaignContractError):
        fit_checkpoint(features, (0, 1), np.array([2.0, float("nan")]), (2, 3))


def test_malformed_or_cross_campaign_predictions_cannot_be_scored():
    prepared = prepare_campaign(artificial_assay())
    frozen = freeze_predictions(prepared)
    with pytest.raises(CampaignContractError):
        score_campaign(prepared, replace(frozen, values=frozen.values[:-1]))
    other = prepare_campaign(artificial_assay(prefix="OTHER"))
    with pytest.raises(CampaignContractError):
        score_campaign(other, frozen)


def test_invalid_entity_or_target_is_not_silently_dropped():
    source = artificial_assay()
    duplicate = replace(source, records=source.records + (source.records[0],))
    with pytest.raises(CampaignContractError):
        prepare_campaign(duplicate)
    invalid = replace(
        source,
        records=(replace(source.records[0], target_pchembl=float("nan")),) + source.records[1:],
    )
    with pytest.raises(CampaignContractError):
        prepare_campaign(invalid)
