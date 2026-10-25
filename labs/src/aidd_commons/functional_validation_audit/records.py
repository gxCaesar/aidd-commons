"""Reuse the two source readers without reinterpreting their admission rules."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aidd_commons.assay_endpoint_controls.data import AssayDataset, load_cached_assays
from aidd_commons.decision_unit_scope.data import ActivityRow, load_cached_cohort


@dataclass(frozen=True)
class Tables:
    chembl_rows: tuple[ActivityRow, ...]
    pubchem_assays: dict[int, AssayDataset]


def load_tables(chembl_cache: Path, pubchem_cache: Path) -> Tables:
    """Read cached snapshots through their owners and retain admitted rows."""
    cohort = load_cached_cohort(chembl_cache)
    assays = load_cached_assays(pubchem_cache)
    rows = tuple(
        row
        for parent in cohort.parents.values()
        for row in parent.rows
        if row.classification in ("point", "bound")
    )
    if len({row.activity_id for row in rows}) != len(rows):
        raise ValueError("ChEMBL activity IDs are not unique")
    return Tables(rows, assays)
