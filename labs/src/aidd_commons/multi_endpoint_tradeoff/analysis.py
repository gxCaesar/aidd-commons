"""Summarize admitted point measurements without combining endpoint families."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Any

import numpy as np

from aidd_commons.decision_unit_scope.data import CohortDataset

from .protocol import FAMILIES, NAMED_FAMILIES, STANDARD_UNITS, TYPE_TO_FAMILY, UNMAPPED_FAMILY


@dataclass(frozen=True)
class Measurement:
    """One admitted point row, before within-key replicates are collapsed."""

    parent_id: str
    assay_id: str
    document_id: str
    standard_type: str
    value: float
    unit: str = STANDARD_UNITS

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.parent_id, self.assay_id, self.document_id, self.standard_type)


def family_for_type(standard_type: str) -> str:
    """Map by declared standard type only; retain every unrecognized type."""
    return TYPE_TO_FAMILY.get(standard_type, UNMAPPED_FAMILY)


def admitted_measurements(cohort: CohortDataset) -> tuple[Measurement, ...]:
    """Apply the sibling laboratory's frozen admission rule to its parsed rows."""
    return tuple(
        Measurement(
            parent_id=parent_id,
            assay_id=row.assay_chembl_id,
            document_id=row.document_chembl_id,
            standard_type=row.standard_type or "",
            value=float(row.standard_value),
            unit=row.standard_units or "",
        )
        for parent_id, dataset in sorted(cohort.parents.items())
        for row in dataset.rows
        if row.classification == "point" and row.standard_value is not None
    )


def independent_measurements(rows: tuple[Measurement, ...]) -> tuple[Measurement, ...]:
    """Represent repeated rows of one assay/document/type by their median."""
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        if row.unit != STANDARD_UNITS:
            raise ValueError(f"unexpected unit for {row.key}: {row.unit}")
        grouped[row.key].append(row.value)
    return tuple(
        Measurement(*key, float(median(values))) for key, values in sorted(grouped.items())
    )


def value_summary(rows: tuple[Measurement, ...]) -> dict[str, Any]:
    """State a value only alongside its independent count, spread and unit."""
    values = [row.value for row in rows]
    centre: float | None
    lower: float | None
    upper: float | None
    if values:
        q1, q3 = np.quantile(values, [0.25, 0.75], method="linear")
        centre = float(median(values))
        lower, upper = float(q1), float(q3)
    else:
        centre = lower = upper = None
    return {
        "independent_measurement_count": len(rows),
        "distinct_document_count": len({row.document_id for row in rows}),
        "distinct_assay_count": len({row.assay_id for row in rows}),
        "median": centre,
        "q1": lower,
        "q3": upper,
        "interquartile_range": upper - lower if upper is not None and lower is not None else None,
        "unit": STANDARD_UNITS,
    }


def analyse(rows: tuple[Measurement, ...], parent_names: dict[str, str]) -> dict[str, Any]:
    """Build a parallel family table and a complete parent-by-family matrix."""
    independent = independent_measurements(rows)
    unknown_parents = {row.parent_id for row in independent} - parent_names.keys()
    if unknown_parents:
        raise ValueError(f"measurements for undeclared parents: {sorted(unknown_parents)}")
    families: dict[str, dict[str, Any]] = {}
    for family in FAMILIES:
        selected = tuple(row for row in independent if family_for_type(row.standard_type) == family)
        families[family] = {
            **value_summary(selected),
            "compounds_without_measurement_count": len(parent_names)
            - len({row.parent_id for row in selected}),
        }

    compounds: list[dict[str, Any]] = []
    empty: list[dict[str, Any]] = []
    for parent_id, name in sorted(parent_names.items()):
        selected = tuple(row for row in independent if row.parent_id == parent_id)
        by_family = {
            family: value_summary(
                tuple(row for row in selected if family_for_type(row.standard_type) == family)
            )
            for family in FAMILIES
        }
        present = [
            family
            for family in NAMED_FAMILIES
            if by_family[family]["independent_measurement_count"] > 0
        ]
        missing = [family for family in NAMED_FAMILIES if family not in present]
        compounds.append(
            {
                "parent_molecule_chembl_id": parent_id,
                "pref_name": name,
                "families": by_family,
                "present_named_families": present,
                "missing_named_families": missing,
            }
        )
        if missing:
            empty.append(
                {
                    "parent_molecule_chembl_id": parent_id,
                    "pref_name": name,
                    "missing_families": missing,
                    "present_named_family_count": len(present),
                }
            )
    return {
        "admitted_measurement_count": len(independent),
        "families": families,
        "per_compound_coverage": compounds,
        "compounds_with_empty_family": empty,
    }
