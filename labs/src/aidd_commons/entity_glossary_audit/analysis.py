"""Audit identifiers on admitted point rows without merging entity kinds."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from aidd_commons.decision_unit_scope.data import ActivityRow, CohortDataset

from .protocol import KIND_FIELDS, UNNAMED_KINDS


class AuditError(ValueError):
    """An admitted row cannot support the declared entity reading."""


def admitted_rows(cohort: CohortDataset) -> tuple[ActivityRow, ...]:
    """Apply the sibling lab's point admission, retaining each reported row."""
    rows: list[ActivityRow] = []
    for parent_id, dataset in sorted(cohort.parents.items()):
        if dataset.parent_molecule_chembl_id != parent_id:
            raise AuditError("parent dataset key differs from its declared parent")
        for row in dataset.rows:
            if row.parent_molecule_chembl_id != parent_id:
                raise AuditError("activity row differs from its parent dataset")
            if row.classification == "point":
                rows.append(row)
    return tuple(rows)


def audit_rows(
    rows: Sequence[ActivityRow], *, declared_salts: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Count identifier values over admitted rows and independent groups."""
    if not rows:
        raise AuditError("no admitted point rows")
    salts = declared_salts or {}
    values: dict[str, set[str]] = {kind: set() for kind in KIND_FIELDS}
    groups: dict[tuple[str, str, str, str], list[ActivityRow]] = defaultdict(list)
    target_molecules: dict[str, set[str]] = defaultdict(set)
    molecule_parents: dict[str, str] = {}
    activity_ids: set[int] = set()
    child_ids: set[str] = set()
    child_rows = 0
    salt_rows = 0

    for row in rows:
        if row.classification != "point":
            raise AuditError("an audited row is not an admitted point measurement")
        if row.activity_id in activity_ids:
            raise AuditError("duplicate activity identifier")
        activity_ids.add(row.activity_id)
        for kind, field in KIND_FIELDS.items():
            identifier = getattr(row, field)
            if not isinstance(identifier, str) or not identifier.strip():
                raise AuditError(f"admitted row has no {field}")
            values[kind].add(identifier)
        assert row.target_chembl_id is not None
        old_parent = molecule_parents.setdefault(
            row.molecule_chembl_id, row.parent_molecule_chembl_id
        )
        if old_parent != row.parent_molecule_chembl_id:
            raise AuditError("one molecule identifier resolves to two parents")
        if row.is_child_form:
            child_rows += 1
            child_ids.add(row.molecule_chembl_id)
            if row.molecule_chembl_id in salts:
                salt_rows += 1
        groups[(row.parent_molecule_chembl_id, *row.grouping_key)].append(row)
        target_molecules[row.target_chembl_id].add(row.molecule_chembl_id)

    per_kind = {
        kind: {"field": field, "distinct_identifiers": len(values[kind]), "row_uses": len(rows)}
        for kind, field in KIND_FIELDS.items()
    }
    return {
        "admitted_point_row_count": len(rows),
        "admitted_measurement_count": len(groups),
        "per_kind": per_kind,
        "totals": {
            "distinct_identifiers_across_kinds": sum(len(items) for items in values.values()),
            "identifier_uses": len(rows) * len(KIND_FIELDS),
            "measurements_with_multiple_molecule_records": sum(
                len({row.molecule_chembl_id for row in members}) > 1 for members in groups.values()
            ),
        },
        "unnamed_kinds": {
            kind: {"reason": reason, "admitted_rows_without_identifier": len(rows)}
            for kind, reason in UNNAMED_KINDS.items()
        },
        "molecule_parent_disagreement": {
            "admitted_rows": child_rows,
            "distinct_molecule_records": len(child_ids),
            "molecule_record_ids": sorted(child_ids),
            "declared_salt_ids": sorted(child_ids.intersection(salts)),
            "declared_salt_rows": salt_rows,
            "other_child_ids": sorted(child_ids.difference(salts)),
        },
        "assay_target_coverage": {
            "distinct_assays": len(values["assay"]),
            "distinct_targets": len(values["target"]),
            "targets_with_multiple_molecule_records": sum(
                len(molecules) > 1 for molecules in target_molecules.values()
            ),
        },
    }


def check_invariants(result: Mapping[str, Any]) -> list[str]:
    """Check arithmetic and kind coverage without assuming a convenient result."""
    failures: list[str] = []
    rows = result["admitted_point_row_count"]
    measurements = result["admitted_measurement_count"]
    per_kind = result["per_kind"]
    totals = result["totals"]
    disagreement = result["molecule_parent_disagreement"]
    coverage = result["assay_target_coverage"]
    if rows <= 0 or not 0 < measurements <= rows:
        failures.append("admission or grouping count")
    if set(per_kind) != set(KIND_FIELDS):
        failures.append("named kind coverage")
    if set(result["unnamed_kinds"]) != set(UNNAMED_KINDS):
        failures.append("unnamed kind coverage")
    if any(
        item["row_uses"] != rows or item["distinct_identifiers"] < 1 for item in per_kind.values()
    ):
        failures.append("per-kind row use or identifier count")
    if totals["identifier_uses"] != rows * len(KIND_FIELDS) or totals[
        "distinct_identifiers_across_kinds"
    ] != sum(item["distinct_identifiers"] for item in per_kind.values()):
        failures.append("identifier totals")
    if not 0 <= disagreement["admitted_rows"] <= rows:
        failures.append("child row count")
    if disagreement["distinct_molecule_records"] != len(disagreement["molecule_record_ids"]):
        failures.append("child molecule count")
    if disagreement["declared_salt_rows"] > disagreement["admitted_rows"]:
        failures.append("declared salt row count")
    if (
        coverage["distinct_assays"] != per_kind["assay"]["distinct_identifiers"]
        or coverage["distinct_targets"] != per_kind["target"]["distinct_identifiers"]
    ):
        failures.append("assay or target coverage")
    if not 0 <= coverage["targets_with_multiple_molecule_records"] <= coverage["distinct_targets"]:
        failures.append("multi-molecule target count")
    if any(
        item["admitted_rows_without_identifier"] != rows
        for item in result["unnamed_kinds"].values()
    ):
        failures.append("unnamed kind row coverage")
    return failures
