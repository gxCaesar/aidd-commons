from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .protocol import DISTANCE_EDGES, DISTANCE_MAXIMUM

DISTANCE_BIN_COUNT = len(DISTANCE_EDGES) - 1
OVERFLOW_BIN_INDEX = DISTANCE_BIN_COUNT


class FeatureContractError(ValueError):
    """Raised when pair-distance features would violate the frozen feature contract."""


@dataclass(frozen=True)
class PairDistanceFeatures:
    values: np.ndarray
    channels: tuple[tuple[int, int], ...]
    names: tuple[str, ...]


def build_pair_distance_features(
    nuclear_charges: np.ndarray, coordinates: np.ndarray
) -> PairDistanceFeatures:
    _validate_inputs(nuclear_charges, coordinates)
    safe_coordinates = _as_safe_float64(coordinates)
    channels_to_pairs = _channels_to_pairs(nuclear_charges)
    channels = tuple(sorted(channels_to_pairs))
    row_count = int(safe_coordinates.shape[0])
    blocks: list[np.ndarray] = []
    names: list[str] = []

    for channel in channels:
        pairs = channels_to_pairs[channel]
        histogram = np.zeros((row_count, DISTANCE_BIN_COUNT + 1), dtype=float)
        row_positions = np.arange(row_count)
        for left, right in pairs:
            distances = np.linalg.norm(
                safe_coordinates[:, left, :] - safe_coordinates[:, right, :], axis=1
            )
            if not bool(np.all(np.isfinite(distances))) or bool(np.any(distances <= 0.0)):
                raise FeatureContractError("pair distance must be finite and strictly positive")
            bins = _distance_bins(distances)
            histogram[row_positions, bins] += 1.0
        histogram /= float(len(pairs))
        blocks.append(histogram)
        names.extend(_channel_names(channel))

    if not blocks:
        raise FeatureContractError("at least two atoms are required for pair-distance features")
    return PairDistanceFeatures(
        values=np.concatenate(blocks, axis=1),
        channels=channels,
        names=tuple(names),
    )


def _validate_inputs(nuclear_charges: np.ndarray, coordinates: np.ndarray) -> None:
    if nuclear_charges.ndim != 1 or not np.issubdtype(nuclear_charges.dtype, np.integer):
        raise FeatureContractError("nuclear_charges must be a one-dimensional integer vector")
    if not bool(np.all(nuclear_charges > 0)):
        raise FeatureContractError("nuclear_charges must be positive")
    if (
        coordinates.ndim != 3
        or coordinates.shape[1] != nuclear_charges.shape[0]
        or coordinates.shape[2] != 3
    ):
        raise FeatureContractError("coordinates must have shape (n_frames, n_atoms, 3)")
    if not _is_real_numeric_dtype(coordinates.dtype):
        raise FeatureContractError("coordinates must use a real integer or floating dtype")
    if not bool(np.all(np.isfinite(coordinates))):
        raise FeatureContractError("coordinates must be finite for pair-distance features")


def _as_safe_float64(values: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore", invalid="ignore"):
        converted = np.asarray(values, dtype=np.float64)
    if not bool(np.all(np.isfinite(converted))):
        raise FeatureContractError("coordinates must be representable as finite float64 values")
    return converted


def _is_real_numeric_dtype(dtype: np.dtype[np.generic]) -> bool:
    return np.issubdtype(dtype, np.integer) or np.issubdtype(dtype, np.floating)


def _channels_to_pairs(charges: np.ndarray) -> dict[tuple[int, int], list[tuple[int, int]]]:
    result: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for left in range(charges.shape[0]):
        for right in range(left + 1, charges.shape[0]):
            channel = (
                int(min(charges[left], charges[right])),
                int(max(charges[left], charges[right])),
            )
            result.setdefault(channel, []).append((left, right))
    return result


def _distance_bins(distances: np.ndarray) -> np.ndarray:
    bins = np.full(distances.shape, OVERFLOW_BIN_INDEX, dtype=np.int64)
    in_range = distances <= DISTANCE_MAXIMUM
    bins[in_range] = np.minimum(
        np.searchsorted(np.asarray(DISTANCE_EDGES), distances[in_range], side="right") - 1,
        DISTANCE_BIN_COUNT - 1,
    )
    return bins


def _channel_names(channel: tuple[int, int]) -> tuple[str, ...]:
    prefix = f"Z{channel[0]}-Z{channel[1]}"
    bins = tuple(f"{prefix}:bin-{index:03d}" for index in range(DISTANCE_BIN_COUNT))
    return (*bins, f"{prefix}:overflow-over-10.0")
