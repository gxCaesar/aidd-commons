"""Constructed inputs isolate the model and its unit and source contracts."""

from __future__ import annotations

from copy import deepcopy

import pytest
from aidd_commons.pkpd_translation_audit.model import ModelError, simulate
from aidd_commons.pkpd_translation_audit.protocol import (
    HEPATOCYTE_UNIT,
    MICROSOME_UNIT,
    expected_protocol,
)


def specs() -> dict:
    return deepcopy(expected_protocol()["model"]["parameters"])


def test_constructed_curve_and_uncertainty() -> None:
    result = simulate(10.0, HEPATOCYTE_UNIT, 1.0, 0.5, 2.0, specs())
    assert result.clearance_l_h == pytest.approx(0.06)
    assert result.concentration_0h_umol_l == pytest.approx(1.0)
    assert result.concentration_half_interval_umol_l == pytest.approx(0.48675225596)
    assert result.concentration_umol_l == pytest.approx(0.2369277587)
    assert result.free_concentration_umol_l == pytest.approx(0.1 * result.concentration_umol_l)
    assert result.occupancy == pytest.approx(
        result.free_concentration_umol_l / (0.2 + result.free_concentration_umol_l)
    )
    assert result.effect_lower < result.effect < result.effect_upper
    assert all(a <= b for a, b in zip(result.stage_widths, result.stage_widths[1:], strict=False))


def test_unsourced_parameter_is_refused() -> None:
    parameters = specs()
    parameters["kd_umol_l"]["source"] = ""
    with pytest.raises(ModelError, match="no source"):
        simulate(10.0, HEPATOCYTE_UNIT, 1.0, 0.5, 2.0, parameters)


def test_microsome_basis_is_not_silently_converted() -> None:
    with pytest.raises(ModelError, match="per-million-cell"):
        simulate(10.0, MICROSOME_UNIT, 1.0, 0.5, 2.0, specs())
