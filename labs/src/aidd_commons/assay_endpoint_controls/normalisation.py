"""The control-normalisation equations and the Hill curve, as executable code.

The lessons state the control-normalisation equations in prose. This module is
where those sentences become functions that can be read, tested against
hand-computed values, and run on the archived assay records.

Three normalisation regimes appear in the declared assay set, and they are
different mathematical objects:

``wells_relative_to_two_references``
    The response of one well is placed between a full-response reference well
    and a no-response reference well. This is the equation archived for the
    formylpeptide receptor assay and the neuropeptide Y1 assay.

``archived_pka_equation``
    The equation as it is written in the archived protein kinase A protocol.
    It is kept as its own function, and separately from the conventional
    rearrangement, because the two do not agree about which end of the scale
    the positive control sits on.

``relative_to_one_reference``
    The response is placed relative to a single full-response reference. The
    baseline is not stated in the archived protocol, so the function requires
    one and refuses to guess it.

Every function here raises ``NormalisationUndefinedError`` when the archive
does not supply what the equation needs. That refusal is the teaching point:
an assay whose record does not define the denominator of its own normalisation
cannot be put on a common scale, and the lab says so instead of inventing a
number.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray


class NormalisationUndefinedError(ValueError):
    """Raised when an archived record does not supply what an equation needs."""


def percent_inhibition_wells(
    signal: float, positive_control: float, negative_control: float
) -> float:
    """Percent inhibition from a test well and two reference wells.

    This is the equation archived for assay 519 and, in its ratio form, for
    assay 1277::

        %Inhibition = 100 x [1 - (signal - positive_control)
                              / (negative_control - positive_control)]

    The positive control is the full-response reference and the negative
    control is the no-response reference, so the test well at the positive
    control gives 0 percent and the test well at the negative control gives
    100 percent.
    """
    span = negative_control - positive_control
    if span == 0.0:
        raise NormalisationUndefinedError(
            "the positive and negative controls have the same value, so the normalisation "
            "has no dynamic range"
        )
    return 100.0 * (1.0 - (signal - positive_control) / span)


def percent_inhibition_archived_pka(
    signal: float, positive_control: float, negative_control: float
) -> float:
    """Percent inhibition as the archived protein kinase A protocol writes it.

    The archived equation is::

        %inhibition = (test_compound - median_positive_control)
                      / (median_positive_control - median_negative_control) * 100

    It is kept verbatim because the point of the lab is that this equation and
    the archived values do not agree about the direction of the scale. Use
    ``percent_inhibition_conventional`` to see the rearranged form.
    """
    span = positive_control - negative_control
    if span == 0.0:
        raise NormalisationUndefinedError(
            "the positive and negative controls have the same value, so the normalisation "
            "has no dynamic range"
        )
    return 100.0 * (signal - positive_control) / span


def percent_inhibition_conventional(
    signal: float, positive_control: float, negative_control: float
) -> float:
    """Percent inhibition on the scale the archived values are actually on.

    ::

        %Inhibition = 100 x (positive_control - signal)
                      / (positive_control - negative_control)

    The test well at the positive control gives 0 percent and the test well at
    the negative control gives 100 percent, which is the direction the
    archived per-concentration values run in.
    """
    span = positive_control - negative_control
    if span == 0.0:
        raise NormalisationUndefinedError(
            "the positive and negative controls have the same value, so the normalisation "
            "has no dynamic range"
        )
    return 100.0 * (positive_control - signal) / span


def percent_relative_to_one_reference(
    signal: float, positive_control: float, baseline: float | None
) -> float:
    """Percent of a single full-response reference.

    ::

        %response = 100 x (signal - baseline) / (positive_control - baseline)

    The archived protocols for the assays in this regime name the reference
    but not the baseline, so ``baseline`` is a required argument. Passing
    ``None`` is refused rather than silently treated as zero.
    """
    if baseline is None:
        raise NormalisationUndefinedError(
            "the archived protocol names one reference but no baseline, so the response "
            "cannot be placed on a 0-to-100 scale"
        )
    span = positive_control - baseline
    if span == 0.0:
        raise NormalisationUndefinedError(
            "the reference and the baseline have the same value, so the normalisation "
            "has no dynamic range"
        )
    return 100.0 * (signal - baseline) / span


def hill_response(
    concentration: NDArray[np.float64],
    ec50: float,
    hill_slope: float,
    baseline: float,
    amplitude: float,
) -> NDArray[np.float64]:
    """The four-parameter logistic concentration-response curve.

    ::

        y(c) = baseline + amplitude * c^h / (ec50^h + c^h)

    With ``baseline`` and ``amplitude`` taken from the archived fitted
    asymptotes this reproduces the archived per-concentration values for the
    assays that archive them. With ``baseline = 0`` and ``amplitude = 100`` it
    is the curve an assay that fixes its range at 0 to 100 percent is
    describing, and with ``baseline = 0`` and ``amplitude = -100`` it is the
    activation curve of an assay whose top is fixed at 100 percent.

    The concentration and the ``ec50`` must be in the same unit, which this
    protocol fixes as micromolar.
    """
    if ec50 <= 0.0:
        raise ValueError("the half-maximal concentration must be positive")
    if hill_slope == 0.0:
        raise ValueError("the Hill coefficient must not be zero")
    ratio = np.power(concentration / ec50, hill_slope)
    return baseline + amplitude * ratio / (1.0 + ratio)


def fit_hill_curve(
    concentrations: Sequence[float],
    responses: Sequence[float],
    *,
    fixed_baseline: float | None = None,
    fixed_amplitude: float | None = None,
) -> tuple[float, float, float, float]:
    """Fit the four-parameter logistic curve to archived points.

    Returns ``(ec50, hill_slope, baseline, amplitude)``. When
    ``fixed_baseline`` or ``fixed_amplitude`` is given, that parameter is held
    at the given value and is not fitted, which is what an assay that fixes
    the bottom or the top of its range does.

    The fit is a plain non-linear least-squares fit on the raw archived
    points. It is used only where the archived record does not carry the
    fitted asymptotes, so that the archived endpoint can be compared with a
    curve computed from the archived per-concentration values.
    """
    from scipy.optimize import curve_fit

    x = np.asarray(concentrations, dtype=np.float64)
    y = np.asarray(responses, dtype=np.float64)
    if x.size < 4:
        raise NormalisationUndefinedError("at least four points are needed to fit a Hill curve")
    if np.any(x <= 0.0):
        raise ValueError("every concentration must be positive")
    if not np.all(np.isfinite(y)):
        raise ValueError("every response must be finite")

    fixed: dict[str, float | None] = {
        "ec50": None,
        "slope": None,
        "baseline": fixed_baseline,
        "amplitude": fixed_amplitude,
    }
    order = ("ec50", "slope", "baseline", "amplitude")
    free = [name for name in order if fixed[name] is None]
    starts = {
        "ec50": float(np.median(x)),
        "slope": 1.0,
        "baseline": float(y.min()),
        "amplitude": float(y.max() - y.min()) or 100.0,
    }
    lower = {"ec50": 1e-12, "slope": 1e-3, "baseline": -np.inf, "amplitude": -np.inf}
    upper = {"ec50": np.inf, "slope": 50.0, "baseline": np.inf, "amplitude": np.inf}

    def model(concentration: NDArray[np.float64], *free_values: float) -> NDArray[np.float64]:
        values = {name: float(value) for name, value in zip(free, free_values, strict=True)}
        for name in order:
            pinned = fixed[name]
            if pinned is not None:
                values[name] = float(pinned)
        return hill_response(
            concentration, values["ec50"], values["slope"], values["baseline"], values["amplitude"]
        )

    fitted, _ = curve_fit(
        model,
        x,
        y,
        p0=[starts[name] for name in free],
        bounds=([lower[name] for name in free], [upper[name] for name in free]),
        maxfev=40000,
    )
    values = {name: float(value) for name, value in zip(free, fitted, strict=True)}
    for name in order:
        pinned = fixed[name]
        if pinned is not None:
            values[name] = float(pinned)
    return values["ec50"], values["slope"], values["baseline"], values["amplitude"]


def compound_split_bucket(seed: int, compound_id: str) -> int:
    """The deterministic split bucket of one compound.

    The bucket is the parity of the first eight bytes of a SHA-256 digest of
    the seed and the compound identifier, read as an unsigned integer. It does
    not depend on row order, on how many compounds the assay contains, or on
    any fitted quantity, so the same compound always lands in the same half.
    """
    seed_bytes = hashlib.sha256(f"{seed}:{compound_id}".encode()).digest()
    return int.from_bytes(seed_bytes[:8], "big") % 2
