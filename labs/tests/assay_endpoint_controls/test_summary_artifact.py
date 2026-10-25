"""The committed public summary must be internally consistent.

This test reads the committed `summary.json` only. It does not need the
cached archive, so it runs in CI with no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.assay_endpoint_controls.protocol import (
    DECLARED_ASSAYS,
    PROTOCOL_ID,
    SPLIT_RULE,
    SPLIT_SEED,
    SUMMARY_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = ROOT / "labs/assay_endpoint_controls/summary.json"


def load_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_the_committed_summary_matches_the_frozen_protocol() -> None:
    summary = load_summary()
    assert summary["protocol_id"] == PROTOCOL_ID
    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert summary["split"]["rule"] == SPLIT_RULE
    assert summary["split"]["seed"] == SPLIT_SEED
    assert set(summary["assays"]) == {str(aid) for aid in DECLARED_ASSAYS}


def test_the_committed_summary_carries_a_computation_date_and_software_versions() -> None:
    summary = load_summary()
    assert summary["computed_on"]
    assert len(summary["computed_on"]) == 10
    software = summary["software"]
    assert set(software) == {"python", "numpy", "scipy", "rdkit"}
    for version in software.values():
        assert str(version).strip()


def test_the_committed_summary_mixes_are_internally_consistent() -> None:
    summary = load_summary()
    readout = summary["readout_mix"]
    assert readout["total"] == sum(readout["counts"].values())
    for key, fraction in readout["fractions"].items():
        assert fraction == pytest.approx(
            readout["counts"][key] / readout["total"], abs=1e-6
        )
    relation = summary["relation_mix"]
    assert relation["total"] == sum(relation["counts"].values())
    assert set(relation["counts"]) <= {"=", "<", ">", "unstated"}


def test_the_committed_summary_counts_every_admitted_row_of_every_assay() -> None:
    summary = load_summary()
    total = 0
    for aid in DECLARED_ASSAYS:
        assay = summary["assays"][str(aid)]
        audit = assay["audit"]
        assert audit["retained_rows"] <= audit["input_rows"]
        assert sum(audit["exclusion_counts"].values()) == (
            audit["input_rows"] - audit["retained_rows"]
        )
        assert audit["admitted_compounds"] <= audit["retained_rows"]
        assert assay["relation_mix"]["total"] == audit["retained_rows"]
        total += audit["retained_rows"]
    assert summary["relation_mix"]["total"] == total
    assert summary["split"]["counts"]["development"] + summary["split"]["counts"][
        "held_out"
    ] == total


def test_the_committed_summary_reports_a_control_audit_for_every_assay() -> None:
    summary = load_summary()
    for aid in DECLARED_ASSAYS:
        audit = summary["assays"][str(aid)]["reference_audit"]
        assert audit["declared_regime"] in (
            "positive_and_negative_reference",
            "single_positive_reference",
            "none_declared",
        )
        expected = {
            "positive_and_negative_reference": 2,
            "single_positive_reference": 1,
            "none_declared": 0,
        }[audit["declared_regime"]]
        assert audit["references_declared"] == expected
        if audit["declared_regime"] == "none_declared":
            assert audit["control_keywords_in_protocol"] == []
            assert audit["equation_scale_verdict"] == "not_declared"
        else:
            assert audit["control_keywords_in_protocol"]
        assert audit["equation_scale_verdict"] in (
            "zero_to_hundred_scale",
            "shifted_scale",
            "other_scale",
            "not_declared",
        )


def test_the_committed_summary_states_what_each_assay_licenses() -> None:
    summary = load_summary()
    for aid in DECLARED_ASSAYS:
        assay = summary["assays"][str(aid)]
        assert assay["licensed_claims"]
        assert assay["unlicensed_claims"]
        assert all(isinstance(claim, str) and claim for claim in assay["licensed_claims"])
        assert all(isinstance(claim, str) and claim for claim in assay["unlicensed_claims"])


def test_the_committed_summary_carries_a_fixed_number_of_named_examples() -> None:
    summary = load_summary()
    for aid in DECLARED_ASSAYS:
        examples = summary["assays"][str(aid)]["examples"]
        assert len(examples) == 2
        for example in examples:
            assert example["compound_id"].isdigit()
            assert "endpoints" in example
            if "responses" in example:
                assert len(example["responses"]) == len(example["concentrations_um"])
                assert len(example["concentrations_um"]) >= 5
            else:
                assert len(example["concentration_categories"]) == len(
                    example["concentrations_um"]
                )
                assert all(
                    item is None or isinstance(item, str)
                    for item in example["concentration_categories"]
                )


def test_the_committed_summary_holds_no_bulk_compound_list() -> None:
    summary = load_summary()
    for aid in DECLARED_ASSAYS:
        assay = summary["assays"][str(aid)]
        assert set(assay) == {
            "name",
            "endpoint",
            "direction",
            "audit",
            "outcome_mix",
            "relation_mix",
            "readout_mix",
            "confidence_score",
            "replicate_structure",
            "reference_audit",
            "curve_check",
            "licensed_claims",
            "unlicensed_claims",
            "examples",
        }
        assert isinstance(assay["audit"]["exclusion_counts"], dict)
        assert len(assay["examples"]) == 2


def test_the_committed_summary_reports_the_split_stability_of_every_assay() -> None:
    summary = load_summary()
    stability = summary["split_stability"]
    assert set(stability) == {str(aid) for aid in DECLARED_ASSAYS}
    for entry in stability.values():
        assert set(entry) == {"development", "held_out"}
        for half in entry.values():
            assert "relation_mix" in half
            assert "readout_mix" in half
