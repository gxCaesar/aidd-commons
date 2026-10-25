"""The descriptive read-out of the declared assay set.

The order of this module is the order of the lab: the cheap baseline first
(counts and distributions), then the concentration-response checks, then the
statement of what each assay does and does not license. No model is fitted
anywhere except the per-compound Hill refit, which exists only where the
archived record does not carry the fitted asymptotes, and which uses only the
archived points of the compound it describes.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from statistics import median

import numpy as np
from numpy.typing import NDArray

from .data import AssayDataset, MeasurementRow
from .normalisation import (
    NormalisationUndefinedError,
    compound_split_bucket,
    fit_hill_curve,
    hill_response,
    percent_inhibition_archived_pka,
    percent_inhibition_conventional,
    percent_inhibition_wells,
    percent_relative_to_one_reference,
)
from .protocol import (
    AMBIGUOUS_CONTROL_WORDS,
    CONTROL_KEYWORDS,
    CONTROL_REGIMES,
    CURVE_TOLERANCE_POINTS,
    EQUATION_SCALE_BAND_POINTS,
    EQUATION_SCALE_FRACTION,
    REFERENCE_KEYWORDS,
    SPLIT_SEED,
    AssaySpec,
)


class AnalysisContractError(ValueError):
    """Raised when an analysis input does not meet its declared shape."""


@dataclass(frozen=True)
class MixSummary:
    """A distribution over a small set of named categories."""

    counts: Mapping[str, int]
    total: int

    def fraction(self, key: str) -> float:
        if self.total == 0:
            return 0.0
        return self.counts.get(key, 0) / self.total


@dataclass(frozen=True)
class ScoreSummary:
    """The distribution of the archived confidence score."""

    count: int
    minimum: float
    median: float
    maximum: float
    fraction_at_maximum: float
    fraction_zero: float


@dataclass(frozen=True)
class ReferenceAudit:
    """What the archived protocol says about controls, blanks and vehicles."""

    declared_regime: str
    control_keywords: tuple[str, ...]
    ambiguous_words: tuple[str, ...]
    reference_keywords: tuple[str, ...]
    references_declared: int
    normalisation_equation: str
    archived_equation_text: str
    equation_value_at_positive_control: float | None
    equation_value_at_negative_control: float | None
    equation_scale_verdict: str
    equation_matches_archived_scale: bool | None
    fraction_inside_equation_range: float | None
    archived_scale_low: float | None
    archived_scale_high: float | None
    archived_response_min: float | None
    archived_response_max: float | None
    archived_values_above_hundred: int
    archived_values_below_zero: int


@dataclass(frozen=True)
class CurveAgreement:
    """How far the archived curve sits from the curve the record describes."""

    curves: int
    points: int
    median_absolute_deviation: float | None
    p90_absolute_deviation: float | None
    maximum_absolute_deviation: float | None
    fraction_within_tolerance: float | None
    median_endpoint_log10_error: float | None
    fraction_endpoint_within_factor_three: float | None


@dataclass(frozen=True)
class CurveCheck:
    """The concentration-response check for one assay and one split bucket."""

    mode: str
    tolerance_points: float
    recomputed_curves: int
    refitted_curves: int
    skipped_rows: int
    development: CurveAgreement
    heldout: CurveAgreement


@dataclass(frozen=True)
class AssayProfile:
    """Everything the lab reports about one declared assay."""

    aid: int
    name: str
    endpoint_label: str
    endpoint_unit: str
    direction: str
    input_rows: int
    retained_rows: int
    admitted_compounds: int
    exclusion_counts: Mapping[str, int]
    outcome_mix: MixSummary
    relation_mix: MixSummary
    readout_mix: MixSummary
    score: ScoreSummary
    replicate_counts: MixSummary
    replicate_declaration: str
    determination_column: str
    determination_kind: str
    hill_fit_mode: str
    reference_audit: ReferenceAudit
    curve_check: CurveCheck
    licensed_claims: tuple[str, ...]
    unlicensed_claims: tuple[str, ...]
    examples: tuple[Mapping[str, object], ...] = field(default_factory=tuple)


def _numeric_points(row: MeasurementRow) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    concentrations = [point.concentration_um for point in row.points if point.value is not None]
    values = [point.value for point in row.points if point.value is not None]
    return (
        np.asarray(concentrations, dtype=np.float64),
        np.asarray(values, dtype=np.float64),
    )


def _split_bucket(row: MeasurementRow, seed: int) -> int:
    return compound_split_bucket(seed, row.compound_id)


def readout_mix(datasets: Mapping[int, AssayDataset]) -> MixSummary:
    """The distribution of the archived endpoint labels over the whole set."""
    counter: Counter[str] = Counter()
    for dataset in datasets.values():
        for row in dataset.rows:
            for label in row.endpoints:
                counter[label] += 1
    return MixSummary(counts=dict(sorted(counter.items())), total=sum(counter.values()))


def relation_mix(datasets: Mapping[int, AssayDataset]) -> MixSummary:
    """The distribution of the archived relation qualifiers over the whole set.

    An equality is a measurement. A bound, ``<`` or ``>``, is a censored
    value: the archive states that the true value lies on one side of the
    number and the number itself is not the measurement.
    """
    counter: Counter[str] = Counter()
    for dataset in datasets.values():
        for row in dataset.rows:
            qualifier = row.qualifier or "unstated"
            counter[qualifier] += 1
    return MixSummary(counts=dict(sorted(counter.items())), total=sum(counter.values()))


def score_summary(rows: Sequence[MeasurementRow]) -> ScoreSummary:
    """The distribution of the archived confidence score."""
    scores = [row.activity_score for row in rows if row.activity_score is not None]
    if not scores:
        raise AnalysisContractError("no archived row carries a confidence score")
    ordered = sorted(scores)
    return ScoreSummary(
        count=len(ordered),
        minimum=ordered[0],
        median=float(median(ordered)),
        maximum=ordered[-1],
        fraction_at_maximum=sum(1 for score in ordered if score == ordered[-1]) / len(ordered),
        fraction_zero=sum(1 for score in ordered if score == 0.0) / len(ordered),
    )


def _equation_endpoints(equation: str) -> tuple[float | None, float | None]:
    """The values the archived equation gives at the two reference wells.

    A positive control and a negative control that differ by one hundred
    units are used, so the numbers below are the equation's own mapping of the
    two references onto the response scale.
    """
    positive, negative = 100.0, 0.0
    try:
        if equation == "wells_relative_to_two_references":
            return (
                percent_inhibition_wells(positive, positive, negative),
                percent_inhibition_wells(negative, positive, negative),
            )
        if equation == "archived_pka_equation":
            return (
                percent_inhibition_archived_pka(positive, positive, negative),
                percent_inhibition_archived_pka(negative, positive, negative),
            )
        if equation == "relative_to_one_reference":
            return (
                percent_relative_to_one_reference(positive, positive, 0.0),
                percent_relative_to_one_reference(0.0, positive, 0.0),
            )
    except NormalisationUndefinedError:
        return (None, None)
    return (None, None)


def reference_audit(dataset: AssayDataset) -> ReferenceAudit:
    """Audit what the archived protocol declares about controls and references.

    The last part of the audit is the interesting one. The archived equation
    is run at its own reference wells, which gives the two numbers it would
    produce for a full response and for no response. Those two numbers are
    compared with the extremes the archived per-concentration values actually
    reach, under whichever pairing fits better. When they do not agree, the
    equation as written is not the equation that produced the archived values.
    """
    spec = dataset.spec
    if spec.control_regime not in CONTROL_REGIMES:
        raise AnalysisContractError(f"assay {spec.aid}: unknown control regime")
    lowered = dataset.protocol_text.lower()
    control_keywords = tuple(keyword for keyword in CONTROL_KEYWORDS if keyword in lowered)
    ambiguous_words = tuple(word for word in AMBIGUOUS_CONTROL_WORDS if word in lowered)
    reference_keywords = tuple(keyword for keyword in REFERENCE_KEYWORDS if keyword in lowered)
    at_positive, at_negative = _equation_endpoints(spec.normalisation_equation)
    values = [
        point.value for row in dataset.rows for point in row.points if point.value is not None
    ]
    scale_low = float(np.percentile(values, 5)) if values else None
    scale_high = float(np.percentile(values, 95)) if values else None
    observed_min = float(min(values)) if values else None
    observed_max = float(max(values)) if values else None
    above_hundred = sum(1 for value in values if value > 100.0)
    below_zero = sum(1 for value in values if value < 0.0)

    verdict = "not_declared"
    matches: bool | None = None
    fraction_inside: float | None = None
    if at_positive is not None and at_negative is not None:
        low = min(at_positive, at_negative)
        high = max(at_positive, at_negative)
        if abs((high - low) - 100.0) <= EQUATION_SCALE_BAND_POINTS:
            verdict = (
                "zero_to_hundred_scale"
                if abs(low) <= EQUATION_SCALE_BAND_POINTS
                else "shifted_scale"
            )
        else:
            verdict = "other_scale"
        if values:
            inside = sum(
                1
                for value in values
                if low - EQUATION_SCALE_BAND_POINTS
                <= value
                <= high + EQUATION_SCALE_BAND_POINTS
            )
            fraction_inside = inside / len(values)
            matches = fraction_inside >= EQUATION_SCALE_FRACTION
    return ReferenceAudit(
        declared_regime=spec.control_regime,
        control_keywords=control_keywords,
        ambiguous_words=ambiguous_words,
        reference_keywords=reference_keywords,
        references_declared=len(reference_keywords),
        normalisation_equation=spec.normalisation_equation,
        archived_equation_text=spec.archived_normalisation_text,
        equation_value_at_positive_control=at_positive,
        equation_value_at_negative_control=at_negative,
        equation_scale_verdict=verdict,
        equation_matches_archived_scale=matches,
        fraction_inside_equation_range=fraction_inside,
        archived_scale_low=scale_low,
        archived_scale_high=scale_high,
        archived_response_min=observed_min,
        archived_response_max=observed_max,
        archived_values_above_hundred=above_hundred,
        archived_values_below_zero=below_zero,
    )


def _archived_parameters(
    row: MeasurementRow, spec: AssaySpec
) -> tuple[float, float, float, float] | None:
    """``(ec50, slope, baseline, amplitude)`` as the archive states them."""
    endpoint = row.endpoints.get(spec.endpoint_label)
    if endpoint is None or endpoint <= 0.0:
        return None
    columns = spec.hill_parameter_columns
    if not columns:
        return None
    slope = _row_number(row, columns[0])
    if slope is None or slope == 0.0:
        return None
    if len(columns) < 3:
        return None
    baseline = _row_number(row, columns[1])
    amplitude = _row_number(row, columns[2])
    if baseline is None or amplitude is None:
        return None
    return (endpoint, slope, baseline, amplitude - baseline)


def _row_number(row: MeasurementRow, column: str) -> float | None:
    """A numeric value the archived row carries in one of its own columns.

    The per-row Hill columns are not part of the endpoint contract, so they
    are read from the archived row text kept alongside the parsed fields.
    """
    return row.extra_numbers.get(column)


def _agreement(
    deviations: Sequence[float],
    endpoint_errors: Sequence[float],
    tolerance: float,
    curves: int,
    points: int,
) -> CurveAgreement:
    if not deviations:
        return CurveAgreement(
            curves=curves,
            points=points,
            median_absolute_deviation=None,
            p90_absolute_deviation=None,
            maximum_absolute_deviation=None,
            fraction_within_tolerance=None,
            median_endpoint_log10_error=None,
            fraction_endpoint_within_factor_three=None,
        )
    ordered = sorted(deviations)
    index = min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))
    log_errors = sorted(abs(error) for error in endpoint_errors)
    return CurveAgreement(
        curves=curves,
        points=points,
        median_absolute_deviation=float(ordered[len(ordered) // 2]),
        p90_absolute_deviation=float(ordered[index]),
        maximum_absolute_deviation=float(ordered[-1]),
        fraction_within_tolerance=sum(1 for value in ordered if value <= tolerance) / len(ordered),
        median_endpoint_log10_error=(
            float(log_errors[len(log_errors) // 2]) if log_errors else None
        ),
        fraction_endpoint_within_factor_three=(
            sum(1 for value in log_errors if value <= np.log10(3.0)) / len(log_errors)
            if log_errors
            else None
        ),
    )


def _curve_check(
    dataset: AssayDataset, *, seed: int, tolerance: float
) -> CurveCheck:
    """Compare the archived per-concentration values with the archived curve.

    Two modes are possible and the archive decides which one applies. Where
    the archive carries the fitted asymptotes, the curve is recomputed from
    the archived parameters and the deviation from the archived values is
    measured. Where it does not, the lab fits its own four-parameter logistic
    to each compound's archived points, using only that compound's points,
    and compares the fitted endpoint with the archived one.
    """
    spec = dataset.spec
    if not spec.concentration_columns_are_numeric:
        return CurveCheck(
            mode="not_applicable_categorical_readout",
            tolerance_points=tolerance,
            recomputed_curves=0,
            refitted_curves=0,
            skipped_rows=len(dataset.rows),
            development=_agreement([], [], tolerance, 0, 0),
            heldout=_agreement([], [], tolerance, 0, 0),
        )

    deviations: dict[int, list[float]] = {0: [], 1: []}
    endpoint_errors: dict[int, list[float]] = {0: [], 1: []}
    curves: Counter[int] = Counter()
    points: Counter[int] = Counter()
    recomputed = 0
    refitted = 0
    skipped = 0

    for row in dataset.rows:
        bucket = _split_bucket(row, seed)
        concentrations, values = _numeric_points(row)
        if concentrations.size == 0:
            skipped += 1
            continue
        archived = _archived_parameters(row, spec)
        if archived is not None:
            ec50, slope, baseline, amplitude = archived
            predicted = hill_response(concentrations, ec50, slope, baseline, amplitude)
            deviations[bucket].extend(np.abs(values - predicted).tolist())
            points[bucket] += int(concentrations.size)
            curves[bucket] += 1
            recomputed += 1
            continue
        if row.qualifier in ("<", ">"):
            skipped += 1
            continue
        try:
            fitted_ec50, fitted_slope, fitted_baseline, fitted_amplitude = fit_hill_curve(
                concentrations.tolist(),
                values.tolist(),
                fixed_baseline=0.0 if spec.hill_fit_mode == "fixed_range" else None,
                fixed_amplitude=100.0 if spec.hill_fit_mode == "fixed_range" else None,
            )
        except (NormalisationUndefinedError, ValueError):
            skipped += 1
            continue
        predicted = hill_response(
            concentrations, fitted_ec50, fitted_slope, fitted_baseline, fitted_amplitude
        )
        deviations[bucket].extend(np.abs(values - predicted).tolist())
        points[bucket] += int(concentrations.size)
        curves[bucket] += 1
        refitted += 1
        archived_endpoint = row.endpoints.get(spec.endpoint_label)
        if archived_endpoint and archived_endpoint > 0.0:
            endpoint_errors[bucket].append(
                float(abs(np.log10(fitted_ec50 / archived_endpoint)))
            )

    mode = (
        "recompute_from_archived_parameters"
        if spec.hill_fit_mode == "recompute"
        else "refit_from_archived_points"
    )
    return CurveCheck(
        mode=mode,
        tolerance_points=tolerance,
        recomputed_curves=recomputed,
        refitted_curves=refitted,
        skipped_rows=skipped,
        development=_agreement(
            deviations[0], endpoint_errors[0], tolerance, curves[0], points[0]
        ),
        heldout=_agreement(deviations[1], endpoint_errors[1], tolerance, curves[1], points[1]),
    )


def _claims(
    spec: AssaySpec, audit: ReferenceAudit
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """What the archived record licenses and what it does not.

    The licensed list is about this assay. The unlicensed list is about the
    conclusions a reader might otherwise draw from it.
    """
    licensed: list[str] = []
    unlicensed: list[str] = []
    if spec.control_regime == "positive_and_negative_reference":
        licensed.append(
            "The archived per-concentration values, read on the scale the archived protocol "
            "states, and the archived endpoint with its qualifier."
        )
        licensed.append(
            "A comparison of two compounds measured in this assay under this normalisation, "
            "because both references are named and the equation is written down."
        )
        unlicensed.append(
            "A comparison of this assay's per-concentration values with the values of an "
            "assay normalised differently, without redoing the normalisation on the raw "
            "signal, which the archive does not carry."
        )
        if audit.equation_matches_archived_scale is False:
            unlicensed.append(
                "The equation as it is written in the archived protocol, because it does not "
                "reproduce the scale the archived values are on."
            )
    elif spec.control_regime == "single_positive_reference":
        licensed.append(
            "The archived endpoint and its qualifier, and the shape of one compound's own "
            "archived curve."
        )
        licensed.append(
            "A statement that one compound reached more response than another at the same "
            "tested concentration, on this assay's own scale."
        )
        unlicensed.append(
            "The zero end of the response scale, because the archived protocol names one "
            "reference and no baseline, so the absolute percent has no stated origin."
        )
        unlicensed.append(
            "A claim that the response is 100 percent at any concentration, because the "
            "reference is only stated to define the top of the scale."
        )
    else:
        licensed.append(
            "A statement about this compound at the stated concentrations, on the terms the "
            "archive itself uses, including the boundary of its reported threshold."
        )
        unlicensed.append(
            "Any ranking of compounds by potency, because the endpoints of the response "
            "scale are set by controls that the archived protocol never names."
        )
        unlicensed.append(
            "Any statement that the response was 0 percent or 100 percent at any "
            "concentration, because the archive reports categories and no defined scale."
        )
        unlicensed.append(
            "A comparison of this assay's thresholds with the endpoints of an assay whose "
            "scale is defined by named controls."
        )
    if audit.archived_values_above_hundred:
        unlicensed.append(
            f"A statement that every archived per-concentration value is a percentage on a "
            f"0-to-100 scale, because {audit.archived_values_above_hundred} of the archived "
            "values fall above 100."
        )
    return tuple(licensed), tuple(unlicensed)


def _examples(dataset: AssayDataset, count: int = 2) -> tuple[Mapping[str, object], ...]:
    """A fixed number of named examples, with the raw values that back them.

    The examples carry the archived per-concentration values so that a reader
    can check the normalisation and the curve by hand without the cache.
    """
    spec = dataset.spec
    chosen: list[Mapping[str, object]] = []
    ordered = sorted(dataset.rows, key=lambda row: row.compound_id)
    for row in ordered:
        if len(chosen) >= count:
            break
        if not row.endpoints:
            continue
        entry: dict[str, object] = {
            "compound_id": row.compound_id,
            "outcome": row.outcome,
            "activity_score": row.activity_score,
            "qualifier": row.qualifier,
            "endpoints": dict(sorted(row.endpoints.items())),
        }
        if spec.concentration_columns_are_numeric:
            entry["concentrations_um"] = [point.concentration_um for point in row.points]
            entry["responses"] = [point.value for point in row.points]
        else:
            entry["concentrations_um"] = [point.concentration_um for point in row.points]
            entry["concentration_categories"] = [point.category for point in row.points]
        chosen.append(entry)
    return tuple(chosen)


def assay_profile(dataset: AssayDataset, *, seed: int = SPLIT_SEED) -> AssayProfile:
    """The full descriptive profile of one declared assay."""
    spec = dataset.spec
    audit = reference_audit(dataset)
    counter: Counter[str] = Counter()
    for row in dataset.rows:
        counter[row.outcome or "unstated"] += 1
    relations: Counter[str] = Counter()
    for row in dataset.rows:
        relations[row.qualifier or "unstated"] += 1
    readouts: Counter[str] = Counter()
    for row in dataset.rows:
        for label in row.endpoints:
            readouts[label] += 1
    replicates: Counter[str] = Counter()
    for row in dataset.rows:
        replicates[str(row.replicate_count) if row.replicate_count is not None else "unstated"] += 1
    licensed, unlicensed = _claims(spec, audit)
    return AssayProfile(
        aid=spec.aid,
        name=dataset.name,
        endpoint_label=spec.endpoint_label,
        endpoint_unit=spec.endpoint_units[0],
        direction=spec.direction,
        input_rows=dataset.audit.input_rows,
        retained_rows=dataset.audit.retained_rows,
        admitted_compounds=dataset.audit.admitted_compounds,
        exclusion_counts=dict(dataset.audit.exclusion_counts),
        outcome_mix=MixSummary(counts=dict(sorted(counter.items())), total=sum(counter.values())),
        relation_mix=MixSummary(
            counts=dict(sorted(relations.items())), total=sum(relations.values())
        ),
        readout_mix=MixSummary(counts=dict(sorted(readouts.items())), total=sum(readouts.values())),
        score=score_summary(dataset.rows),
        replicate_counts=MixSummary(
            counts=dict(sorted(replicates.items(), key=lambda item: item[0])),
            total=sum(replicates.values()),
        ),
        replicate_declaration=spec.replicate_declaration,
        determination_column=spec.determination_column,
        determination_kind=spec.determination_kind,
        hill_fit_mode=spec.hill_fit_mode,
        reference_audit=audit,
        curve_check=_curve_check(
            dataset, seed=seed, tolerance=CURVE_TOLERANCE_POINTS
        ),
        licensed_claims=licensed,
        unlicensed_claims=unlicensed,
        examples=_examples(dataset),
    )


def split_counts(datasets: Mapping[int, AssayDataset], *, seed: int = SPLIT_SEED) -> dict[str, int]:
    """How many admitted compounds land in each half of the declared split."""
    development = 0
    heldout = 0
    for dataset in datasets.values():
        for row in dataset.rows:
            if _split_bucket(row, seed) == 0:
                development += 1
            else:
                heldout += 1
    return {"development": development, "held_out": heldout}


def split_stability(
    datasets: Mapping[int, AssayDataset], *, seed: int = SPLIT_SEED
) -> dict[str, dict[str, object]]:
    """The cheap baseline recomputed on each half of the compound split.

    The point of this check is narrow and worth stating: the readout mix, the
    relation mix and the score distribution describe an assay, but only if
    they do not move when a different sample of compounds is used. Anything
    that moves is a property of the compound sample rather than of the assay,
    and a reader should not carry it across as an assay property.
    """
    report: dict[str, dict[str, object]] = {}
    for aid in sorted(datasets):
        dataset = datasets[aid]
        buckets: dict[int, list[MeasurementRow]] = {0: [], 1: []}
        for row in dataset.rows:
            buckets[_split_bucket(row, seed)].append(row)
        entry: dict[str, object] = {}
        for label, bucket in (("development", 0), ("held_out", 1)):
            rows = buckets[bucket]
            if not rows:
                entry[label] = {"compounds": 0}
                continue
            relations: Counter[str] = Counter()
            readouts: Counter[str] = Counter()
            for row in rows:
                relations[row.qualifier or "unstated"] += 1
                for label_name in row.endpoints:
                    readouts[label_name] += 1
            entry[label] = {
                "compounds": len(rows),
                "relation_mix": dict(sorted(relations.items())),
                "readout_mix": dict(sorted(readouts.items())),
                "score": {
                    "median": score_summary(rows).median,
                    "maximum": score_summary(rows).maximum,
                },
            }
        report[str(aid)] = entry
    return report


def conventional_percent_inhibition(signal: float, positive: float, negative: float) -> float:
    """The rearranged form of the two-reference equation, exposed for readers."""
    return percent_inhibition_conventional(signal, positive, negative)
