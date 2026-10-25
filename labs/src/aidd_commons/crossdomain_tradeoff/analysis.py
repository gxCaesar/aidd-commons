"""Execute the curriculum's nomination rule and report it without a score.

The rule is the candidate-nomination workbook's: five required inputs, three
teaching thresholds, and no composite. This module resolves each input for a
candidate, names the input that blocks the nomination, and reports the next
decision the evidence points to.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .protocol import (
    EXPOSURE_RATIO_MINIMUM,
    INPUT_STATES,
    INPUTS,
    POTENCY_LIMIT_NM,
    SELECTIVITY_RATIO_MINIMUM,
)

POTENCY_UNIT = "nM"

INPUT_SCOPES = {
    "potency": "Observed in vitro response potency in the named assay and document only.",
    "selectivity_ratio": "A ratio against an intended target.",
    "exposure_ratio": "An exposure compared with an effective concentration.",
    "safety_package": "An independently reviewed safety package.",
    "functional_validation": "Interpretable functional validation for the compound.",
}


def _input(
    name: str,
    state: str,
    *,
    value: float | str | None = None,
    unit: str | None = None,
    meets_threshold: bool | None = None,
    evidence_kind: str = "none",
    note: str | None = None,
) -> dict[str, Any]:
    """One required input: its state, its value and whether it meets its rule."""
    return {
        "name": name,
        "state": state,
        "value": value,
        "unit": unit,
        "meets_threshold": meets_threshold,
        "evidence_kind": evidence_kind,
        "scope": INPUT_SCOPES[name],
        "note": note,
    }


def _potency_input(profile: dict[str, Any]) -> dict[str, Any]:
    """Resolve the potency input of one measured parent."""
    family = profile.get("efficacy")
    if family is None:
        return _input(
            "potency",
            "absent",
            note="No admitted response-potency point exists for this parent.",
        )
    rows = [row for row in family["measurements"] if row.get("unit") == POTENCY_UNIT]
    if not rows:
        units = sorted({row.get("unit") for row in family["measurements"] if row.get("unit")})
        return _input(
            "potency",
            "not covered",
            unit=units[0] if units else None,
            note=(
                "The admitted potency is in "
                f"{units[0] if units else 'an unstated unit'}, which is not the gate unit."
            ),
        )
    endpoint_types = sorted({row["endpoint_type"] for row in rows})
    if len(endpoint_types) > 1:
        return _input(
            "potency",
            "indeterminate",
            unit=POTENCY_UNIT,
            evidence_kind="multi-activity median",
            note=(
                "The admitted records mix the endpoint types "
                f"{', '.join(endpoint_types)}, so no single potency value is the family's."
            ),
        )
    values = sorted(row["value"] for row in rows)
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    return _input(
        "potency",
        "supplied",
        value=median,
        unit=POTENCY_UNIT,
        meets_threshold=median <= POTENCY_LIMIT_NM,
        evidence_kind="single-activity point" if len(rows) == 1 else "multi-activity median",
    )


def _not_covered(name: str, note: str) -> dict[str, Any]:
    """An input the measured families do not cover."""
    return _input(name, "not covered", note=note)


def _measured_inputs(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Resolve the five inputs for one measured parent."""
    return {
        "potency": _potency_input(profile),
        "selectivity_ratio": _not_covered(
            "selectivity_ratio",
            "The cohort holds inhibition potency against two drug-metabolising enzymes, which "
            "is not a selectivity ratio against an intended target.",
        ),
        "exposure_ratio": _not_covered(
            "exposure_ratio",
            "The cohort holds in vitro intrinsic clearance, which is not an exposure and "
            "cannot form an exposure-to-effective-concentration ratio.",
        ),
        "safety_package": _not_covered(
            "safety_package",
            "No measured safety material exists for this cohort, and a review is a human "
            "decision that no measurement supplies.",
        ),
        "functional_validation": _not_covered(
            "functional_validation",
            "The measured assay records in this repository classify assay records rather than "
            "validate a compound's function.",
        ),
    }


