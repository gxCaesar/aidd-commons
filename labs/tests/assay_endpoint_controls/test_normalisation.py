"""The control-normalisation equations and the Hill curve, against literal oracles.

Every expected value here is computed by hand from the equation the archived
protocol states, so a change in the code that changes the number fails the
test rather than quietly changing the lab's output.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from aidd_commons.assay_endpoint_controls.normalisation import (
    NormalisationUndefinedError,
    compound_split_bucket,
    fit_hill_curve,
    hill_response,
    percent_inhibition_archived_pka,
    percent_inhibition_conventional,
    percent_inhibition_wells,
    percent_relative_to_one_reference,
)


def test_the_two_reference_equation_puts_the_full_response_at_one_hundred() -> None:
    # 100 * [1 - (signal - 100) / (0 - 100)]
    assert percent_inhibition_wells(100.0, 100.0, 0.0) == pytest.approx(100.0)
    assert percent_inhibition_wells(0.0, 100.0, 0.0) == pytest.approx(0.0)
    assert percent_inhibition_wells(50.0, 100.0, 0.0) == pytest.approx(50.0)
    assert percent_inhibition_wells(150.0, 200.0, 100.0) == pytest.approx(50.0)
    # A signal below the no-response reference falls below zero percent.
    assert percent_inhibition_wells(25.0, 200.0, 100.0) == pytest.approx(-75.0)


def test_the_two_reference_equation_refuses_a_reference_pair_without_dynamic_range() -> None:
    with pytest.raises(NormalisationUndefinedError, match="dynamic range"):
        percent_inhibition_wells(10.0, 5.0, 5.0)


def test_the_archived_pka_equation_runs_from_zero_to_minus_one_hundred() -> None:
    # 100 * (signal - 100) / (100 - 0)
    assert percent_inhibition_archived_pka(100.0, 100.0, 0.0) == pytest.approx(0.0)
    assert percent_inhibition_archived_pka(0.0, 100.0, 0.0) == pytest.approx(-100.0)
    assert percent_inhibition_archived_pka(50.0, 100.0, 0.0) == pytest.approx(-50.0)


def test_the_conventional_rearrangement_runs_from_zero_to_one_hundred() -> None:
    assert percent_inhibition_conventional(100.0, 100.0, 0.0) == pytest.approx(0.0)
    assert percent_inhibition_conventional(0.0, 100.0, 0.0) == pytest.approx(100.0)
    assert percent_inhibition_conventional(50.0, 100.0, 0.0) == pytest.approx(50.0)


def test_the_single_reference_equation_needs_a_baseline_and_refuses_without_one() -> None:
    assert percent_relative_to_one_reference(100.0, 100.0, 0.0) == pytest.approx(100.0)
    assert percent_relative_to_one_reference(0.0, 100.0, 0.0) == pytest.approx(0.0)
    assert percent_relative_to_one_reference(50.0, 100.0, 0.0) == pytest.approx(50.0)
    with pytest.raises(NormalisationUndefinedError, match="baseline"):
        percent_relative_to_one_reference(50.0, 100.0, None)


def test_the_hill_curve_hits_the_half_maximal_concentration() -> None:
    concentrations = np.array([0.01, 0.1, 1.0, 10.0, 100.0])
    values = hill_response(concentrations, 1.0, 1.0, 0.0, 100.0)
    assert values[2] == pytest.approx(50.0)
    assert values[0] == pytest.approx(100.0 / 101.0)
    assert values[-1] == pytest.approx(100.0 * 100.0 / 101.0)


def test_the_hill_curve_honours_the_archived_asymptotes() -> None:
    concentrations = np.array([0.003, 0.682, 60.0])
    values = hill_response(concentrations, 0.682, 1.16, 5.228, 96.435)
    assert values[1] == pytest.approx(5.228 + 96.435 / 2.0)
    low_ratio = (0.003 / 0.682) ** 1.16
    high_ratio = (60.0 / 0.682) ** 1.16
    assert values[0] == pytest.approx(5.228 + 96.435 * low_ratio / (1 + low_ratio))
    assert values[-1] == pytest.approx(5.228 + 96.435 * high_ratio / (1 + high_ratio))


def test_the_hill_curve_refuses_an_impossible_parameter() -> None:
    with pytest.raises(ValueError, match="positive"):
        hill_response(np.array([1.0]), 0.0, 1.0, 0.0, 100.0)
    with pytest.raises(ValueError, match="Hill coefficient"):
        hill_response(np.array([1.0]), 1.0, 0.0, 0.0, 100.0)


def test_fitting_recovers_the_parameters_of_a_synthetic_curve() -> None:
    truth_ec50, truth_slope, truth_base, truth_amplitude = 2.0, 1.4, 3.0, 97.0
    concentrations = np.array([0.01, 0.1, 1.0, 10.0, 100.0])
    responses = hill_response(
        concentrations, truth_ec50, truth_slope, truth_base, truth_amplitude
    )
    ec50, slope, baseline, amplitude = fit_hill_curve(
        concentrations.tolist(), responses.tolist()
    )
    assert ec50 == pytest.approx(truth_ec50, rel=1e-4)
    assert slope == pytest.approx(truth_slope, rel=1e-4)
    assert baseline == pytest.approx(truth_base, abs=1e-3)
    assert amplitude == pytest.approx(truth_amplitude, rel=1e-4)


def test_fitting_with_a_fixed_range_holds_the_asymptotes() -> None:
    concentrations = np.array([0.1, 1.0, 10.0, 100.0])
    responses = hill_response(concentrations, 1.0, 1.0, 0.0, 100.0)
    ec50, slope, baseline, amplitude = fit_hill_curve(
        concentrations.tolist(), responses.tolist(), fixed_baseline=0.0, fixed_amplitude=100.0
    )
    assert baseline == 0.0
    assert amplitude == 100.0
    assert ec50 == pytest.approx(1.0, rel=1e-4)
    assert slope == pytest.approx(1.0, rel=1e-4)


def test_fitting_refuses_a_curve_it_cannot_be_given() -> None:
    with pytest.raises(NormalisationUndefinedError, match="four points"):
        fit_hill_curve([1.0, 2.0], [0.0, 1.0])
    with pytest.raises(ValueError, match="positive"):
        fit_hill_curve([0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="finite"):
        fit_hill_curve([1.0, 2.0, 3.0, 4.0], [0.0, 1.0, float("nan"), 3.0])


def test_the_split_bucket_is_deterministic_and_balanced_over_the_declared_set() -> None:
    assert compound_split_bucket(20261021, "5056270") == compound_split_bucket(20261021, "5056270")
    assert compound_split_bucket(20261021, "5056270") in (0, 1)
    assert compound_split_bucket(20261021, "5056270") != compound_split_bucket(1, "5056270")
    buckets = [compound_split_bucket(20261021, str(index)) for index in range(1000)]
    assert abs(sum(buckets) - 500) < 60


def test_the_split_bucket_matches_an_independent_computation_of_the_declared_rule() -> None:
    import hashlib

    for compound in ("1", "42", "659413", "2321431"):
        seed_bytes = hashlib.sha256(f"20261021:{compound}".encode()).digest()
        expected = int.from_bytes(seed_bytes[:8], "big") % 2
        assert compound_split_bucket(20261021, compound) == expected
    assert math.isclose(
        compound_split_bucket(20261021, "7"),
        int.from_bytes(hashlib.sha256(b"20261021:7").digest()[:8], "big") % 2,
    )
