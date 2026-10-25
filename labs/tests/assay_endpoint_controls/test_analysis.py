"""The descriptive read-out: mixes, control audit, curve check and split.

These tests build small archived records in memory, so they check the logic
of the lab without the network and without the cached archive.
"""

from __future__ import annotations

import pytest
from aidd_commons.assay_endpoint_controls.analysis import (
    AnalysisContractError,
    assay_profile,
    readout_mix,
    relation_mix,
    score_summary,
    split_counts,
    split_stability,
)
from aidd_commons.assay_endpoint_controls.data import (
    AssayDataset,
    ConcentrationPoint,
    DataAudit,
    MeasurementRow,
)
from aidd_commons.assay_endpoint_controls.protocol import ASSAYS, SPLIT_SEED


def _row(
    compound_id: str,
    *,
    qualifier: str = "=",
    endpoint: float = 1.0,
    label: str = "IC50",
    score: float | None = 90.0,
    outcome: str = "Active",
    points: tuple[tuple[float, float], ...] = ((0.1, 10.0), (1.0, 50.0), (10.0, 90.0)),
    determinations: int | None = 30,
) -> MeasurementRow:
    return MeasurementRow(
        compound_id=compound_id,
        substance_id=f"sid-{compound_id}",
        smiles="CCO",
        outcome=outcome,
        activity_score=score,
        comment="",
        qualifier=qualifier,
        endpoints={label: endpoint},
        points=tuple(
            ConcentrationPoint(concentration_um=concentration, value=value, category=None)
            for concentration, value in points
        ),
        replicate_count=determinations,
        extra_numbers={"Hill Coefficient": 1.0, "Hill S0": 0.0, "Hill Sinf": 100.0},
    )


def _dataset(spec_id: int, rows: list[MeasurementRow], protocol_text: str = "") -> AssayDataset:
    spec = ASSAYS[spec_id]
    return AssayDataset(
        spec=spec,
        name=spec.name,
        protocol_text=protocol_text,
        comment_text="",
        rows=tuple(rows),
        audit=DataAudit(
            input_rows=len(rows),
            retained_rows=len(rows),
            admitted_compounds=len({row.compound_id for row in rows}),
            exclusion_counts={},
        ),
    )


def test_the_readout_mix_counts_every_endpoint_value() -> None:
    dataset = _dataset(519, [_row("1"), _row("2")])
    # The formylpeptide receptor assay declares two endpoint columns.
    dataset = AssayDataset(
        spec=ASSAYS[519],
        name=ASSAYS[519].name,
        protocol_text="",
        comment_text="",
        rows=(
            MeasurementRow(
                compound_id="1",
                substance_id="s",
                smiles="CCO",
                outcome="Active",
                activity_score=90.0,
                comment="",
                qualifier="=",
                endpoints={"IC50": 1.0, "Ki": 2.0},
                points=(),
                replicate_count=18,
            ),
        ),
        audit=DataAudit(
            input_rows=1, retained_rows=1, admitted_compounds=1, exclusion_counts={}
        ),
    )
    mix = readout_mix({519: dataset})
    assert mix.counts == {"IC50": 1, "Ki": 1}
    assert mix.total == 2


def test_the_relation_mix_separates_the_bounds_from_the_equalities() -> None:
    dataset = _dataset(
        548,
        [_row("1", qualifier="="), _row("2", qualifier=">"), _row("3", qualifier="<")],
    )
    mix = relation_mix({548: dataset})
    assert mix.counts == {"<": 1, "=": 1, ">": 1}
    assert mix.total == 3
    assert mix.fraction(">") == pytest.approx(1 / 3)


def test_the_confidence_score_distribution_is_reported_over_the_rows() -> None:
    dataset = _dataset(548, [_row("1", score=0.0), _row("2", score=50.0), _row("3", score=100.0)])
    summary = score_summary(dataset.rows)
    assert summary.count == 3
    assert summary.minimum == 0.0
    assert summary.median == 50.0
    assert summary.maximum == 100.0
    assert summary.fraction_at_maximum == pytest.approx(1 / 3)
    assert summary.fraction_zero == pytest.approx(1 / 3)


def test_a_row_without_a_confidence_score_is_refused_by_the_summary() -> None:
    dataset = _dataset(548, [_row("1", score=None)])
    with pytest.raises(AnalysisContractError, match="confidence score"):
        score_summary(dataset.rows)


def test_the_control_audit_counts_the_reference_wells_the_protocol_names() -> None:
    protocol = (
        "S1P was used as the positive control and the plate was normalised to it."
    )
    dataset = _dataset(439, [_row("1")], protocol_text=protocol)
    profile = assay_profile(dataset, seed=SPLIT_SEED)
    audit = profile.reference_audit
    assert audit.declared_regime == "single_positive_reference"
    assert audit.references_declared == 1
    assert audit.reference_keywords == ("positive control",)
    assert "control" in audit.control_keywords
    assert audit.equation_value_at_positive_control == pytest.approx(100.0)
    assert audit.equation_value_at_negative_control == pytest.approx(0.0)


