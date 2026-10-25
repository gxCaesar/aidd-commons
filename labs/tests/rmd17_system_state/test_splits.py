from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from aidd_commons.rmd17_system_state.data import load_system_npz
from aidd_commons.rmd17_system_state.protocol import SYSTEMS
from aidd_commons.rmd17_system_state.splits import (
    SplitContractError,
    partition_system,
    selected_ranks,
)


def test_selected_ranks_match_literal_rint_linspace_contract() -> None:
    expected = np.rint(np.linspace(0, 99_999, 1_000)).astype(np.int64)
    actual = selected_ranks(100_000)

    assert np.array_equal(actual, expected)
    assert len(actual) == 1_000
    assert len(np.unique(actual)) == 1_000


def test_partition_stably_sorts_old_indices_and_splits_exact_counts(
    valid_ethanol_npz: Path,
) -> None:
    system = load_system_npz(valid_ethanol_npz, SYSTEMS["ethanol"])
    split = partition_system(system)

    expected_positions = np.argsort(system.old_indices, kind="stable")[selected_ranks(100_000)]
    actual_positions = np.concatenate(
        [
            split.train.source_positions,
            split.validation.source_positions,
            split.evaluation.source_positions,
        ]
    )
    actual_indices = np.concatenate(
        [split.train.old_indices, split.validation.old_indices, split.evaluation.old_indices]
    )
    assert np.array_equal(actual_positions, expected_positions)
    assert np.array_equal(actual_indices, np.sort(actual_indices))
    assert split.train.coordinates.shape[0] == 600
    assert split.validation.coordinates.shape[0] == 200
    assert split.evaluation.coordinates.shape[0] == 200


def test_selected_ranks_rejects_fewer_than_one_thousand_frames() -> None:
    with pytest.raises(SplitContractError, match="at least 1000"):
        selected_ranks(999)
