"""Classify paired and fixed-mismatch L1000 correlations without target claims."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from aidd_commons.l1000_perturbation_context.analysis import (
    CompoundSignaturePair,
    matched_pairs,
    null_pairs,
    shared_compounds,
)
from aidd_commons.l1000_perturbation_context.data import CellLineDataset
from aidd_commons.l1000_perturbation_context.protocol import NULL_ROTATION

from .protocol import INFORMATIVE_RHO_MINIMUM


class AuditError(ValueError):
    """A verdict or source pairing violates the declared comparison."""


@dataclass(frozen=True)
class Verdict:
    pert_id: str
    pert_iname: str
    matched_rho: float
    mismatched_rho: float
    verdict: str
    reason: str


def decide(matched_rho: float, mismatched_rho: float) -> tuple[str, str]:
    """Return a pattern verdict, never a molecular-mechanism assertion."""
    if not all(
        math.isfinite(value) and -1 <= value <= 1 for value in (matched_rho, mismatched_rho)
    ):
        raise AuditError("correlations must be finite and within [-1, 1]")
    if matched_rho < INFORMATIVE_RHO_MINIMUM:
        return "undecided", "low_matched_correlation"
    if mismatched_rho > matched_rho:
        return "generic_stress", "mismatch_exceeds_match"
    if mismatched_rho >= INFORMATIVE_RHO_MINIMUM:
        return "undecided", "informative_mismatched_control"
    return "mediator_specific", "match_without_informative_control"


def classify_pairs(
    matched: tuple[CompoundSignaturePair, ...], mismatched: tuple[CompoundSignaturePair, ...]
) -> tuple[Verdict, ...]:
    if not matched or len(matched) != len(mismatched):
        raise AuditError("matched and mismatched cohorts must have equal, nonzero length")
    ids = [pair.pert_id for pair in matched]
    if ids != sorted(set(ids)):
        raise AuditError("matched compound IDs must be unique and sorted")
    verdicts = []
    for index, (own, control) in enumerate(zip(matched, mismatched, strict=True)):
        if not control.pert_id.startswith(f"{own.pert_id}~"):
            raise AuditError("mismatched control does not belong to the compound")
        control_id = control.pert_id.split("~", 1)[1]
        if control_id != ids[(index + NULL_ROTATION) % len(ids)]:
            raise AuditError("mismatched control differs from the frozen rotation")
        verdict, reason = decide(own.spearman_rho, control.spearman_rho)
        verdicts.append(
            Verdict(
                own.pert_id,
                own.pert_iname,
                own.spearman_rho,
                control.spearman_rho,
                verdict,
                reason,
            )
        )
    return tuple(verdicts)


def audit_verdicts(verdicts: tuple[Verdict, ...]) -> list[str]:
    failures = []
    ids = [row.pert_id for row in verdicts]
    if not ids or ids != sorted(set(ids)):
        failures.append("verdict IDs must be nonempty, unique and sorted")
    for row in verdicts:
        try:
            expected = decide(row.matched_rho, row.mismatched_rho)
        except AuditError as error:
            failures.append(f"{row.pert_id}: {error}")
            continue
        if (row.verdict, row.reason) != expected:
            failures.append(f"{row.pert_id}: verdict violates the frozen decision rule")
    return failures


def analyse(datasets: dict[str, CellLineDataset]) -> tuple[tuple[Verdict, ...], dict[str, int]]:
    a, b = datasets["MCF7"], datasets["PC3"]
    shared = shared_compounds(a, b)
    verdicts = classify_pairs(matched_pairs(a, b), null_pairs(a, b))
    failures = audit_verdicts(verdicts)
    if failures:
        raise AuditError("; ".join(failures))
    if len(verdicts) != len(shared):
        raise AuditError("a shared compound lacks a verdict")
    return verdicts, {
        "admitted_mcf7": len(a.signatures),
        "admitted_pc3": len(b.signatures),
        "admitted_union": len(set(a.signatures) | set(b.signatures)),
        "shared_testable": len(shared),
        "mcf7_only": len(set(a.signatures) - set(b.signatures)),
        "pc3_only": len(set(b.signatures) - set(a.signatures)),
    }


def counts(verdicts: tuple[Verdict, ...]) -> dict[str, int]:
    failures = audit_verdicts(verdicts)
    if failures:
        raise AuditError("; ".join(failures))
    raw = Counter(row.verdict for row in verdicts)
    reasons = Counter(row.reason for row in verdicts)
    return {
        "mediator_specific": raw["mediator_specific"],
        "generic_stress": raw["generic_stress"],
        "undecided": raw["undecided"],
        "low_matched_correlation": reasons["low_matched_correlation"],
        "informative_mismatched_control": reasons["informative_mismatched_control"],
    }


def counterevidence_counts(verdicts: tuple[Verdict, ...]) -> dict[str, int]:
    failures = audit_verdicts(verdicts)
    if failures:
        raise AuditError("; ".join(failures))
    exceeds = [row for row in verdicts if row.mismatched_rho > row.matched_rho]
    low = sum(row.matched_rho < INFORMATIVE_RHO_MINIMUM for row in exceeds)
    return {
        "mismatch_exceeds_match_total": len(exceeds),
        "mismatch_exceeds_match_low_matched": low,
        "mismatch_exceeds_match_informative": len(exceeds) - low,
    }
