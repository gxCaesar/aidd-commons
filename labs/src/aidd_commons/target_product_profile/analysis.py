"""Apply the frozen profile to the existing multi-endpoint parent join."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .profile import evaluate_compound


def apply_profile(
    requirements: list[dict[str, Any]], joined_profiles: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Count parent-level contradictions without collapsing units or preferences."""
    evaluations = [evaluate_compound(requirements, profile) for profile in joined_profiles]
    if len({row["parent_chembl_id"] for row in evaluations}) != len(evaluations):
        raise ValueError("joined parent identifiers are duplicated")
    gate_counts: dict[str, dict[str, Any]] = {}
    preference_counts: dict[str, dict[str, int]] = {}
    for requirement in requirements:
        identifier = requirement["id"]
        outcomes = Counter(row["outcomes"][identifier] for row in evaluations)
        if requirement["kind"] == "gate":
            gate_counts[identifier] = {
                "pass": outcomes["pass"],
                "fail": outcomes["fail"],
                "unmeasured": outcomes["unmeasured"],
                "failing_parent_ids": [
                    row["parent_chembl_id"]
                    for row in evaluations
                    if row["outcomes"][identifier] == "fail"
                ],
            }
        else:
            preference_counts[identifier] = {
                "met": outcomes["met"],
                "miss": outcomes["miss"],
                "unmeasured": outcomes["unmeasured"],
            }
    failed = [row for row in evaluations if row["failed_gates"]]
    satisfying = [row["parent_chembl_id"] for row in evaluations if row["profile_satisfying"]]
    result = {
        "counts": {
            "cohort_compound_count": len(evaluations),
            "contradicted_compound_count": len(failed),
            "no_observed_gate_failure_count": len(evaluations) - len(failed),
            "profile_satisfying_compound_count": len(satisfying),
        },
        "per_gate": gate_counts,
        "per_preference": preference_counts,
        "unmeasured_requirements": [
            requirement["id"]
            for requirement in requirements
            if all(row["outcomes"][requirement["id"]] == "unmeasured" for row in evaluations)
        ],
        "satisfying_parent_ids": satisfying,
        "no_contradictions_note": (
            "No measured parent contradicts a mandatory gate. This profile has no observed "
            "discriminating failure in this cohort."
            if not failed
            else None
        ),
    }
    return evaluations, result
