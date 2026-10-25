from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from aidd_commons.rmd17_system_state.data import DataContractError, load_system_npz
from aidd_commons.rmd17_system_state.protocol import SYSTEMS


def test_loader_validates_and_discards_forces_and_old_labels(valid_ethanol_npz: Path) -> None:
    system = load_system_npz(valid_ethanol_npz, SYSTEMS["ethanol"])

    assert system.system_id == "ethanol"
    assert system.coordinates.shape == (100_000, 9, 3)
    assert system.energies.shape == (100_000,)
    assert system.old_indices[0] == 99_999
    assert not hasattr(system, "forces")
    assert not hasattr(system, "old_energies")
    assert not hasattr(system, "old_forces")


def test_loader_rejects_missing_required_array(make_arrays, write_npz) -> None:
    arrays = make_arrays()
    del arrays["forces"]

    with pytest.raises(DataContractError, match="forces"):
        load_system_npz(write_npz("rmd17_ethanol.npz", arrays), SYSTEMS["ethanol"])


@pytest.mark.parametrize("mutation", ["duplicate", "fractional"])
def test_loader_rejects_duplicate_or_non_integer_old_indices(
    make_arrays, write_npz, mutation: str
) -> None:
    arrays = make_arrays()
    if mutation == "duplicate":
        arrays["old_indices"][1] = arrays["old_indices"][0]
    else:
        arrays["old_indices"] = arrays["old_indices"].astype(float)

    with pytest.raises(DataContractError, match="old_indices"):
        load_system_npz(write_npz("rmd17_ethanol.npz", arrays), SYSTEMS["ethanol"])


def test_loader_rejects_wrong_atom_count(make_arrays, write_npz) -> None:
    arrays = make_arrays(n_atoms=8)

    with pytest.raises(DataContractError, match="atom count"):
        load_system_npz(write_npz("rmd17_ethanol.npz", arrays), SYSTEMS["ethanol"])


def test_loader_rejects_shape_mismatch_and_short_trajectory(make_arrays, write_npz) -> None:
    arrays = make_arrays()
    arrays["forces"] = arrays["forces"][:, :-1, :]
    with pytest.raises(DataContractError, match="forces"):
        load_system_npz(write_npz("rmd17_ethanol.npz", arrays), SYSTEMS["ethanol"])

    short_arrays = make_arrays(n_frames=999)
    with pytest.raises(DataContractError, match="100000"):
        load_system_npz(write_npz("rmd17_ethanol.npz", short_arrays), SYSTEMS["ethanol"])


def test_loader_rejects_nonfinite_coordinate_and_energy_shape_mismatch(
    make_arrays, write_npz
) -> None:
    arrays = make_arrays()
    arrays["coords"][0, 0, 0] = np.nan
    with pytest.raises(DataContractError, match="coords"):
        load_system_npz(write_npz("rmd17_ethanol.npz", arrays), SYSTEMS["ethanol"])

    malformed = make_arrays()
    malformed["energies"] = malformed["energies"][:, None]
    with pytest.raises(DataContractError, match="energies"):
        load_system_npz(write_npz("rmd17_ethanol.npz", malformed), SYSTEMS["ethanol"])


def test_loader_accepts_integer_coordinates_but_rejects_nonreal_coordinates(
    make_arrays, write_npz
) -> None:
    integer_arrays = make_arrays()
    integer_coordinates = integer_arrays["coords"].astype(np.int64)
    integer_coordinates[0, 0, 0] = np.iinfo(np.int64).max
    integer_coordinates[0, 1, 0] = np.iinfo(np.int64).min
    integer_arrays["coords"] = integer_coordinates

    loaded = load_system_npz(
        write_npz("rmd17_ethanol.npz", integer_arrays),
        SYSTEMS["ethanol"],
    )

    assert loaded.coordinates.dtype == np.dtype(np.int64)

    nonreal_arrays = make_arrays()
    nonreal_arrays["coords"] = nonreal_arrays["coords"].astype(np.complex128)

    with pytest.raises(DataContractError, match="real"):
        load_system_npz(
            write_npz("rmd17_ethanol.npz", nonreal_arrays),
            SYSTEMS["ethanol"],
        )


def test_loader_requires_expected_filename_and_charge_vector(make_arrays, write_npz) -> None:
    arrays = make_arrays()
    arrays["nuclear_charges"] = arrays["nuclear_charges"][:, None]
    with pytest.raises(DataContractError, match="nuclear_charges"):
        load_system_npz(write_npz("rmd17_ethanol.npz", arrays), SYSTEMS["ethanol"])

    valid_arrays = make_arrays()
    alternate = replace(SYSTEMS["ethanol"], filename="required-name.npz")
    with pytest.raises(DataContractError, match="filename"):
        load_system_npz(write_npz("rmd17_ethanol.npz", valid_arrays), alternate)