def _teaching_inputs(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Resolve the five inputs for one teaching case from the workbook's table."""
    safety = case["safety_package"]
    return {
        "potency": _input(
            "potency",
            "supplied",
            value=case["potency_nm"],
            unit=POTENCY_UNIT,
            meets_threshold=case["potency_nm"] <= POTENCY_LIMIT_NM,
            evidence_kind="constructed teaching row",
        ),
        "selectivity_ratio": _input(
            "selectivity_ratio",
            "supplied",
            value=case["selectivity_ratio"],
            unit="fold",
            meets_threshold=case["selectivity_ratio"] >= SELECTIVITY_RATIO_MINIMUM,
            evidence_kind="constructed teaching row",
        ),
        "exposure_ratio": _input(
            "exposure_ratio",
            "supplied",
            value=case["exposure_ratio"],
            unit="fold",
            meets_threshold=case["exposure_ratio"] >= EXPOSURE_RATIO_MINIMUM,
            evidence_kind="constructed teaching row",
        ),
        "safety_package": _input(
            "safety_package",
            "supplied" if safety != "missing" else "absent",
            value=None if safety == "missing" else safety,
            meets_threshold=safety != "missing",
            evidence_kind="constructed teaching row",
            note=(
                None
                if safety == "missing"
                else "Available for review is not a favourable review, and the review outcome "
                "is not established here."
            ),
        ),
        "functional_validation": _input(
            "functional_validation",
            "supplied",
            value=case["functional_validation"],
            meets_threshold=case["functional_validation"] == "interpretable",
            evidence_kind="constructed teaching row",
        ),
    }


def _blocking_input(inputs: dict[str, dict[str, Any]]) -> str | None:
    """The first required input, in the rule's order, that the candidate does not meet."""
    for name in INPUTS:
        entry = inputs[name]
        if entry["state"] == "supplied" and entry["meets_threshold"]:
            continue
        return name
    return None


def _next_decision(blocking: str | None, inputs: dict[str, dict[str, Any]]) -> str | None:
    """The next decision the evidence points to for one candidate."""
    if blocking is None:
        return None
    entry = inputs[blocking]
    if entry["state"] == "supplied" and entry["meets_threshold"] is False:
        return "revise the candidate"
    return "close an evidence gap"


def _decide(identifier: str, inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Assemble one decision record from its resolved inputs."""
    blocking = _blocking_input(inputs)
    next_decision = _next_decision(blocking, inputs)
    supplied = [name for name in INPUTS if inputs[name]["state"] == "supplied"]
    return {
        "id": identifier,
        "inputs": inputs,
        "blocking_input": blocking,
        "next_decision": next_decision,
        "evidence_grade": {
            "supplied_input_count": len(supplied),
            "supplied_inputs": supplied,
            "kinds": {name: inputs[name]["evidence_kind"] for name in INPUTS},
        },
        "complete": blocking is None,
    }


def decide_teaching_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute the rule on one teaching case from the workbook's table."""
    return _decide(case["id"], _teaching_inputs(case))


def decide_measured(profile: dict[str, Any]) -> dict[str, Any]:
    """Execute the rule on one measured parent."""
    return _decide(profile["parent_chembl_id"], _measured_inputs(profile))


def make_decisions(
    profiles: list[dict[str, Any]], teaching_cases: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute the rule on the teaching cases and on the measured cohort."""
    eligible = [profile for profile in profiles if len(profile.get("present_families", [])) >= 2]
    if not eligible:
        raise ValueError("no parent has two measured endpoint families")
    teaching = [decide_teaching_case(case) for case in teaching_cases]
    measured = [decide_measured(profile) for profile in eligible]
    audit_decisions(teaching + measured)
    return teaching, measured


def audit_decisions(decisions: list[dict[str, Any]]) -> None:
    """Recompute the decision fields and refuse a filled or scored decision."""
    if not decisions or len({row["id"] for row in decisions}) != len(decisions):
        raise ValueError("decision units are missing or duplicated")
    for decision in decisions:
        if set(decision) != {
            "id",
            "inputs",
            "blocking_input",
            "next_decision",
            "evidence_grade",
            "complete",
        }:
            raise ValueError("a decision carries a field the rule does not name")
        inputs = decision["inputs"]
        if tuple(inputs) != INPUTS:
            raise ValueError("decision inputs differ from the frozen order")
        for entry in inputs.values():
            if entry["state"] not in INPUT_STATES:
                raise ValueError("input state is invalid")
            if entry["state"] == "supplied" and entry["value"] is None:
                raise ValueError("a supplied input carries no value")
            if entry["state"] != "supplied" and entry["value"] is not None:
                raise ValueError("an unsupplied input carries a value")
            if entry["state"] == "supplied" and entry["meets_threshold"] is None:
                raise ValueError("a supplied input does not state whether it meets its rule")
        blocking = _blocking_input(inputs)
        if decision["blocking_input"] != blocking:
            raise ValueError("the blocking input differs")
        if decision["next_decision"] != _next_decision(blocking, inputs):
            raise ValueError("the next decision differs")
        if decision["next_decision"] == "change the product profile":
            raise ValueError("a decision points to changing the requirement")
        if decision["complete"] is not (blocking is None):
            raise ValueError("the completeness flag differs from the inputs")
        supplied = [name for name in INPUTS if inputs[name]["state"] == "supplied"]
        if decision["evidence_grade"]["supplied_input_count"] != len(supplied):
            raise ValueError("the supplied input count differs")
        if decision["evidence_grade"]["supplied_inputs"] != supplied:
            raise ValueError("the supplied input list differs")


def blocking_input_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    """Which input blocked each decision, and how often."""
    return dict(Counter(decision["blocking_input"] or "none" for decision in decisions))


def next_decision_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    """Which next decision the evidence points to, and how often."""
    return dict(Counter(decision["next_decision"] or "none" for decision in decisions))


def input_state_counts(decisions: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """How many candidates reach each state of each required input."""
    counts: dict[str, dict[str, int]] = {}
    for decision in decisions:
        for name, entry in decision["inputs"].items():
            bucket = counts.setdefault(name, {})
            bucket[entry["state"]] = bucket.get(entry["state"], 0) + 1
    return counts
