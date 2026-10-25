from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

ArrayPayload = dict[str, np.ndarray]


@pytest.fixture
def make_arrays() -> Callable[[int, int], ArrayPayload]:
    def build(n_frames: int = 100_000, n_atoms: int = 9) -> ArrayPayload:
        charges = np.ones(n_atoms, dtype=np.int64)
        charges[: min(3, n_atoms)] = np.array([6, 6, 8], dtype=np.int64)[: min(3, n_atoms)]
        coordinates = np.zeros((n_frames, n_atoms, 3), dtype=np.float32)
        coordinates[:, :, 0] = np.arange(n_atoms, dtype=np.float32) * 1.25
        if n_atoms > 1:
            coordinates[0, 1, 0] = 2.0
        energies = np.linspace(-3.0, 3.0, n_frames, dtype=np.float64)
        forces = np.zeros_like(coordinates)
        old_indices = np.arange(n_frames - 1, -1, -1, dtype=np.int64)
        return {
            "nuclear_charges": charges,
            "coords": coordinates,
            "energies": energies,
            "forces": forces,
            "old_indices": old_indices,
            "old_energies": energies + 0.25,
            "old_forces": forces + 0.5,
        }

    return build


@pytest.fixture
def write_npz(tmp_path: Path) -> Callable[[str, ArrayPayload], Path]:
    def write(filename: str, arrays: ArrayPayload) -> Path:
        path = tmp_path / filename
        np.savez(path, **arrays)
        return path

    return write


@pytest.fixture(scope="session")
def valid_ethanol_npz(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("rmd17-authored")
    path = directory / "rmd17_ethanol.npz"
    n_frames = 100_000
    n_atoms = 9
    charges = np.array([6, 6, 8, 1, 1, 1, 1, 1, 1], dtype=np.int64)
    coordinates = np.zeros((n_frames, n_atoms, 3), dtype=np.float32)
    coordinates[:, :, 0] = np.arange(n_atoms, dtype=np.float32) * 1.25
    coordinates[0, 1, 0] = 2.0
    energies = np.linspace(-3.0, 3.0, n_frames, dtype=np.float64)
    forces = np.zeros_like(coordinates)
    old_indices = np.arange(n_frames - 1, -1, -1, dtype=np.int64)
    np.savez(
        path,
        nuclear_charges=charges,
        coords=coordinates,
        energies=energies,
        forces=forces,
        old_indices=old_indices,
        old_energies=energies + 0.25,
        old_forces=forces + 0.5,
    )
    return path
