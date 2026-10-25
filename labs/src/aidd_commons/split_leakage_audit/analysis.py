"""Measure shared groups in deterministic splits of independent measurements."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from aidd_commons.decision_unit_scope.analysis import census_cohort
from aidd_commons.decision_unit_scope.data import ActivityRow, CohortDataset

from .protocol import ROUTES, SEED, TRAIN_FRACTION, UNTESTABLE


class AuditError(ValueError):
    """The measurement or split is inconsistent with the frozen contract."""


@dataclass(frozen=True)
class AuditRow:
    """One independent measurement, possibly reported by several activity rows."""

    key: tuple[str, str, str, str]
    groups: Mapping[str, frozenset[str]]


def _structure_keys(smiles: str) -> tuple[str, str]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or not mol.GetNumAtoms():
        raise AuditError("an admitted structure is unreadable by RDKit")
    form = Chem.MolToSmiles(mol, isomericSmiles=True)
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(  # type: ignore[no-untyped-call]
        mol=mol, includeChirality=True
    )
    return (scaffold or f"acyclic:{form}", form)


def measurements_from_cohort(cohort: CohortDataset) -> tuple[AuditRow, ...]:
    """Collapse point rows using the sibling lab's independent measurement key.

    A repeated assay/document/endpoint may contain two tested forms. Both
    forms remain in that measurement's route group set.
    """
    grouped: dict[tuple[str, str, str, str], list[ActivityRow]] = defaultdict(list)
    for parent in cohort.parents.values():
        for row in parent.rows:
            if row.classification == "point":
                grouped[(row.parent_molecule_chembl_id, *row.grouping_key)].append(row)

    rows: list[AuditRow] = []
    for key, members in sorted(grouped.items()):
        groups: dict[str, set[str]] = {route: set() for route in ROUTES}
        for member in members:
            if not member.target_chembl_id:
                raise AuditError("an admitted measurement has no target identifier")
            scaffold, form = _structure_keys(member.canonical_smiles)
            groups["parent"].add(member.parent_molecule_chembl_id)
            groups["scaffold"].add(scaffold)
            groups["assay"].add(member.assay_chembl_id)
            groups["target"].add(member.target_chembl_id)
            groups["standard_form"].add(form)
        rows.append(AuditRow(key, {name: frozenset(values) for name, values in groups.items()}))

    census = census_cohort(cohort)
    if len(rows) != census.independent_measurement_count:
        raise AuditError("the independent measurement count differs from the sibling census")
    return tuple(rows)


def audit_rows(
    rows: Sequence[AuditRow], *, seed: int = SEED, train_fraction: float = TRAIN_FRACTION
) -> dict[str, object]:
    """Count overlap for each route without fitting or selecting a model."""
    if not rows or not 0 < train_fraction < 1:
        raise AuditError("the split needs rows and a fraction strictly between zero and one")
    if len({row.key for row in rows}) != len(rows):
        raise AuditError("measurement keys must be unique")
    for row in rows:
        if set(row.groups) != set(ROUTES) or any(not row.groups[name] for name in ROUTES):
            raise AuditError("every measurement needs every tested route field")
        if row.groups["parent"] != frozenset((row.key[0],)):
            raise AuditError("the parent route differs from the measurement key")

    ordered = sorted(rows, key=lambda row: row.key)
    shuffled = ordered.copy()
    random.Random(seed).shuffle(shuffled)
    train_size = math.floor(train_fraction * len(shuffled))
    if not 0 < train_size < len(shuffled):
        raise AuditError("the row split has an empty partition")
    train = shuffled[:train_size]
    test = shuffled[train_size:]

    route_counts: dict[str, dict[str, int]] = {}
    contaminated: set[tuple[str, str, str, str]] = set()
    for name in ROUTES:
        train_groups = set().union(*(row.groups[name] for row in train))
        test_groups = set().union(*(row.groups[name] for row in test))
        shared = train_groups & test_groups
        affected = [row for row in test if row.groups[name] & shared]
        held_out = [row for row in train if row.groups[name] & test_groups]
        contaminated.update(row.key for row in affected)
        route_counts[name] = {
            "test_rows_with_train_group": len(affected),
            "shared_groups": len(shared),
            "train_rows_to_hold_out": len(held_out),
        }

    parents = sorted({row.key[0] for row in ordered})
    random.Random(seed).shuffle(parents)
    train_parent_count = math.floor(train_fraction * len(parents))
    if not 0 < train_parent_count < len(parents):
        raise AuditError("the parent split has an empty partition")
    train_parents = set(parents[:train_parent_count])
    grouped_train = [row for row in ordered if row.key[0] in train_parents]
    grouped_test = [row for row in ordered if row.key[0] not in train_parents]
    highest = max(ROUTES, key=lambda name: route_counts[name]["test_rows_with_train_group"])
    return {
        "admitted_measurement_count": len(rows),
        "row_split": {"seed": seed, "train_rows": len(train), "test_rows": len(test)},
        "grouped_parent_split": {
            "train_rows": len(grouped_train),
            "test_rows": len(grouped_test),
            "unseen_parent_test_rows": len(grouped_test),
        },
        "routes": route_counts,
        "untestable_routes": dict(UNTESTABLE),
        "aggregate": {
            "contaminated_test_rows": len(contaminated),
            "contributing_routes": sum(
                counts["test_rows_with_train_group"] > 0 for counts in route_counts.values()
            ),
        },
        "highest_overlap_route": highest,
    }
