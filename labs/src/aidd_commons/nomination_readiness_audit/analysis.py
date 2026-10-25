"""Apply a declared readiness rule to independent measurement counts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aidd_commons.decision_unit_scope.analysis import CohortCensus

from .protocol import MEASUREMENT_FIELDS, THRESHOLDS


class AuditError(ValueError):
    """An input or computed readiness table breaks its contract."""


def classify_counts(counts: Mapping[str, int]) -> tuple[str, list[dict[str, Any]]]:
    """Return the state and every measurement deficit for one parent."""
    if set(counts) != set(THRESHOLDS) or any(
        type(value) is not int or value < 0 for value in counts.values()
    ):
        raise AuditError("readiness counts must be non-negative integers for all conditions")
    missing = [
        {
            "condition": metric,
            "additional_count_needed": minimum - counts[metric],
            "record_kind": "admitted ChEMBL activity point record",
            "fields": MEASUREMENT_FIELDS[metric],
        }
        for metric, minimum in THRESHOLDS.items()
        if counts[metric] < minimum
    ]
    met = len(THRESHOLDS) - len(missing)
    state = "go" if met == 3 else "stop" if met == 0 else "hold"
    return state, missing


def analyze(census: CohortCensus) -> dict[str, Any]:
    """Project the decision-unit census onto the readiness conditions."""
    parents: list[dict[str, Any]] = []
    for parent in census.parents:
        counts = {
            "independent_measurements": parent.independent_measurement_count,
            "distinct_assays": parent.distinct_assay_count,
            "distinct_documents": parent.distinct_document_count,
        }
        state, missing = classify_counts(counts)
        parents.append(
            {
                "parent_molecule_chembl_id": parent.parent_molecule_chembl_id,
                "pref_name": parent.pref_name,
                **counts,
                "state": state,
                "missing_measurements": missing,
            }
        )
    parents.sort(key=lambda row: row["parent_molecule_chembl_id"])
    state_members = {
        state: [row["parent_molecule_chembl_id"] for row in parents if row["state"] == state]
        for state in ("go", "hold", "stop")
    }
    non_go = [row for row in parents if row["state"] != "go"]
    closest = min(non_go, key=_distance_to_go) if non_go else None
    result = {
        "cohort_size": len(parents),
        "admitted_measurement_count": census.independent_measurement_count,
        "thresholds": dict(THRESHOLDS),
        "state_counts": {state: len(members) for state, members in state_members.items()},
        "state_members": state_members,
        "parents": parents,
        "closest_to_go": (
            {
                "parent_molecule_chembl_id": closest["parent_molecule_chembl_id"],
                "pref_name": closest["pref_name"],
                "failed_conditions": closest["missing_measurements"],
            }
            if closest is not None
            else None
        ),
    }
    failures = check_invariants(result)
    if failures:
        raise AuditError("; ".join(failures))
    return result


def _distance_to_go(row: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        len(row["missing_measurements"]),
        sum(item["additional_count_needed"] for item in row["missing_measurements"]),
        row["parent_molecule_chembl_id"],
    )


def check_invariants(result: Mapping[str, Any]) -> list[str]:
    """Recompute table totals and states from the three frozen minima."""
    failures: list[str] = []
    rows = result.get("parents")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return ["parent table is not a list of records"]
    ids = [row.get("parent_molecule_chembl_id") for row in rows]
    if len(ids) != len(set(ids)):
        failures.append("parent identifiers repeat")
    if result.get("cohort_size") != len(rows):
        failures.append("cohort size differs from table length")
    if result.get("thresholds") != THRESHOLDS:
        failures.append("thresholds differ from the frozen rule")
    if result.get("admitted_measurement_count") != sum(
        row.get("independent_measurements", 0) for row in rows
    ):
        failures.append("admitted count differs from parent sum")
    expected_members: dict[str, list[str]] = {state: [] for state in ("go", "hold", "stop")}
    for row in rows:
        counts = {metric: row.get(metric) for metric in THRESHOLDS}
        try:
            state, missing = classify_counts(counts)
        except AuditError:
            failures.append(f"invalid counts for {row.get('parent_molecule_chembl_id')}")
            continue
        if row.get("state") != state or row.get("missing_measurements") != missing:
            failures.append(f"wrong state or deficit for {row.get('parent_molecule_chembl_id')}")
        expected_members[state].append(row["parent_molecule_chembl_id"])
    if result.get("state_members") != expected_members:
        failures.append("state member lists differ from parent table")
    if result.get("state_counts") != {
        state: len(members) for state, members in expected_members.items()
    }:
        failures.append("state counts differ from member lists")
    non_go = [row for row in rows if row.get("state") != "go"]
    if non_go and all(isinstance(row.get("missing_measurements"), list) for row in non_go):
        closest = min(non_go, key=_distance_to_go)
        expected_closest = {
            "parent_molecule_chembl_id": closest["parent_molecule_chembl_id"],
            "pref_name": closest["pref_name"],
            "failed_conditions": closest["missing_measurements"],
        }
    else:
        expected_closest = None
    if result.get("closest_to_go") != expected_closest:
        failures.append("closest non-go parent differs from the declared tie rule")
    return failures
