"""Constructed measurements exercise the unit and singleton rule."""

from __future__ import annotations

import pytest
from aidd_commons.generalization_unit_audit.analysis import (
    AuditError,
    Measurement,
    audit_measurements,
    check_invariants,
)
from aidd_commons.generalization_unit_audit.protocol import CANNOT_NAME, UNITS


def row(parent: str, number: int, *, molecule: str, assay: str) -> Measurement:
    key = (parent, assay, f"D{number}", "IC50")
    values = {
        "molecule_record": molecule,
        "parent_molecule": parent,
        "bemis_murcko_scaffold": f"S{parent}",
        "assay": assay,
        "target": "T1",
        "document": f"D{number}",
    }
    return Measurement(key, {name: frozenset((value,)) for name, value in values.items()})


def test_counts_and_missing_units() -> None:
    rows = (
        row("P1", 1, molecule="M1", assay="A1"),
        row("P1", 2, molecule="M1", assay="A2"),
        row("P2", 3, molecule="M2", assay="A3"),
    )
    result = audit_measurements(rows)
    assert result["admitted_measurement_count"] == 3
    assert result["units"]["parent_molecule"] == {
        "value_count": 2,
        "measurement_count": 3,
        "median_measurements_per_value": 1.5,
        "q1_measurements_per_value": 1.25,
        "q3_measurements_per_value": 1.75,
        "single_measurement_values": 1,
    }
    assert result["units"]["assay"]["single_measurement_values"] == 3
    assert result["units_table_cannot_name"] == CANNOT_NAME
    assert not check_invariants(result)


def test_one_measurement_can_carry_two_molecule_values() -> None:
    first = row("P1", 1, molecule="M1", assay="A1")
    units = dict(first.units)
    units["molecule_record"] = frozenset(("M1", "M1-salt"))
    second = row("P2", 2, molecule="M2", assay="A2")
    result = audit_measurements((Measurement(first.key, units), second))
    assert result["admitted_measurement_count"] == 2
    assert result["units"]["molecule_record"]["measurement_count"] == 3


def test_missing_candidate_value_is_refused() -> None:
    first = row("P1", 1, molecule="M1", assay="A1")
    units = dict(first.units)
    del units["document"]
    with pytest.raises(AuditError, match="every candidate unit"):
        audit_measurements((Measurement(first.key, units),))
    assert set(first.units) == set(UNITS)
