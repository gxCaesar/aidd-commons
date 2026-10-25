"""Compute a real trajectory observable and its convergence from committed rMD17 frames.

This module answers a different question from the sibling energy-regression pipeline
in this package: not "can a representation predict the energy of an unseen frame",
but "what does the trajectory say about one physical observable, and how much of it
is needed to estimate that observable to a stated precision". It reads the same two
development NPZ files (`ethanol`, `malonaldehyde`) and touches neither the locked
systems nor the frozen energy-regression contract, split, or selected alphas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Standard atomic weights (IUPAC, conventional values), keyed by nuclear charge. The
# four rMD17 systems (ethanol, malonaldehyde, benzene, uracil) contain only these
# elements; this table is not fitted or approximated from the trajectories.
ATOMIC_MASS_BY_CHARGE: dict[int, float] = {
    1: 1.008,
    6: 12.011,
    7: 14.007,
    8: 15.999,
}


class DynamicsContractError(ValueError):
    """Raised when an input to an observable or convergence computation is invalid."""


def atomic_masses(nuclear_charges: np.ndarray) -> np.ndarray:
    """Map each nuclear charge to its standard atomic mass in atomic mass units."""
    charges = np.asarray(nuclear_charges)
    if charges.ndim != 1:
        raise DynamicsContractError("nuclear_charges must be one-dimensional")
    unknown = sorted({int(z) for z in charges} - set(ATOMIC_MASS_BY_CHARGE))
    if unknown:
        raise DynamicsContractError(
            f"no standard atomic mass declared for nuclear charge(s): {unknown}"
        )
    return np.array([ATOMIC_MASS_BY_CHARGE[int(z)] for z in charges], dtype=np.float64)


def chronological_order(old_indices: np.ndarray) -> np.ndarray:
    """Return the permutation that restores original ab initio trajectory time order.

    rMD17 frames are stored in an order unrelated to simulation time; `old_indices`
    names each frame's position in the original trajectory. A stable ascending sort
    on it is the same convention the sibling energy-regression protocol already uses
    to make its frame selection reproducible, reused here for a different purpose.
    """
    indices = np.asarray(old_indices)
    if indices.ndim != 1:
        raise DynamicsContractError("old_indices must be one-dimensional")
    if np.unique(indices).size != indices.size:
        raise DynamicsContractError("old_indices must be unique")
    return np.argsort(indices, kind="stable")


def radius_of_gyration_series(
    coordinates: np.ndarray, nuclear_charges: np.ndarray, old_indices: np.ndarray
) -> np.ndarray:
    """Mass-weighted radius of gyration for every frame, in chronological trajectory order.

    `Rg(frame) = sqrt(sum_a m_a |r_a - r_com|^2 / sum_a m_a)`, in the coordinate
    array's own length units (Angstrom for rMD17). No frame is dropped or reweighted;
    this is a deterministic function of the committed arrays.
    """
    coords = np.asarray(coordinates, dtype=np.float64)
    if coords.ndim != 3 or coords.shape[2] != 3:
        raise DynamicsContractError("coordinates must have shape (n_frames, n_atoms, 3)")
    masses = atomic_masses(nuclear_charges)
    if masses.shape[0] != coords.shape[1]:
        raise DynamicsContractError(
            "nuclear_charges length must match the atom axis of coordinates"
        )
    order = chronological_order(old_indices)
    coords = coords[order]
    total_mass = float(masses.sum())
    center_of_mass = (coords * masses[None, :, None]).sum(axis=1) / total_mass
    displacement = coords - center_of_mass[:, None, :]
    squared_distance = (displacement**2).sum(axis=2)
    mean_squared_radius = (squared_distance * masses[None, :]).sum(axis=1) / total_mass
    radius: np.ndarray = np.sqrt(mean_squared_radius)
    return radius


@dataclass(frozen=True)
class BlockEstimate:
    blocks: int
    frames_per_block: int
    frames_used: int
    block_mean: float
    block_standard_error: float


def block_standard_error(series: np.ndarray, blocks: int) -> BlockEstimate:
    """Split a chronologically ordered series into equal contiguous blocks and report
    the block-mean standard error, the textbook correction for a correlated time
    series. A trailing remainder shorter than one block is dropped and its size
    reported, never silently padded or redistributed."""
    values = np.asarray(series, dtype=np.float64)
    if values.ndim != 1:
        raise DynamicsContractError("series must be one-dimensional")
    if blocks < 2:
        raise DynamicsContractError("blocks must be at least 2 to estimate a standard error")
    frames_per_block = values.shape[0] // blocks
    if frames_per_block < 1:
        raise DynamicsContractError("fewer frames than requested blocks")
    frames_used = frames_per_block * blocks
    block_means = values[:frames_used].reshape(blocks, frames_per_block).mean(axis=1)
    return BlockEstimate(
        blocks=blocks,
        frames_per_block=frames_per_block,
        frames_used=frames_used,
        block_mean=float(block_means.mean()),
        block_standard_error=float(block_means.std(ddof=1) / np.sqrt(blocks)),
    )


def naive_standard_error(series: np.ndarray) -> float:
    """The standard error under the (here, false) assumption that every frame is an
    independent sample. Reported only as the quantity `block_standard_error` is
    compared against, never as a claimed uncertainty on its own."""
    values = np.asarray(series, dtype=np.float64)
    return float(values.std(ddof=1) / np.sqrt(values.shape[0]))


@dataclass(frozen=True)
class ConvergenceCheckpoint:
    frames_included: int
    cumulative_mean: float
    difference_from_full_trajectory: float


def convergence_checkpoints(
    series: np.ndarray, checkpoints: tuple[int, ...]
) -> tuple[ConvergenceCheckpoint, ...]:
    """Cumulative mean over the first `k` chronologically ordered frames, for each
    declared checkpoint, against the full-trajectory mean. Checkpoints are read in
    the order given; each must be a positive integer no larger than the series."""
    values = np.asarray(series, dtype=np.float64)
    full_mean = float(values.mean())
    results = []
    for k in checkpoints:
        if k < 1 or k > values.shape[0]:
            raise DynamicsContractError(f"checkpoint {k} must be between 1 and {values.shape[0]}")
        cumulative_mean = float(values[:k].mean())
        results.append(
            ConvergenceCheckpoint(
                frames_included=k,
                cumulative_mean=cumulative_mean,
                difference_from_full_trajectory=cumulative_mean - full_mean,
            )
        )
    return tuple(results)
