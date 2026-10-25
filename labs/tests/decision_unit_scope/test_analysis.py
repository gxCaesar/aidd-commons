"""The counting rules: the unit of inference, the grouping unit and the salt case."""

from __future__ import annotations

from typing import Any

import pytest
from aidd_commons.decision_unit_scope.analysis import (
    AnalysisContractError,
    census_cohort,
    census_parent,
    first_admitted_point_row,
    highest_salt_form_share,
    largest_row_to_measurement_gap,
    measurement_context,
    parents_with_no_admitted_measurement,
    resolve_entities,
    seeds_sharing_a_parent,
)
from aidd_commons.decision_unit_scope.data import (
    ActivityRow,
    AssayRecord,
    CohortDataset,
    MoleculeRecord,
    ParentDataset,
)

PARENT = "CHEMBL593"
CHILD = "CHEMBL929"


def row(
    activity_id: int,
    *,
    molecule_id: str = PARENT,
    assay_chembl_id: str = "CHEMBL_ASSAY_1",
    document_chembl_id: str = "CHEMBL_DOC_1",
    standard_type: str = "IC50",
    standard_relation: str = "=",
    standard_value: float = 40.0,
    standard_flag: int = 1,
    potential_duplicate: int = 0,
    data_validity_comment: str | None = None,
    standard_units: str = "nM",
    canonical_smiles: str = "c1ccccc1",
) -> ActivityRow:
    return ActivityRow(
        activity_id=activity_id,
        assay_chembl_id=assay_chembl_id,
        document_chembl_id=document_chembl_id,
        document_journal="J Med Chem",
        document_year=1991,
        molecule_chembl_id=molecule_id,
        parent_molecule_chembl_id=PARENT,
        canonical_smiles=canonical_smiles,
        standard_type=standard_type,
        standard_relation=standard_relation,
        standard_value=standard_value,
        standard_units=standard_units,
        standard_flag=standard_flag,
        potential_duplicate=potential_duplicate,
        data_validity_comment=data_validity_comment,
        pchembl_value=7.4,
        assay_type="B",
        target_chembl_id="CHEMBL_TARGET_1",
        target_organism="Homo sapiens",
        target_pref_name="Target one",
        toid=None,
    )


def assay(assay_chembl_id: str, *, confidence_score: int = 9) -> AssayRecord:
    return AssayRecord(
        assay_chembl_id=assay_chembl_id,
        assay_type="B",
        assay_organism="Homo sapiens",
        assay_tax_id=9606,
        bao_format="BAO_0000224",
        confidence_score=confidence_score,
        document_chembl_id="CHEMBL_DOC_1",
        relationship_type="D",
        target_chembl_id="CHEMBL_TARGET_1",
    )


def molecule(
    molecule_chembl_id: str, pref_name: str, parent_id: str, fragments: int = 1
) -> MoleculeRecord:
    return MoleculeRecord(
        molecule_chembl_id=molecule_chembl_id,
        pref_name=pref_name,
        parent_molecule_chembl_id=parent_id,
        canonical_smiles="c1ccccc1",
        fragment_count=fragments,
    )


def cohort_of(
    rows: list[ActivityRow],
    *,
    molecules: list[MoleculeRecord] | None = None,
    assays: dict[str, AssayRecord] | None = None,
) -> CohortDataset:
    return CohortDataset(
        status={"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2026-05-01"},
        molecules={record.molecule_chembl_id: record for record in (molecules or [])},
        parents={PARENT: ParentDataset(parent_molecule_chembl_id=PARENT, rows=tuple(rows))},
        assays=assays or {},
    )


def test_replicates_inside_one_assay_are_one_measurement() -> None:
    rows = [
        row(1, assay_chembl_id="CHEMBL_A"),
        row(2, assay_chembl_id="CHEMBL_A"),
        row(3, assay_chembl_id="CHEMBL_A", document_chembl_id="CHEMBL_DOC_2"),
    ]
    census = census_parent(ParentDataset(PARENT, tuple(rows)), {}, "Test")
    assert census.admitted_point_count == 3
    assert census.independent_measurement_count == 2
    assert census.independent_experiment_count == 2
    assert census.replicate_point_row_count == 1


def test_two_documents_in_one_assay_are_two_measurements_but_one_assay() -> None:
    rows = [
        row(1, assay_chembl_id="CHEMBL_A", document_chembl_id="CHEMBL_DOC_1"),
        row(2, assay_chembl_id="CHEMBL_A", document_chembl_id="CHEMBL_DOC_2"),
    ]
    census = census_parent(ParentDataset(PARENT, tuple(rows)), {}, "Test")
    assert census.independent_measurement_count == 2
    assert census.independent_experiment_count == 2
    assert census.distinct_assay_count == 1
    assert census.distinct_document_count == 2


def test_the_endpoint_type_is_part_of_the_grouping_unit() -> None:
    rows = [
        row(1, standard_type="IC50"),
        row(2, standard_type="Ki"),
    ]
    census = census_parent(ParentDataset(PARENT, tuple(rows)), {}, "Test")
    assert census.independent_measurement_count == 2
    assert census.independent_experiment_count == 1
    assert census.endpoint_type_counts == {"IC50": 1, "Ki": 1}


def test_a_salt_row_is_counted_as_a_salt_form_measurement() -> None:
    rows = [row(1), row(2, molecule_id=CHILD)]
    census = census_parent(ParentDataset(PARENT, tuple(rows)), {}, "Test")
    assert census.admitted_point_count == 2
    assert census.parent_form_point_count == 1
    assert census.salt_form_point_count == 1
    assert census.child_molecule_ids == (CHILD,)


