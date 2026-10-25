"""Constructed rows make the field-to-claim rule inspectable."""

from __future__ import annotations

from dataclasses import replace

import pytest
from aidd_commons.assay_endpoint_controls.data import AssayDataset, DataAudit
from aidd_commons.assay_endpoint_controls.protocol import ASSAYS
from aidd_commons.functional_validation_audit.analysis import (
    AuditError,
    AuditRecord,
    audit_records,
    audit_tables,
    chembl_record,
    pubchem_record,
)
from aidd_commons.functional_validation_audit.records import Tables

from .test_records import activity, assay_dataset, assay_row


def test_point_bound_response_and_unlicensed_records() -> None:
    point = chembl_record(activity())
    bound = chembl_record(replace(activity(), activity_id=2, standard_relation=">"))
    response_row = assay_row()
    response = pubchem_record(assay_dataset(response_row), response_row)
    none_row = replace(assay_row(label="MIC"), qualifier="", points=())
    none_assay = AssayDataset(
        ASSAYS[691], "assay", "Categorical outcome.", "", (none_row,), DataAudit(1, 1, 1, {})
    )
    none = pubchem_record(none_assay, none_row)
    result = audit_records((point, bound, response, none))
    assert result["tables"]["chembl37"]["kind_counts"] == {
        "point_measurement": 1,
        "bound": 1,
        "concentration_response_table": 0,
        "no_licensed_claim": 0,
    }
    assert result["tables"]["pubchem_bioassay"]["kind_counts"] == {
        "point_measurement": 0,
        "bound": 0,
        "concentration_response_table": 1,
        "no_licensed_claim": 1,
    }
    assert result["records_licensing_no_claim"] == 1
    assert result["licensed_claim_counts"]["clinical_outcome"] == 0
    assert "clinical_outcome" in result["unmeasurable_routes"]
    assert point.licensed_claims == ("endpoint_point", "binding_point")
    assert bound.licensed_claims == ("endpoint_bound", "binding_bound")


def test_per_assay_endpoints_and_qualifiers_count_values_and_rows_separately() -> None:
    first = assay_row()
    second = replace(first, compound_id="9", qualifier=">", endpoints={"IC50": 2.0})
    dataset = replace(assay_dataset(first), rows=(first, second), audit=DataAudit(2, 2, 2, {}))
    result = audit_tables(Tables((activity(),), {548: dataset}))
    assay = result["pubchem_assays"]["548"]
    assert assay["endpoint_counts"]["IC50"] == 2
    assert assay["qualifier_row_counts"] == {"=": 1, ">": 1}
    assert assay["stated_qualifier_values"] == 2
    assert assay["equality_values"] == 1
    assert assay["bound_values"] == 1


@pytest.mark.parametrize(
    "record",
    [
        AuditRecord("x", "chembl37", "point_measurement", ("clinical_outcome",)),
        AuditRecord("x", "pubchem_bioassay", "no_licensed_claim", ("endpoint_point",)),
        AuditRecord("x", "chembl37", "point_measurement", ("functional_response",)),
        AuditRecord("x", "chembl37", "point_measurement", ("endpoint_bound",)),
        AuditRecord("x", "pubchem_bioassay", "bound", ("endpoint_bound", "binding_bound")),
    ],
)
def test_claim_promotion_is_refused(record: AuditRecord) -> None:
    with pytest.raises(AuditError):
        audit_records((record,))
