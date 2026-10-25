from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.rmd17_system_state.features import (
    FeatureContractError,
    build_pair_distance_features,
)


def test_pair_distance_features_use_sorted_element_channels_and_fixed_pair_normalisation() -> None:
    charges = np.array([1, 8, 1], dtype=np.int64)
    coordinates = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 0.0]]])

    features = build_pair_distance_features(charges, coordinates)

    assert features.channels == ((1, 1), (1, 8))
    assert features.values.shape == (1, 202)
    assert np.sum(features.values[0, :101]) == pytest.approx(1.0)
    assert np.sum(features.values[0, 101:]) == pytest.approx(1.0)
    assert features.values[0, 20] == pytest.approx(1.0)
    assert features.values[0, 101 + 10] == pytest.approx(0.5)
    assert features.values[0, 101 + 22] == pytest.approx(0.5)


def test_pair_distance_features_are_invariant_to_atom_permutation_translation_and_rotation() -> (
    None
):
    charges = np.array([1, 8, 1], dtype=np.int64)
    coordinates = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 0.0]]])
    reference = build_pair_distance_features(charges, coordinates)

    permutation = np.array([2, 0, 1])
    permuted = build_pair_distance_features(charges[permutation], coordinates[:, permutation, :])
    rotation = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    transformed_coordinates = coordinates @ rotation + np.array([5.0, -3.0, 2.0])
    transformed = build_pair_distance_features(charges, transformed_coordinates)

    assert np.array_equal(permuted.values, reference.values)
    assert np.array_equal(transformed.values, reference.values)


def test_pair_distance_features_put_distances_over_ten_angstrom_in_explicit_overflow_bin() -> None:
    features = build_pair_distance_features(
        np.array([1, 1], dtype=np.int64),
        np.array([[[0.0, 0.0, 0.0], [10.1, 0.0, 0.0]]]),
    )

    assert features.values.shape == (1, 101)
    assert features.values[0, -1] == pytest.approx(1.0)
    assert np.sum(features.values[0, :-1]) == pytest.approx(0.0)


def test_pair_distance_features_promote_extreme_int64_coordinates_before_subtraction() -> None:
    maximum = np.iinfo(np.int64).max
    coordinates = np.array(
        [[[maximum, 0, 0], [-maximum, 0, 0]]],
        dtype=np.int64,
    )

    features = build_pair_distance_features(
        np.array([1, 1], dtype=np.int64),
        coordinates,
    )

    assert features.values.shape == (1, 101)
    assert features.values[0, -1] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "coordinates",
    [
        np.array([[[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]]),
        np.array([[[0.0, 0.0, 0.0], [np.nan, 0.0, 0.0]]]),
    ],
)
def test_pair_distance_features_reject_nonpositive_or_nonfinite_distances(
    coordinates: np.ndarray,
) -> None:
    with pytest.raises(FeatureContractError, match="distance"):
        build_pair_distance_features(np.array([1, 1], dtype=np.int64), coordinates)
