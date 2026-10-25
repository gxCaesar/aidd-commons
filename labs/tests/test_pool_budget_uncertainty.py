"""Artificial assays only; no ChEMBL cache or locked records are loaded."""

from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.chembl_egfr.data import AssayDataset, normalise_activity_rows
from aidd_commons.pool_budget_campaign import prepare_campaign
from aidd_commons.pool_budget_uncertainty import (
    AcquiredLabelLedger,
    UncertaintyContractError,
    ensemble_variance_order,
    prepare_uncertainty_campaign,
    score_uncertainty_policy,
)


def artificial_assay(assay_id: str = "CHEMBL5736995", prefix: str = "PRIMARY") -> AssayDataset:
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


def test_prepare_uncertainty_campaign_matches_prepare_campaign_on_the_same_dataset():
    dataset = artificial_assay()
    frozen = prepare_campaign(dataset)
    uncertainty = prepare_uncertainty_campaign(dataset)

    assert uncertainty.parent_ids == frozen.library.parent_ids
    assert np.array_equal(uncertainty.features, frozen.library.features)
    assert uncertainty.groups == frozen.library.groups
    assert uncertainty.initial == frozen.plan.initial
    assert uncertainty.pool == frozen.plan.pool
    assert uncertainty.evaluation == frozen.plan.evaluation
    assert uncertainty.checkpoints == frozen.plan.checkpoints


def test_ledger_refuses_a_repeated_or_post_close_acquisition():
    targets = np.array([1.0, 2.0, 3.0, 4.0])
    ledger = AcquiredLabelLedger(targets, initial=(0,))
    assert ledger.current_training_rows() == (0,)
    assert ledger.current_training_labels().tolist() == [1.0]

    ledger.acquire((1,))
    assert ledger.current_training_rows() == (0, 1)

    with pytest.raises(UncertaintyContractError, match="already initial"):
        ledger.acquire((0,))
    with pytest.raises(UncertaintyContractError, match="acquired twice"):
        ledger.acquire((1,))

    ledger.close()
    with pytest.raises(UncertaintyContractError, match="closed"):
        ledger.acquire((2,))


def test_ensemble_variance_order_is_deterministic_complete_and_label_bounded():
    dataset = artificial_assay()
    library = prepare_uncertainty_campaign(dataset)

    def run() -> tuple[tuple[int, ...], tuple]:
        ledger = AcquiredLabelLedger(library.targets, library.initial)
        return ensemble_variance_order(library.features, ledger, library.pool, library.checkpoints)

    picks_a, diagnostics_a = run()
    picks_b, _ = run()

    assert picks_a == picks_b  # deterministic: no RNG anywhere in this path
    assert len(picks_a) == library.checkpoints[-1]
    assert len(set(picks_a)) == len(picks_a)
    assert set(picks_a).issubset(set(library.pool))
    assert not set(picks_a) & set(library.initial)
    assert len(diagnostics_a) == len(library.checkpoints) - 1
    for round_index, diagnostic in enumerate(diagnostics_a, start=1):
        assert diagnostic.round_index == round_index
        assert diagnostic.fold_models >= 2
        assert diagnostic.variance_maximum >= diagnostic.variance_minimum >= 0.0


def test_ensemble_variance_order_rejects_malformed_inputs():
    dataset = artificial_assay()
    library = prepare_uncertainty_campaign(dataset)
    ledger = AcquiredLabelLedger(library.targets, library.initial)

    with pytest.raises(UncertaintyContractError, match="binary matrix"):
        ensemble_variance_order(
            library.features.astype(float) + 0.5, ledger, library.pool, library.checkpoints
        )

    ledger = AcquiredLabelLedger(library.targets, library.initial)
    with pytest.raises(UncertaintyContractError, match="at least one round"):
        ensemble_variance_order(library.features, ledger, library.pool, (5,))


def test_ensemble_variance_order_needs_at_least_two_fold_models():
    dataset = artificial_assay()
    library = prepare_uncertainty_campaign(dataset)
    ledger = AcquiredLabelLedger(library.targets, library.initial)

    with pytest.raises(UncertaintyContractError, match="too few fold models"):
        ensemble_variance_order(
            library.features, ledger, library.pool, library.checkpoints, fold_count=1
        )


def test_score_uncertainty_policy_reports_the_same_shape_as_the_frozen_policies():
    dataset = artificial_assay()
    library = prepare_uncertainty_campaign(dataset)
    ledger = AcquiredLabelLedger(library.targets, library.initial)
    picks, _ = ensemble_variance_order(library.features, ledger, library.pool, library.checkpoints)

    result = score_uncertainty_policy(library, picks)

    assert result["name"] == "ensemble-variance-uncertainty"
    for key in ("recovery", "scaffold_fraction", "evaluation_mae"):
        assert len(result[key]) == len(library.checkpoints)
    assert result["recovery"][0] == 0.0
    assert all(0.0 <= value <= 1.0 for value in result["scaffold_fraction"])
    assert all(value >= 0.0 for value in result["evaluation_mae"])
    assert 0.0 <= result["normalized_auc"] <= 1.0
