"""The predeclared rule names all three states and every deficit."""

from types import SimpleNamespace
from typing import cast

from aidd_commons.decision_unit_scope.analysis import CohortCensus
from aidd_commons.nomination_readiness_audit.analysis import analyze, classify_counts


def test_constructed_compounds_cover_go_hold_and_stop() -> None:
    examples = (
        SimpleNamespace(
            parent_molecule_chembl_id="P1",
            pref_name="go example",
            independent_measurement_count=5,
            distinct_assay_count=3,
            distinct_document_count=2,
        ),
        SimpleNamespace(
            parent_molecule_chembl_id="P2",
            pref_name="hold example",
            independent_measurement_count=4,
            distinct_assay_count=3,
            distinct_document_count=2,
        ),
        SimpleNamespace(
            parent_molecule_chembl_id="P3",
            pref_name="stop example",
            independent_measurement_count=0,
            distinct_assay_count=0,
            distinct_document_count=0,
        ),
    )
    census = cast(CohortCensus, SimpleNamespace(parents=examples, independent_measurement_count=9))
    result = analyze(census)
    assert result["state_counts"] == {"go": 1, "hold": 1, "stop": 1}
    assert result["state_members"] == {"go": ["P1"], "hold": ["P2"], "stop": ["P3"]}
    assert result["parents"][1]["missing_measurements"] == [
        {
            "condition": "independent_measurements",
            "additional_count_needed": 1,
            "record_kind": "admitted ChEMBL activity point record",
            "fields": ["assay_chembl_id", "document_chembl_id", "standard_type"],
        }
    ]
    assert result["closest_to_go"]["parent_molecule_chembl_id"] == "P2"


def test_failed_conditions_are_all_named() -> None:
    state, missing = classify_counts(
        {"independent_measurements": 0, "distinct_assays": 0, "distinct_documents": 0}
    )
    assert state == "stop"
    assert [item["additional_count_needed"] for item in missing] == [5, 3, 2]
