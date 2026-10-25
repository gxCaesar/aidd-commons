from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import RMD17SystemData
from .protocol import (
    EVALUATION_FRAME_COUNT,
    SAMPLED_FRAME_COUNT,
    TRAIN_FRAME_COUNT,
    VALIDATION_FRAME_COUNT,
)


class SplitContractError(ValueError):
    """Raised when deterministic rMD17 sampling cannot satisfy the protocol."""


@dataclass(frozen=True)
class FramePartition:
    coordinates: np.ndarray
    energies: np.ndarray
    old_indices: np.ndarray
    source_positions: np.ndarray


@dataclass(frozen=True)
class SystemSplit:
    train: FramePartition
    validation: FramePartition
    evaluation: FramePartition


def selected_ranks(n_frames: int) -> np.ndarray:
    if n_frames < SAMPLED_FRAME_COUNT:
        raise SplitContractError(f"rMD17 sampling requires at least {SAMPLED_FRAME_COUNT} frames")
    ranks = np.rint(np.linspace(0, n_frames - 1, SAMPLED_FRAME_COUNT)).astype(np.int64)
    if ranks.shape != (SAMPLED_FRAME_COUNT,) or np.unique(ranks).size != SAMPLED_FRAME_COUNT:
        raise SplitContractError("sampling produced duplicate selected ranks")
    return ranks


def partition_system(system: RMD17SystemData) -> SystemSplit:
    positions = np.argsort(system.old_indices, kind="stable")
    selected_positions = positions[selected_ranks(system.frame_count)]
    if selected_positions.shape != (SAMPLED_FRAME_COUNT,):
        raise SplitContractError("sampling did not produce exactly 1000 selected rows")
    if not np.all(np.diff(system.old_indices[selected_positions]) > 0):
        raise SplitContractError("selected rows are not strictly ordered by old_indices")

    return SystemSplit(
        train=_partition(system, selected_positions[:TRAIN_FRAME_COUNT]),
        validation=_partition(
            system,
            selected_positions[TRAIN_FRAME_COUNT : TRAIN_FRAME_COUNT + VALIDATION_FRAME_COUNT],
        ),
        evaluation=_partition(
            system,
            selected_positions[
                TRAIN_FRAME_COUNT + VALIDATION_FRAME_COUNT : TRAIN_FRAME_COUNT
                + VALIDATION_FRAME_COUNT
                + EVALUATION_FRAME_COUNT
            ],
        ),
    )


def _partition(system: RMD17SystemData, positions: np.ndarray) -> FramePartition:
    return FramePartition(
        coordinates=system.coordinates[positions],
        energies=system.energies[positions],
        old_indices=system.old_indices[positions],
        source_positions=positions,
    )