def test_a_bound_is_never_counted_as_a_point_measurement() -> None:
    rows = [row(1), row(2, standard_relation=">")]
    census = census_parent(ParentDataset(PARENT, tuple(rows)), {}, "Test")
    assert census.admitted_point_count == 1
    assert census.admitted_bound_count == 1
    assert census.bound_relation_counts == {">": 1}


def test_the_exclusion_counts_partition_the_reported_rows() -> None:
    rows = [
        row(1),
        row(2, standard_type="Activity"),
        row(3, standard_flag=0),
        row(4, potential_duplicate=1),
    ]
    census = census_parent(ParentDataset(PARENT, tuple(rows)), {}, "Test")
    assert sum(census.exclusion_counts.values()) == 3
    assert census.reported_row_count == 4
    assert census.admitted_point_count == 1


def test_the_assay_context_is_attached_to_the_measurements() -> None:
    rows = [row(1, assay_chembl_id="CHEMBL_A")]
    census = census_parent(
        ParentDataset(PARENT, tuple(rows)),
        {"CHEMBL_A": assay("CHEMBL_A", confidence_score=8)},
        "Test",
    )
    assert census.assay_type_counts == {"B": 1}
    assert census.confidence_score_counts == {"8": 1}
    assert census.assay_organism_counts == {"Homo sapiens": 1}
    assert census.target_organism_counts == {"Homo sapiens": 1}
    assert census.assay_type_disagreement_count == 0


def test_the_entity_resolution_collapses_a_salt_onto_its_parent() -> None:
    cohort = cohort_of(
        [],
        molecules=[
            molecule(PARENT, "DELAVIRDINE", PARENT),
            molecule(CHILD, "DELAVIRDINE MESYLATE", PARENT, fragments=2),
        ],
    )
    resolutions = resolve_entities(cohort)
    assert {item.parent_molecule_chembl_id for item in resolutions} == {PARENT}
    assert resolutions[0].is_multi_component is (resolutions[0].fragment_count > 1)


def test_a_seed_that_is_its_own_parent_resolves_to_itself() -> None:
    cohort = cohort_of(
        [],
        molecules=[molecule(PARENT, "DELAVIRDINE", PARENT)],
    )
    resolutions = resolve_entities(cohort)
    assert len(resolutions) == 1
    assert resolutions[0].is_own_parent is True
    assert resolutions[0].parent_molecule_chembl_id == PARENT


def test_the_named_examples_pick_the_right_compounds() -> None:
    cohort = cohort_of(
        [
            row(1),
            row(2, molecule_id=CHILD),
            row(3, standard_type="Activity"),
            row(4, standard_type="Inhibition"),
        ],
        molecules=[
            molecule(PARENT, "DELAVIRDINE", PARENT),
            molecule(CHILD, "DELAVIRDINE MESYLATE", PARENT, fragments=2),
        ],
    )
    census = census_cohort(cohort)
    assert census.reported_row_count == 4
    assert census.admitted_point_count == 2
    assert census.salt_form_point_count == 1
    gap = largest_row_to_measurement_gap(census)
    assert gap.parent_molecule_chembl_id == PARENT
    salt = highest_salt_form_share(census)
    assert salt.parent_molecule_chembl_id == PARENT
    assert seeds_sharing_a_parent(census) == ((PARENT, (PARENT, CHILD)),)


def test_a_parent_with_no_admissible_measurement_is_reported_as_such() -> None:
    cohort = cohort_of(
        [row(1, standard_type="Activity")],
        molecules=[molecule(PARENT, "DELAVIRDINE", PARENT)],
    )
    census = census_cohort(cohort)
    empty = parents_with_no_admitted_measurement(census)
    assert [item.parent_molecule_chembl_id for item in empty] == [PARENT]
    assert empty[0].reported_row_count == 1


def test_one_reported_value_carries_its_whole_context() -> None:
    rows = [row(1, assay_chembl_id="CHEMBL_A"), row(2, molecule_id=CHILD)]
    context = measurement_context(rows[1], assay("CHEMBL_A"), "DELAVIRDINE")
    assert context.tested_molecule_chembl_id == CHILD
    assert context.tested_form == "child (salt or mixture) form"
    assert context.standard_type == "IC50"
    assert context.standard_value == 40.0
    assert context.standard_relation == "="
    assert context.assay_type == "B"
    assert context.assay_organism == "Homo sapiens"
    assert context.confidence_score == 9
    assert context.document_chembl_id == "CHEMBL_DOC_1"
    assert context.document_journal == "J Med Chem"
    assert context.target_organism == "Homo sapiens"


def test_a_parent_without_an_admitted_measurement_has_no_example_row() -> None:
    dataset = ParentDataset(PARENT, (row(1, standard_type="Activity"),))
    with pytest.raises(AnalysisContractError, match="no admitted point measurement"):
        first_admitted_point_row(dataset)


def test_a_missing_assay_record_is_reported_rather_than_guessed() -> None:
    rows = [row(1, assay_chembl_id="CHEMBL_A")]
    census = census_parent(ParentDataset(PARENT, tuple(rows)), {}, "Test")
    assert census.confidence_score_counts == {"assay record not fetched": 1}
    assert census.assay_organism_counts == {"assay record not fetched": 1}


def _unused(_: Any) -> None:
    """Keep the typing import honest."""
