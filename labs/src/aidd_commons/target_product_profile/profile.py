"""Judge a declared requirement against the joined, unit-labelled measurements."""

from __future__ import annotations

from typing import Any


def judge_requirement(requirement: dict[str, Any], compound: dict[str, Any]) -> str:
    """Return pass/fail for gates, met/miss for preferences, or unmeasured."""
    family = requirement["family"]
    entry = compound.get(family)
    if entry is None:
        return "unmeasured"
    selector = requirement["selector"]
    if not isinstance(selector, dict) or len(selector) != 1:
        raise ValueError(f"invalid selector for {requirement['id']}")
    key, selected_value = next(iter(selector.items()))
    rows = [row for row in entry["measurements"] if row.get(key) == selected_value]
    if not rows:
        return "unmeasured"
    if any(row["unit"] != requirement["unit"] for row in rows):
        raise ValueError(f"incompatible unit for {requirement['id']}")
    comparison = requirement["comparison"]
    if comparison == "all_lte":
        satisfied = all(row["value"] <= requirement["threshold"] for row in rows)
    elif comparison == "all_gte":
        satisfied = all(row["value"] >= requirement["threshold"] for row in rows)
    else:
        raise ValueError(f"unsupported comparison for {requirement['id']}")
    if requirement["kind"] == "gate":
        return "pass" if satisfied else "fail"
    if requirement["kind"] == "preference":
        return "met" if satisfied else "miss"
    raise ValueError(f"unsupported requirement kind for {requirement['id']}")


def evaluate_compound(
    requirements: list[dict[str, Any]], compound: dict[str, Any]
) -> dict[str, Any]:
    outcomes = {item["id"]: judge_requirement(item, compound) for item in requirements}
    gates = [item["id"] for item in requirements if item["kind"] == "gate"]
    preferences = [item["id"] for item in requirements if item["kind"] == "preference"]
    return {
        "parent_chembl_id": compound["parent_chembl_id"],
        "passed_gates": [item for item in gates if outcomes[item] == "pass"],
        "failed_gates": [item for item in gates if outcomes[item] == "fail"],
        "unmeasured_gates": [item for item in gates if outcomes[item] == "unmeasured"],
        "missed_preferences": [item for item in preferences if outcomes[item] == "miss"],
        "unmeasured_preferences": [item for item in preferences if outcomes[item] == "unmeasured"],
        "outcomes": outcomes,
        "profile_satisfying": all(outcomes[item] == "pass" for item in gates),
    }