def test_the_control_audit_finds_no_reference_in_a_protocol_that_names_none() -> None:
    dataset = _dataset(691, [_row("1")], protocol_text="No reference was used here.")
    profile = assay_profile(dataset, seed=SPLIT_SEED)
    audit = profile.reference_audit
    assert audit.declared_regime == "none_declared"
    assert audit.references_declared == 0
    assert audit.control_keywords == ()
    assert audit.normalisation_equation == "not_declared"
    assert audit.equation_matches_archived_scale is None


def test_the_archived_pka_equation_is_reported_as_a_shifted_scale() -> None:
    protocol = (
        "The positive control was Staurosporine and the negative control was DMSO only. "
        "%inhibition = (test_compound - median_positive_control)"
        "/(median_positive_control - median_negative_control)*100"
    )
    points = ((0.003, 4.1), (0.682, 51.7), (60.0, 105.2))
    dataset = _dataset(548, [_row("1", points=points)], protocol_text=protocol)
    audit = assay_profile(dataset, seed=SPLIT_SEED).reference_audit
    assert audit.equation_value_at_positive_control == pytest.approx(0.0)
    assert audit.equation_value_at_negative_control == pytest.approx(-100.0)
    assert audit.equation_scale_verdict == "shifted_scale"
    assert audit.equation_matches_archived_scale is False


def test_a_two_reference_assay_reports_a_zero_to_hundred_scale() -> None:
    protocol = (
        "The positive control and the negative control were read on every plate. "
        "%Inhibition = 100 x [1 - (MFI_test - MFI_PC)/(MFI_NC - MFI_PC)]"
    )
    points = ((0.1, 4.1), (0.682, 51.7), (60.0, 100.0))
    dataset = _dataset(519, [_row("1", points=points)], protocol_text=protocol)
    audit = assay_profile(dataset, seed=SPLIT_SEED).reference_audit
    assert audit.equation_scale_verdict == "zero_to_hundred_scale"
    assert audit.equation_matches_archived_scale is True


def test_an_assay_without_a_control_licenses_no_potency_ranking() -> None:
    dataset = _dataset(691, [_row("1"), _row("2")], protocol_text="No reference was used.")
    profile = assay_profile(dataset, seed=SPLIT_SEED)
    assert profile.unlicensed_claims
    joined = " ".join(profile.unlicensed_claims)
    assert "ranking of compounds by potency" in joined
    assert profile.licensed_claims


def test_the_split_places_every_row_in_exactly_one_half() -> None:
    rows = [_row(str(index)) for index in range(20)]
    dataset = _dataset(548, rows)
    counts = split_counts({548: dataset}, seed=SPLIT_SEED)
    assert counts["development"] + counts["held_out"] == 20
    assert counts["development"] > 0
    assert counts["held_out"] > 0


def test_the_split_is_stable_under_a_change_of_row_order() -> None:
    rows = [_row(str(index)) for index in range(20)]
    forward = split_counts({548: _dataset(548, rows)}, seed=SPLIT_SEED)
    backward = split_counts({548: _dataset(548, list(reversed(rows)))}, seed=SPLIT_SEED)
    assert forward == backward


def test_the_split_stability_report_names_both_halves_for_every_assay() -> None:
    rows = [_row(str(index)) for index in range(10)]
    dataset = _dataset(548, rows)
    report = split_stability({548: dataset}, seed=SPLIT_SEED)
    assert set(report) == {"548"}
    entry = report["548"]
    assert set(entry) == {"development", "held_out"}
    for half in entry.values():
        assert "relation_mix" in half
        assert "readout_mix" in half
        assert "score" in half


def test_the_curve_check_recomputes_the_archived_parameters_when_they_are_there() -> None:
    points = ((0.1, 9.09), (1.0, 50.0), (10.0, 90.91))
    dataset = _dataset(
        548,
        [
            MeasurementRow(
                compound_id="1",
                substance_id="s",
                smiles="CCO",
                outcome="Active",
                activity_score=90.0,
                comment="",
                qualifier="=",
                endpoints={"IC50": 1.0},
                points=tuple(
                    ConcentrationPoint(concentration_um=c, value=v, category=None)
                    for c, v in points
                ),
                replicate_count=30,
                extra_numbers={
                    "Hill Coefficient": 1.0,
                    "Hill S0": 0.0,
                    "Hill Sinf": 100.0,
                },
            )
        ],
    )
    check = assay_profile(dataset, seed=SPLIT_SEED).curve_check
    assert check.mode == "recompute_from_archived_parameters"
    assert check.recomputed_curves == 1
    assert check.development.curves + check.heldout.curves == 1
    assert check.development.median_absolute_deviation == pytest.approx(0.0, abs=0.05)


def test_a_categorical_assay_has_no_curve_check() -> None:
    dataset = _dataset(691, [_row("1")])
    check = assay_profile(dataset, seed=SPLIT_SEED).curve_check
    assert check.mode == "not_applicable_categorical_readout"
    assert check.development.curves == 0
    assert check.heldout.curves == 0
