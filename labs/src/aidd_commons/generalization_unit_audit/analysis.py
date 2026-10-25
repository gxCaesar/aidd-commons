"""Collapse admitted rows and count measurements under candidate units."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from aidd_commons.decision_unit_scope.analysis import census_cohort
from aidd_commons.decision_unit_scope.data import ActivityRow, CohortDataset

from .protocol import CANNOT_NAME, RULE, UNITS


class AuditError(ValueError):
    """A measurement or a count violates the declared rule."""


@dataclass(frozen=True)
class Measurement:
    key: tuple[str, str, str, str]
    units: Mapping[str, frozenset[str]]


def _scaffold(smiles: str) -> str:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None or not molecule.GetNumAtoms():
        raise AuditError("an admitted structure is unreadable by RDKit")
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(  # type: ignore[no-untyped-call]
        mol=molecule, includeChirality=True
    )
    form = Chem.MolToSmiles(molecule, isomericSmiles=True)
    return scaffold or f"acyclic:{form}"


def measurements_from_cohort(cohort: CohortDataset) -> tuple[Measurement, ...]:
    grouped: dict[tuple[str, str, str, str], list[ActivityRow]] = defaultdict(list)
    for parent in cohort.parents.values():
        for row in parent.rows:
            if row.classification == "point":
                grouped[(row.parent_molecule_chembl_id, *row.grouping_key)].append(row)

    measurements: list[Measurement] = []
    for key, members in sorted(grouped.items()):
        units: dict[str, set[str]] = {name: set() for name in UNITS}
        for row in members:
            if not row.target_chembl_id:
                raise AuditError("an admitted measurement has no target identifier")
            units["molecule_record"].add(row.molecule_chembl_id)
            units["parent_molecule"].add(row.parent_molecule_chembl_id)
            units["bemis_murcko_scaffold"].add(_scaffold(row.canonical_smiles))
            units["assay"].add(row.assay_chembl_id)
            units["target"].add(row.target_chembl_id)
            units["document"].add(row.document_chembl_id)
        measurements.append(
            Measurement(key, {name: frozenset(values) for name, values in units.items()})
        )
    if len(measurements) != census_cohort(cohort).independent_measurement_count:
        raise AuditError("measurement count differs from the sibling census")
    return tuple(measurements)


def _percentile(sorted_counts: Sequence[int], fraction: float) -> float:
    position = (len(sorted_counts) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return float(
        sorted_counts[lower] + (sorted_counts[upper] - sorted_counts[lower]) * (position - lower)
    )


def audit_measurements(rows: Sequence[Measurement]) -> dict[str, Any]:
    if not rows or len({row.key for row in rows}) != len(rows):
        raise AuditError("measurement keys must be nonempty and unique")
    counts: dict[str, dict[str, Any]] = {}
    for name in UNITS:
        per_value: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
        for row in rows:
            if set(row.units) != set(UNITS) or any(not values for values in row.units.values()):
                raise AuditError("every measurement needs every candidate unit field")
            if row.units["parent_molecule"] != frozenset((row.key[0],)):
                raise AuditError("parent unit differs from measurement key")
            for value in row.units[name]:
                if not value:
                    raise AuditError("a candidate unit has an empty value")
                per_value[value].add(row.key)
        values = sorted(len(keys) for keys in per_value.values())
        counts[name] = {
            "value_count": len(values),
            "measurement_count": sum(values),
            "median_measurements_per_value": _percentile(values, 0.5),
            "q1_measurements_per_value": _percentile(values, 0.25),
            "q3_measurements_per_value": _percentile(values, 0.75),
            "single_measurement_values": values.count(1),
        }
    most = max(UNITS, key=lambda name: counts[name]["value_count"])
    fewest = min(UNITS, key=lambda name: counts[name]["value_count"])
    if most == fewest:
        raise AuditError("candidate units do not differ in value count")
    return {
        "admitted_measurement_count": len(rows),
        "units": counts,
        "units_table_cannot_name": dict(CANNOT_NAME),
        "two_unit_comparison": {
            "most_values": most,
            "fewest_values": fewest,
            "units": {most: counts[most], fewest: counts[fewest]},
        },
        "measurement_rule": dict(RULE),
    }


def check_invariants(result: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    count = result.get("admitted_measurement_count")
    units = result.get("units")
    if (
        not isinstance(count, int)
        or count <= 0
        or not isinstance(units, dict)
        or set(units) != set(UNITS)
    ):
        return ["missing measurement count or candidate units"]
    for name, item in units.items():
        if not isinstance(item, dict):
            failures.append(f"{name}: invalid unit counts")
            continue
        value_count = item.get("value_count")
        membership = item.get("measurement_count")
        singleton = item.get("single_measurement_values")
        if (
            not isinstance(value_count, int)
            or not isinstance(membership, int)
            or not isinstance(singleton, int)
        ):
            failures.append(f"{name}: missing integer counts")
            continue
        if not (
            1 <= value_count <= membership and count <= membership and 0 <= singleton <= value_count
        ):
            failures.append(f"{name}: impossible counts")
        q1 = item.get("q1_measurements_per_value")
        median = item.get("median_measurements_per_value")
        q3 = item.get("q3_measurements_per_value")
        if (
            not isinstance(q1, (int, float))
            or not isinstance(median, (int, float))
            or not isinstance(q3, (int, float))
        ):
            failures.append(f"{name}: invalid quartiles")
        elif not (1 <= q1 <= median <= q3 <= membership):
            failures.append(f"{name}: invalid quartiles")
    if result.get("units_table_cannot_name") != CANNOT_NAME:
        failures.append("missing units the table cannot name")
    if result.get("measurement_rule") != RULE:
        failures.append("changed measurement rule")
    if not failures:
        most = max(UNITS, key=lambda name: units[name]["value_count"])
        fewest = min(UNITS, key=lambda name: units[name]["value_count"])
        expected = {
            "most_values": most,
            "fewest_values": fewest,
            "units": {most: units[most], fewest: units[fewest]},
        }
        if result.get("two_unit_comparison") != expected:
            failures.append("two-unit comparison differs from declared ordering")
    return failures
