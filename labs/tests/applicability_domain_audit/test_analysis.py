"""Distance and error grouping checks on constructed molecules."""

import numpy as np
import pytest
from aidd_commons.applicability_domain_audit.analysis import (
    AuditError,
    error_halves,
    nearest_training,
    property_matrix,
    scaled_pair_distances,
)
from aidd_commons.freesolv.data import MoleculeRecord


def molecule(smiles: str) -> MoleculeRecord:
    return MoleculeRecord(smiles, smiles, smiles, 0.0)


def test_constructed_molecules_use_train_scaled_mean_property_distance() -> None:
    train = property_matrix([molecule("C"), molecule("CC"), molecule("O")])
    test = property_matrix([molecule("CO"), molecule("CCO")])
    observed = scaled_pair_distances(train, test)
    scale = np.std(train, axis=0, ddof=0)
    scale[scale == 0] = 1.0
    first_to_each = [np.mean(np.abs(test[0] - row) / scale) for row in train]
    np.testing.assert_allclose(observed[0], first_to_each)
    indices, distances = nearest_training(observed)
    assert indices[0] == int(np.argmin(first_to_each))
    assert distances[0] == pytest.approx(min(first_to_each))
    assert observed.shape == (2, 3)


def test_two_distance_halves_are_ranked_before_errors() -> None:
    distances = np.asarray([0.4, 0.1, 0.3, 0.2])
    errors = np.asarray([4.0, 1.0, 3.0, 2.0])
    halves = error_halves(distances, errors, ["d", "a", "c", "b"])
    assert halves == {
        "smaller_distance": {"count": 2, "median_absolute_error_kcal_mol": 1.5},
        "larger_distance": {"count": 2, "median_absolute_error_kcal_mol": 3.5},
    }


def test_a_test_molecule_without_a_training_neighbour_is_refused() -> None:
    with pytest.raises(AuditError, match="training neighbour"):
        nearest_training(np.empty((1, 0)))
    with pytest.raises(AuditError, match="nonempty finite"):
        scaled_pair_distances(np.empty((0, 5)), np.zeros((1, 5)))
