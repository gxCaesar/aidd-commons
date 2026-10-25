"""Constructed cases distinguish gates, preferences and absent evidence."""

from __future__ import annotations

from aidd_commons.target_product_profile.profile import evaluate_compound, judge_requirement


def test_gate_and_preference_are_judged_separately() -> None:
    requirements = [
        {
            "id": "clearance_gate",
            "kind": "gate",
            "family": "exposure",
            "selector": {"assay_system": "Human liver microsomes"},
            "comparison": "all_lte",
            "threshold": 50,
            "unit": "mL.min-1.g-1",
        },
        {
            "id": "clearance_preference",
            "kind": "preference",
            "family": "exposure",
            "selector": {"assay_system": "Human liver microsomes"},
            "comparison": "all_lte",
            "threshold": 20,
            "unit": "mL.min-1.g-1",
        },
    ]
    compound = {
        "parent_chembl_id": "CHEMBLTEST",
        "exposure": {
            "measurements": [
                {"assay_system": "Human liver microsomes", "value": 30, "unit": "mL.min-1.g-1"}
            ]
        },
    }
    evaluated = evaluate_compound(requirements, compound)
    assert evaluated["passed_gates"] == ["clearance_gate"]
    assert evaluated["failed_gates"] == []
    assert evaluated["missed_preferences"] == ["clearance_preference"]
    assert evaluated["profile_satisfying"] is True


def test_unmeasured_requirement_never_passes() -> None:
    requirement = {
        "id": "clinical_response",
        "kind": "gate",
        "family": "clinical_efficacy",
        "selector": None,
        "comparison": "all_gte",
        "threshold": 30,
        "unit": "%",
    }
    compound = {"parent_chembl_id": "CHEMBLTEST"}
    assert judge_requirement(requirement, compound) == "unmeasured"
    assert evaluate_compound([requirement], compound)["profile_satisfying"] is False


def test_incompatible_units_are_refused() -> None:
    requirement = {
        "id": "clearance",
        "kind": "gate",
        "family": "exposure",
        "selector": {"assay_system": "Human liver microsomes"},
        "comparison": "all_lte",
        "threshold": 50,
        "unit": "mL.min-1.g-1",
    }
    compound = {
        "parent_chembl_id": "CHEMBLTEST",
        "exposure": {
            "measurements": [
                {
                    "assay_system": "Human liver microsomes",
                    "value": 30,
                    "unit": "uL.min-1.(10^6cells)-1",
                }
            ]
        },
    }
    import pytest

    with pytest.raises(ValueError, match="incompatible unit"):
        judge_requirement(requirement, compound)
