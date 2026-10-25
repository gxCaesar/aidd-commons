"""The two existing readers own admission and reject absent records."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from aidd_commons.assay_endpoint_controls.data import (
    AssayDataset,
    ConcentrationPoint,
    DataAudit,
    MeasurementRow,
)
from aidd_commons.assay_endpoint_controls.protocol import ASSAYS
from aidd_commons.decision_unit_scope.data import DataContractError, normalise_activity_row
from aidd_commons.functional_validation_audit import records
from aidd_commons.functional_validation_audit.analysis import AuditError, pubchem_record


def activity(relation: str = "="):
    return normalise_activity_row(
        {
            "activity_id": 1,
            "assay_chembl_id": "CHEMBL-A",
            "document_chembl_id": "CHEMBL-D",
            "molecule_chembl_id": "CHEMBL-M",
            "parent_molecule_chembl_id": "CHEMBL-M",
            "canonical_smiles": "CCO",
            "standard_type": "Kd",
            "standard_relation": relation,
            "standard_value": 12.0,
            "standard_units": "nM",
            "standard_flag": 1,
            "potential_duplicate": 0,
            "assay_type": "B",
        }
    )


def assay_row(*, label: str = "IC50") -> MeasurementRow:
    return MeasurementRow(
        compound_id="7",
        substance_id="8",
        smiles="CCO",
        outcome="Active",
        activity_score=70.0,
        comment="",
        qualifier="=",
        endpoints={label: 1.0},
        points=tuple(ConcentrationPoint(float(i), float(i), None) for i in range(1, 6)),
        replicate_count=None,
    )


def assay_dataset(row: MeasurementRow) -> AssayDataset:
    return AssayDataset(
        ASSAYS[548],
        "assay",
        "The archived response is inhibition.",
        "",
        (row,),
        DataAudit(1, 1, 1, {}),
    )


def test_both_source_readers_are_called_and_source_admission_is_reused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, Path]] = []
    admitted = activity()
    excluded = normalise_activity_row(
        {
            **{
                "activity_id": 2,
                "assay_chembl_id": "CHEMBL-A",
                "document_chembl_id": "CHEMBL-D",
                "molecule_chembl_id": "CHEMBL-M",
                "parent_molecule_chembl_id": "CHEMBL-M",
                "canonical_smiles": "CCO",
                "standard_type": "Kd",
                "standard_relation": "=",
                "standard_value": 12.0,
                "standard_units": "nM",
                "standard_flag": 0,
                "potential_duplicate": 0,
            }
        }
    )

    def read_chembl(path: Path) -> SimpleNamespace:
        calls.append(("chembl", path))
        return SimpleNamespace(parents={"P": SimpleNamespace(rows=(admitted, excluded))})

    def read_pubchem(path: Path) -> dict[int, AssayDataset]:
        calls.append(("pubchem", path))
        return {548: assay_dataset(assay_row())}

    monkeypatch.setattr(records, "load_cached_cohort", read_chembl)
    monkeypatch.setattr(records, "load_cached_assays", read_pubchem)
    tables = records.load_tables(tmp_path / "c", tmp_path / "p")
    assert calls == [("chembl", tmp_path / "c"), ("pubchem", tmp_path / "p")]
    assert tables.chembl_rows == (admitted,)
    assert list(tables.pubchem_assays) == [548]


def test_a_missing_snapshot_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DataContractError, match="not present"):
        records.load_tables(tmp_path / "absent", tmp_path / "absent")


def test_an_endpoint_not_in_the_declared_assay_is_refused() -> None:
    row = assay_row(label="invented")
    with pytest.raises(AuditError, match="declared endpoint"):
        pubchem_record(assay_dataset(row), row)
