"""Unit and CLI tests for the rMD17 observable-and-convergence extension.

Uses only the synthetic fixtures already defined for this lab (`make_arrays`,
`write_npz`); no real rMD17 download is needed to run these tests.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from aidd_commons.rmd17_system_state.dynamics import (
    DynamicsContractError,
    atomic_masses,
    block_standard_error,
    chronological_order,
    convergence_checkpoints,
    naive_standard_error,
    radius_of_gyration_series,
)

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/rmd17_system_state"

_spec = importlib.util.spec_from_file_location(
    "rmd17_inspect_dynamics", LAB / "inspect_dynamics.py"
)
inspect_dynamics = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(inspect_dynamics)


def test_atomic_masses_maps_standard_weights() -> None:
    masses = atomic_masses(np.array([1, 6, 8], dtype=np.int64))

    assert masses.tolist() == [1.008, 12.011, 15.999]


def test_atomic_masses_rejects_unknown_charge() -> None:
    with pytest.raises(DynamicsContractError, match=r"\[26\]"):
        atomic_masses(np.array([1, 26], dtype=np.int64))


def test_chronological_order_undoes_a_reversal() -> None:
    old_indices = np.array([3, 2, 1, 0], dtype=np.int64)

    order = chronological_order(old_indices)

    assert order.tolist() == [3, 2, 1, 0]


def test_chronological_order_rejects_duplicates() -> None:
    with pytest.raises(DynamicsContractError, match="unique"):
        chronological_order(np.array([0, 0, 1], dtype=np.int64))


def test_radius_of_gyration_matches_a_two_point_analytic_case() -> None:
    # Two equal masses at +/- 2 along x: Rg = 2 exactly, for any number of frames.
    coordinates = np.zeros((3, 2, 3))
    coordinates[:, 0, 0] = -2.0
    coordinates[:, 1, 0] = 2.0
    charges = np.array([6, 6], dtype=np.int64)  # equal mass by construction
    old_indices = np.array([2, 0, 1], dtype=np.int64)

    series = radius_of_gyration_series(coordinates, charges, old_indices)

    assert series.shape == (3,)
    assert np.allclose(series, 2.0)


def test_radius_of_gyration_reflects_chronological_reordering() -> None:
    # Frame 0 (raw order) is the wide one; old_indices says it is chronologically last.
    coordinates = np.zeros((2, 2, 3))
    coordinates[0, 1, 0] = 4.0  # raw frame 0: separation 4 -> Rg = 2
    coordinates[1, 1, 0] = 2.0  # raw frame 1: separation 2 -> Rg = 1
    charges = np.array([6, 6], dtype=np.int64)
    old_indices = np.array([1, 0], dtype=np.int64)  # raw 0 is chronologically after raw 1

    series = radius_of_gyration_series(coordinates, charges, old_indices)

    assert np.allclose(series, [1.0, 2.0])


def test_radius_of_gyration_rejects_mismatched_mass_axis() -> None:
    coordinates = np.zeros((2, 3, 3))
    charges = np.array([6, 6], dtype=np.int64)
    old_indices = np.array([0, 1], dtype=np.int64)

    with pytest.raises(DynamicsContractError, match="atom axis"):
        radius_of_gyration_series(coordinates, charges, old_indices)


def test_block_standard_error_matches_manual_computation_and_drops_remainder() -> None:
    values = np.arange(10, dtype=np.float64)  # 0..9, 3 blocks of 3 drops the 10th

    estimate = block_standard_error(values, blocks=3)

    expected_block_means = values[:9].reshape(3, 3).mean(axis=1)
    assert estimate.frames_per_block == 3
    assert estimate.frames_used == 9
    assert estimate.block_mean == pytest.approx(expected_block_means.mean())
    assert estimate.block_standard_error == pytest.approx(
        expected_block_means.std(ddof=1) / np.sqrt(3)
    )


def test_block_standard_error_rejects_too_few_blocks() -> None:
    with pytest.raises(DynamicsContractError, match="at least 2"):
        block_standard_error(np.arange(10, dtype=np.float64), blocks=1)


def test_block_standard_error_rejects_more_blocks_than_frames() -> None:
    with pytest.raises(DynamicsContractError, match="fewer frames"):
        block_standard_error(np.arange(3, dtype=np.float64), blocks=10)


def test_naive_standard_error_matches_textbook_formula() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    assert naive_standard_error(values) == pytest.approx(values.std(ddof=1) / np.sqrt(5))


def test_convergence_checkpoints_reproduce_full_mean_at_the_final_checkpoint() -> None:
    values = np.linspace(0.0, 1.0, 1000)

    checkpoints = convergence_checkpoints(values, (10, 1000))

    assert checkpoints[-1].frames_included == 1000
    assert checkpoints[-1].difference_from_full_trajectory == pytest.approx(0.0, abs=1e-12)
    assert checkpoints[0].frames_included == 10
    assert checkpoints[0].cumulative_mean == pytest.approx(values[:10].mean())


def test_convergence_checkpoints_rejects_an_out_of_range_checkpoint() -> None:
    with pytest.raises(DynamicsContractError, match="between 1 and 5"):
        convergence_checkpoints(np.arange(5, dtype=np.float64), (100,))


def test_show_and_check_run_end_to_end_on_synthetic_full_length_trajectories(
    tmp_path: Path, make_arrays, write_npz, monkeypatch, capsys
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("ethanol", "malonaldehyde"):
        arrays = make_arrays()
        path = data_dir / f"rmd17_{name}.npz"
        np.savez(path, **arrays)

    monkeypatch.setattr(inspect_dynamics, "DATA", data_dir)
    protocol = inspect_dynamics.load_protocol()

    results = inspect_dynamics.compute(protocol)
    inspect_dynamics.show(protocol, results)
    printed = capsys.readouterr().out
    assert "ETHANOL" in printed
    assert "MALONALDEHYDE" in printed
    assert "What this does not show" in printed

    failures = inspect_dynamics.check(protocol, results)
    printed = capsys.readouterr().out
    assert failures == []
    assert "FAIL" not in printed


def test_missing_data_file_exits_with_an_actionable_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(inspect_dynamics, "DATA", tmp_path)
    protocol = inspect_dynamics.load_protocol()

    with pytest.raises(SystemExit) as excinfo:
        inspect_dynamics.compute(protocol)
    assert excinfo.value.code == 1


def test_observable_protocol_is_consistent_json() -> None:
    protocol = json.loads((LAB / "observable-protocol.json").read_text())

    assert protocol["systems"] == ["ethanol", "malonaldehyde"]
    assert set(protocol["systems"]).isdisjoint({"benzene", "uracil"})
    assert protocol["convergence_checkpoints"][-1] == 100_000
    assert all(size >= 2 for size in protocol["block_sizes"])


def test_cli_show_runs_without_network_or_arguments() -> None:
    # The real ~64 MB-per-system rMD17 files are local execution artifacts, not
    # committed to the repository; the synthetic end-to-end test above already
    # exercises this exact code path when they are absent, as in a fresh clone.
    if not (LAB / "data/rmd17_ethanol.npz").exists():
        pytest.skip("local rMD17 development files are not distributed")
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_dynamics.py"), "show"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0
    assert "ETHANOL" in result.stdout
    assert "Run 'check' to recompute" in result.stdout
