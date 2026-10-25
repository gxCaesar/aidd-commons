"""Small constructed rows expose the difference between entity kinds."""

from dataclasses import replace

from aidd_commons.decision_unit_scope.data import ActivityRow
from aidd_commons.entity_glossary_audit.analysis import audit_rows, check_invariants


def point_row(activity_id: int = 1) -> ActivityRow:
    return ActivityRow(
        activity_id=activity_id,
        assay_chembl_id="CHEMBL_A1",
        document_chembl_id="CHEMBL_D1",
        document_journal=None,
        document_year=None,
        molecule_chembl_id="CHEMBL1",
        parent_molecule_chembl_id="CHEMBL1",
        canonical_smiles="CC",
        standard_type="IC50",
        standard_relation="=",
        standard_value=10.0,
        standard_units="nM",
        standard_flag=1,
        potential_duplicate=0,
        data_validity_comment=None,
        pchembl_value=None,
        assay_type=None,
        target_chembl_id="CHEMBL_T1",
        target_organism=None,
        target_pref_name=None,
        toid=None,
    )


def test_entity_kinds_disagreement_and_target_coverage() -> None:
    first = point_row()
    child = replace(first, activity_id=2, molecule_chembl_id="CHEMBL2")
    second_assay = replace(
        first,
        activity_id=3,
        assay_chembl_id="CHEMBL_A2",
        document_chembl_id="CHEMBL_D2",
        target_chembl_id="CHEMBL_T2",
    )
    next_parent = replace(
        first,
        activity_id=4,
        molecule_chembl_id="CHEMBL3",
        parent_molecule_chembl_id="CHEMBL3",
        assay_chembl_id="CHEMBL_A3",
        document_chembl_id="CHEMBL_D3",
    )
    result = audit_rows(
        (first, child, second_assay, next_parent), declared_salts={"CHEMBL2": "CHEMBL1"}
    )
    assert check_invariants(result) == []
    assert result["admitted_measurement_count"] == 3
    assert result["per_kind"]["molecule_record"]["distinct_identifiers"] == 3
    assert result["per_kind"]["parent_molecule"]["distinct_identifiers"] == 2
    assert result["per_kind"]["assay"]["distinct_identifiers"] == 3
    assert result["per_kind"]["target"]["distinct_identifiers"] == 2
    assert result["per_kind"]["document"]["distinct_identifiers"] == 3
    assert result["molecule_parent_disagreement"]["admitted_rows"] == 1
    assert result["molecule_parent_disagreement"]["declared_salt_ids"] == ["CHEMBL2"]
    assert result["assay_target_coverage"]["targets_with_multiple_molecule_records"] == 1
    assert result["totals"]["measurements_with_multiple_molecule_records"] == 1


def test_missing_kinds_remain_named() -> None:
    result = audit_rows((point_row(),))
    assert set(result["unnamed_kinds"]) == {
        "complex",
        "cell_state",
        "patient",
        "therapeutic_candidate",
    }
    assert all(
        value["admitted_rows_without_identifier"] == 1 for value in result["unnamed_kinds"].values()
    )
