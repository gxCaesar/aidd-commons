"""Constructed measurements exercise the family and uncertainty rules."""

from __future__ import annotations

from aidd_commons.multi_endpoint_tradeoff.analysis import Measurement, analyse, family_for_type


def test_mapping_and_per_family_statistics() -> None:
    rows = (
        Measurement("A", "assay-1", "doc-1", "IC50", 10),
        Measurement("A", "assay-2", "doc-2", "EC50", 30),
        Measurement("A", "assay-2", "doc-2", "EC50", 50),
        Measurement("B", "assay-3", "doc-3", "Kd", 100),
        Measurement("B", "assay-4", "doc-4", "NEW_TYPE", 200),
    )
    result = analyse(rows, {"A": "Alpha", "B": "Beta", "C": "Gamma"})
    assert result["admitted_measurement_count"] == 4
    efficacy = result["families"]["efficacy"]
    assert efficacy["independent_measurement_count"] == 2
    assert efficacy["distinct_document_count"] == 2
    assert efficacy["distinct_assay_count"] == 2
    assert efficacy["median"] == 25
    assert efficacy["q1"] == 17.5
    assert efficacy["q3"] == 32.5
    assert efficacy["interquartile_range"] == 15
    assert efficacy["unit"] == "nM"
    assert efficacy["compounds_without_measurement_count"] == 2
    assert result["families"]["other"]["independent_measurement_count"] == 2
    assert family_for_type("NEW_TYPE") == "other"
    assert result["families"]["toxicity"]["independent_measurement_count"] == 0
    assert result["families"]["exposure"]["median"] is None
    assert result["compounds_with_empty_family"] == [
        {
            "parent_molecule_chembl_id": "A",
            "pref_name": "Alpha",
            "missing_families": ["toxicity", "exposure"],
            "present_named_family_count": 1,
        },
        {
            "parent_molecule_chembl_id": "B",
            "pref_name": "Beta",
            "missing_families": ["efficacy", "toxicity", "exposure"],
            "present_named_family_count": 0,
        },
        {
            "parent_molecule_chembl_id": "C",
            "pref_name": "Gamma",
            "missing_families": ["efficacy", "toxicity", "exposure"],
            "present_named_family_count": 0,
        },
    ]
