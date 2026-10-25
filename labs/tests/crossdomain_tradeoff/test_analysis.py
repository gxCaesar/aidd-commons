"""The decision rule reproduces the workbook's answer and states what the data cannot."""

from __future__ import annotations

from pathlib import Path

import pytest
from aidd_commons.crossdomain_tradeoff.analysis import (
    audit_decisions,
    decide_measured,
    decide_teaching_case,
    make_decisions,
)
from aidd_commons.crossdomain_tradeoff.protocol import (
    INPUTS,
    TEACHING_CASES,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def teaching_decisions() -> list[dict]:
    return [decide_teaching_case(case) for case in TEACHING_CASES]


def test_the_teaching_cases_block_on_the_input_the_workbook_names(
    teaching_decisions: list[dict],
) -> None:
    """The computed answer is the lesson's worked answer."""
    blocked = {row["id"]: row["blocking_input"] for row in teaching_decisions}
    assert blocked == {
        "N1": "selectivity_ratio",
        "N2": "exposure_ratio",
        "N3": "safety_package",
    }


def test_no_teaching_case_completes_the_nomination(
    teaching_decisions: list[dict],
) -> None:
    """The rule's completeness gate refuses every candidate, including N3."""
    assert all(row["complete"] is False for row in teaching_decisions)
    assert sum(row["complete"] for row in teaching_decisions) == 0


def test_the_next_decision_follows_the_evidence(teaching_decisions: list[dict]) -> None:
    """A supplied input that fails points at the candidate, a missing one at the gap."""
    decisions = {row["id"]: row["next_decision"] for row in teaching_decisions}
    assert decisions == {
        "N1": "revise the candidate",
        "N2": "revise the candidate",
        "N3": "close an evidence gap",
    }


def test_the_rule_never_points_at_changing_the_requirement(
    teaching_decisions: list[dict],
) -> None:
    """Changing a threshold so that a favourite passes is not a discovery."""
    assert all(row["next_decision"] != "change the product profile" for row in teaching_decisions)


def test_a_review_available_package_is_not_a_favourable_review(
    teaching_decisions: list[dict],
) -> None:
    """An available safety package supplies the input and settles nothing else."""
    n1 = next(row for row in teaching_decisions if row["id"] == "N1")
    safety = n1["inputs"]["safety_package"]
    assert safety["state"] == "supplied"
    assert safety["value"] == "available for review"
    assert safety["note"] is not None
    assert "not a favourable review" in safety["note"]


def test_a_missing_teaching_input_carries_no_value(teaching_decisions: list[dict]) -> None:
    """A missing input is missing, not a zero."""
    n3 = next(row for row in teaching_decisions if row["id"] == "N3")
    safety = n3["inputs"]["safety_package"]
    assert safety["state"] == "absent"
    assert safety["value"] is None
    assert safety["meets_threshold"] is False


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_the_measured_cohort_supplies_at_most_one_input() -> None:
    """The families the cohort has in abundance are not the inputs the rule needs."""
    from pathlib import Path

    from aidd_commons.multi_endpoint_integration.summary import build_summary

    root = Path(__file__).resolve().parents[3]
    integration = build_summary(root / ".cache")
    teaching, measured = make_decisions(integration["profiles"], list(TEACHING_CASES))
    assert len(measured) == 58
    states: dict[str, dict[str, int]] = {}
    for decision in measured:
        for name, entry in decision["inputs"].items():
            states.setdefault(name, {})
            states[name][entry["state"]] = states[name].get(entry["state"], 0) + 1
    assert states["potency"] == {"absent": 57, "indeterminate": 1}
    for name in ("selectivity_ratio", "exposure_ratio", "safety_package", "functional_validation"):
        assert states[name] == {"not covered": 58}
    assert all(row["complete"] is False for row in measured)
    assert all(row["next_decision"] == "close an evidence gap" for row in measured)
    assert teaching


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_the_measured_decisions_name_their_inputs_in_the_rules_order() -> None:
    """Every decision reports the five inputs in the rule's order."""
    from pathlib import Path

    from aidd_commons.multi_endpoint_integration.summary import build_summary

    root = Path(__file__).resolve().parents[3]
    integration = build_summary(root / ".cache")
    _, measured = make_decisions(integration["profiles"], list(TEACHING_CASES))
    for decision in measured:
        assert tuple(decision["inputs"]) == INPUTS


def test_a_mixture_of_endpoint_types_makes_the_potency_indeterminate() -> None:
    """A representative value over mixed quantities is not the family's potency."""
    profile = {
        "parent_chembl_id": "TEST",
        "efficacy": {
            "measurements": [
                {
                    "assay_chembl_id": "CHEMBL1",
                    "document_chembl_id": "CHEMBL2",
                    "endpoint_type": "EC50",
                    "value": 7800.0,
                    "unit": "nM",
                },
                {
                    "assay_chembl_id": "CHEMBL3",
                    "document_chembl_id": "CHEMBL4",
                    "endpoint_type": "IC50",
                    "value": 5.591,
                    "unit": "nM",
                },
            ]
        },
    }
    decision = decide_measured(profile)
    potency = decision["inputs"]["potency"]
    assert potency["state"] == "indeterminate"
    assert potency["value"] is None
    assert "endpoint types" in potency["note"]


def test_a_single_endpoint_type_supplies_a_potency() -> None:
    """One endpoint type gives one potency value and a decided gate."""
    profile = {
        "parent_chembl_id": "TEST",
        "efficacy": {
            "measurements": [
                {
                    "assay_chembl_id": "CHEMBL1",
                    "document_chembl_id": "CHEMBL2",
                    "endpoint_type": "IC50",
                    "value": 40.0,
                    "unit": "nM",
                }
            ]
        },
    }
    decision = decide_measured(profile)
    potency = decision["inputs"]["potency"]
    assert potency["state"] == "supplied"
    assert potency["value"] == 40.0
    assert potency["meets_threshold"] is True
    assert decision["blocking_input"] == "selectivity_ratio"


def test_the_audit_refuses_a_decision_with_a_score(teaching_decisions: list[dict]) -> None:
    """A composite is not a decision."""
    tampered = [dict(row) for row in teaching_decisions]
    tampered[0]["score"] = 0.91
    with pytest.raises(ValueError):
        audit_decisions(tampered)


def test_the_audit_refuses_a_filled_missing_input(teaching_decisions: list[dict]) -> None:
    """A missing input cannot be filled with a default."""
    tampered = [dict(row) for row in teaching_decisions]
    inputs = dict(tampered[2]["inputs"])
    inputs["safety_package"] = dict(
        inputs["safety_package"], state="supplied", value="available for review"
    )
    tampered[2]["inputs"] = inputs
    with pytest.raises(ValueError):
        audit_decisions(tampered)
