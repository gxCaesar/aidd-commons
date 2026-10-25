"""The constructed contrast reaches support, counterevidence and both undecided reasons."""

import pytest
from aidd_commons.l1000_perturbation_context.analysis import CompoundSignaturePair
from aidd_commons.mechanism_consistency.analysis import (
    AuditError,
    audit_verdicts,
    classify_pairs,
    counterevidence_counts,
    counts,
    decide,
)


def pair(pert_id: str, rho: float) -> CompoundSignaturePair:
    return CompoundSignaturePair(pert_id, pert_id, rho)


def test_constructed_compounds_and_reasons():
    matched = tuple(
        pair(name, rho)
        for name, rho in (("A", 0.6), ("B", 0.4), ("C", 0.6), ("D", 0.09), ("E", 0.6))
    )
    mismatched = tuple(
        pair(name, rho)
        for name, rho in (("A~B", 0.05), ("B~C", 0.55), ("C~D", 0.6), ("D~E", 0.8), ("E~A", 0.2))
    )
    verdicts = classify_pairs(matched, mismatched)
    assert [(row.verdict, row.reason) for row in verdicts] == [
        ("mediator_specific", "match_without_informative_control"),
        ("generic_stress", "mismatch_exceeds_match"),
        ("undecided", "informative_mismatched_control"),
        ("undecided", "low_matched_correlation"),
        ("undecided", "informative_mismatched_control"),
    ]
    assert counts(verdicts) == {
        "mediator_specific": 1,
        "generic_stress": 1,
        "undecided": 3,
        "low_matched_correlation": 1,
        "informative_mismatched_control": 2,
    }
    assert audit_verdicts(verdicts) == []
    assert counterevidence_counts(verdicts) == {
        "mismatch_exceeds_match_total": 2,
        "mismatch_exceeds_match_low_matched": 1,
        "mismatch_exceeds_match_informative": 1,
    }


def test_informative_boundary_and_invalid_rho():
    assert decide(0.1, 0.09)[0] == "mediator_specific"
    assert decide(0.099999, -0.2)[0] == "undecided"
    assert decide(0.2, 0.2)[0] == "undecided"
    assert decide(0.2, 0.21)[0] == "generic_stress"
    with pytest.raises(AuditError):
        decide(float("nan"), 0.0)


def test_wrong_rotation_refused():
    matched = (pair("A", 0.5), pair("B", 0.4))
    mismatched = (pair("A~A", 0.0), pair("B~A", 0.0))
    with pytest.raises(AuditError, match="rotation"):
        classify_pairs(matched, mismatched)
