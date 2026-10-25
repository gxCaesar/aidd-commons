from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .protocol import EXPECTED_FRAME_COUNT, REQUIRED_NPZ_KEYS, SystemSpec


class DataContractError(ValueError):
    """Raised when an rMD17 NPZ file violates the frozen source contract."""


@dataclass(frozen=True)
class RMD17SystemData:
    system_id: str
    nuclear_charges: np.ndarray
    coordinates: np.ndarray
    energies: np.ndarray
    old_indices: np.ndarray

    @property
    def frame_count(self) -> int:
        return int(self.coordinates.shape[0])


def load_system_npz(path: Path, specification: SystemSpec) -> RMD17SystemData:
    if path.name != specification.filename:
        raise DataContractError(f"filename must be {specification.filename}, received {path.name}")
    try:
        with np.load(path, allow_pickle=False) as archive:
            missing = [name for name in REQUIRED_NPZ_KEYS if name not in archive.files]
            if missing:
                raise DataContractError(f"missing required arrays: {', '.join(missing)}")
            arrays = {name: np.asarray(archive[name]) for name in REQUIRED_NPZ_KEYS}
    except DataContractError:
        raise
    except (OSError, ValueError) as error:
        raise DataContractError(f"could not load NPZ file: {error}") from error

    charges = arrays["nuclear_charges"]
    coordinates = arrays["coords"]
    energies = arrays["energies"]
    forces = arrays["forces"]
    old_indices = arrays["old_indices"]
    old_energies = arrays["old_energies"]
    old_forces = arrays["old_forces"]

    _validate_charges(charges, specification)
    _validate_coordinates(coordinates, charges)
    n_frames = int(coordinates.shape[0])
    if n_frames != EXPECTED_FRAME_COUNT:
        raise DataContractError(
            f"coords must contain exactly {EXPECTED_FRAME_COUNT} frames, found {n_frames}"
        )
    _validate_vector("energies", energies, n_frames)
    _validate_coordinate_array("forces", forces, coordinates.shape)
    _validate_old_indices(old_indices, n_frames)
    _validate_vector("old_energies", old_energies, n_frames)
    _validate_coordinate_array("old_forces", old_forces, coordinates.shape)

    return RMD17SystemData(
        system_id=specification.system_id,
        nuclear_charges=charges,
        coordinates=coordinates,
        energies=energies,
        old_indices=old_indices,
    )


def _validate_charges(charges: np.ndarray, specification: SystemSpec) -> None:
    if charges.ndim != 1 or not np.issubdtype(charges.dtype, np.integer):
        raise DataContractError("nuclear_charges must be a one-dimensional integer vector")
    if int(charges.shape[0]) != specification.expected_atoms:
        raise DataContractError(
            f"nuclear_charges atom count must be {specification.expected_atoms}, "
            f"found {charges.shape[0]}"
        )
    if not np.all(charges > 0):
        raise DataContractError("nuclear_charges must be positive")


def _validate_coordinates(coordinates: np.ndarray, charges: np.ndarray) -> None:
    if (
        coordinates.ndim != 3
        or coordinates.shape[1] != charges.shape[0]
        or coordinates.shape[2] != 3
    ):
        raise DataContractError("coords must have shape (n_frames, n_atoms, 3)")
    _require_real_numeric("coords", coordinates)
    _require_finite("coords", coordinates)


def _validate_vector(name: str, values: np.ndarray, n_frames: int) -> None:
    if values.ndim != 1 or values.shape[0] != n_frames:
        raise DataContractError(f"{name} must have shape ({n_frames},)")
    _require_real_numeric(name, values)
    _require_finite(name, values)


def _validate_coordinate_array(name: str, values: np.ndarray, shape: tuple[int, ...]) -> None:
    if values.shape != shape:
        raise DataContractError(f"{name} must match coords shape {shape}")
    _require_real_numeric(name, values)
    _require_finite(name, values)


def _validate_old_indices(old_indices: np.ndarray, n_frames: int) -> None:
    if (
        old_indices.ndim != 1
        or old_indices.shape[0] != n_frames
        or not np.issubdtype(old_indices.dtype, np.integer)
    ):
        raise DataContractError(
            f"old_indices must be a one-dimensional integer vector with {n_frames} entries"
        )
    if np.any(old_indices < 0) or np.unique(old_indices).size != n_frames:
        raise DataContractError("old_indices must be unique and non-negative")


def _require_real_numeric(name: str, values: np.ndarray) -> None:
    if not (
        np.issubdtype(values.dtype, np.integer) or np.issubdtype(values.dtype, np.floating)
    ):
        raise DataContractError(f"{name} must use a real integer or floating dtype")


def _require_finite(name: str, values: np.ndarray) -> None:
    try:
        finite = np.isfinite(values)
    except TypeError as error:
        raise DataContractError(f"{name} must contain numeric finite values") from error
    if not bool(np.all(finite)):
        raise DataContractError(f"{name} must contain only finite values")
