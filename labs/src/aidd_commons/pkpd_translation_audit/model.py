"""One-compartment exposure, binding and direct-effect interval arithmetic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import exp, isfinite
from typing import Any

from .protocol import HEPATOCYTE_UNIT


class ModelError(ValueError):
    """A dimension, parameter or interval cannot support the model."""


@dataclass(frozen=True)
class ModelResult:
    clearance_l_h: float
    clearance_lower_l_h: float
    clearance_upper_l_h: float
    concentration_0h_umol_l: float
    concentration_half_interval_umol_l: float
    concentration_umol_l: float
    free_concentration_umol_l: float
    occupancy: float
    effect: float
    effect_lower: float
    effect_upper: float
    stage_widths: tuple[float, ...]


def parameter_values(specs: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    """Refuse an unproven numeric parameter even in a constructed test."""
    values: dict[str, float] = {}
    for name, spec in specs.items():
        source = spec.get("source")
        unit = spec.get("unit")
        value = spec.get("value")
        if not isinstance(source, str) or not source.strip():
            raise ModelError(f"parameter {name} has no source")
        if not isinstance(unit, str) or not unit.strip():
            raise ModelError(f"parameter {name} has no unit")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            raise ModelError(f"parameter {name} is not finite numeric")
        values[name] = float(value)
    return values


def clearance_l_h(value: float, unit: str, effective_cells: float) -> float:
    if unit != HEPATOCYTE_UNIT:
        raise ModelError("clearance requires a per-million-cell hepatocyte basis")
    if not isfinite(value) or value <= 0 or not isfinite(effective_cells) or effective_cells <= 0:
        raise ModelError("clearance and effective-cell count must be positive finite")
    return value * effective_cells * 60.0 / 1e12


def _curve(
    clearance: float,
    fu: float,
    kd: float,
    emax: float,
    ec50: float,
    dose: float,
    volume: float,
    time: float,
) -> tuple[float, float, float, float]:
    total = dose / volume * exp(-clearance / volume * time)
    free = fu * total
    occupancy = free / (kd + free)
    effect = emax * occupancy * (1 + ec50) / (ec50 + occupancy)
    return total, free, occupancy, effect


def simulate(
    rat_clearance: float,
    unit: str,
    factor: float,
    factor_lower: float,
    factor_upper: float,
    specs: Mapping[str, Mapping[str, Any]],
) -> ModelResult:
    p = parameter_values(specs)
    required = {
        "dose_umol",
        "volume_l",
        "interval_h",
        "effective_cells",
        "rat_clearance_relative_error",
        "fu",
        "fu_lower",
        "fu_upper",
        "kd_umol_l",
        "kd_lower_umol_l",
        "kd_upper_umol_l",
        "emax",
        "emax_lower",
        "emax_upper",
        "ec50_occupancy",
        "ec50_occupancy_lower",
        "ec50_occupancy_upper",
        "translation_lower_quantile",
        "translation_upper_quantile",
    }
    if set(p) != required:
        raise ModelError("parameter list differs from the declared model")
    if not (0 < p["translation_lower_quantile"] < p["translation_upper_quantile"] < 1):
        raise ModelError("translation quantiles must be ordered inside (0, 1)")
    if not (0 < factor_lower <= factor <= factor_upper):
        raise ModelError("species factors must be ordered and positive")
    if not (0 <= p["rat_clearance_relative_error"] < 1):
        raise ModelError("rat clearance relative error must be below one")
    for key in (
        "dose_umol",
        "volume_l",
        "interval_h",
        "effective_cells",
        "kd_lower_umol_l",
        "ec50_occupancy_lower",
    ):
        if p[key] <= 0:
            raise ModelError(f"{key} must be positive")
    for stem, lower, upper in (
        ("fu", "fu_lower", "fu_upper"),
        ("kd_umol_l", "kd_lower_umol_l", "kd_upper_umol_l"),
        ("emax", "emax_lower", "emax_upper"),
        ("ec50_occupancy", "ec50_occupancy_lower", "ec50_occupancy_upper"),
    ):
        if not (0 < p[lower] <= p[stem] <= p[upper]):
            raise ModelError(f"{stem} sensitivity range is invalid")
    if p["fu_upper"] > 1 or p["emax_upper"] > 1 or p["ec50_occupancy_upper"] > 1:
        raise ModelError("fractions cannot exceed one")

    base = clearance_l_h(rat_clearance, unit, p["effective_cells"])
    nominal_cl = base * factor
    low_rat = base * (1 - p["rat_clearance_relative_error"])
    high_rat = base * (1 + p["rat_clearance_relative_error"])
    low_cl = low_rat * factor_lower
    high_cl = high_rat * factor_upper
    dose, volume, time = p["dose_umol"], p["volume_l"], p["interval_h"]

    def effect_at(cl: float, fu: float, kd: float, emax: float, ec50: float) -> float:
        return _curve(cl, fu, kd, emax, ec50, dose, volume, time)[3]

    total, free, occupancy, effect = _curve(
        nominal_cl,
        p["fu"],
        p["kd_umol_l"],
        p["emax"],
        p["ec50_occupancy"],
        dose,
        volume,
        time,
    )
    stages = (
        (
            low_rat * factor,
            high_rat * factor,
            p["fu"],
            p["fu"],
            p["kd_umol_l"],
            p["kd_umol_l"],
            p["emax"],
            p["emax"],
            p["ec50_occupancy"],
            p["ec50_occupancy"],
        ),
        (
            low_cl,
            high_cl,
            p["fu"],
            p["fu"],
            p["kd_umol_l"],
            p["kd_umol_l"],
            p["emax"],
            p["emax"],
            p["ec50_occupancy"],
            p["ec50_occupancy"],
        ),
        (
            low_cl,
            high_cl,
            p["fu_lower"],
            p["fu_upper"],
            p["kd_umol_l"],
            p["kd_umol_l"],
            p["emax"],
            p["emax"],
            p["ec50_occupancy"],
            p["ec50_occupancy"],
        ),
        (
            low_cl,
            high_cl,
            p["fu_lower"],
            p["fu_upper"],
            p["kd_lower_umol_l"],
            p["kd_upper_umol_l"],
            p["emax"],
            p["emax"],
            p["ec50_occupancy"],
            p["ec50_occupancy"],
        ),
        (
            low_cl,
            high_cl,
            p["fu_lower"],
            p["fu_upper"],
            p["kd_lower_umol_l"],
            p["kd_upper_umol_l"],
            p["emax_lower"],
            p["emax_upper"],
            p["ec50_occupancy_lower"],
            p["ec50_occupancy_upper"],
        ),
    )
    bounds: list[tuple[float, float]] = []
    for stage in stages:
        cl_low, cl_high, fu_low, fu_high, kd_low, kd_high, em_low, em_high, ec_low, ec_high = stage
        lower_effect = effect_at(cl_high, fu_low, kd_high, em_low, ec_high)
        upper_effect = effect_at(cl_low, fu_high, kd_low, em_high, ec_low)
        bounds.append((lower_effect, upper_effect))
    widths = tuple(high - low for low, high in bounds)
    return ModelResult(
        clearance_l_h=nominal_cl,
        clearance_lower_l_h=low_cl,
        clearance_upper_l_h=high_cl,
        concentration_0h_umol_l=dose / volume,
        concentration_half_interval_umol_l=dose / volume * exp(-nominal_cl / volume * time / 2),
        concentration_umol_l=total,
        free_concentration_umol_l=free,
        occupancy=occupancy,
        effect=effect,
        effect_lower=bounds[-1][0],
        effect_upper=bounds[-1][1],
        stage_widths=widths,
    )
