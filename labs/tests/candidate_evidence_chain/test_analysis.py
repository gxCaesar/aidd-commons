"""Small constructed profiles exercise the link states, not candidate claims."""

from __future__ import annotations

import copy

import pytest
from aidd_commons.candidate_evidence_chain.analysis import audit_chains, make_chain


def profile() -> dict[str, object]:
    return {
        "parent_chembl_id": "TEST-PARENT",
        "efficacy": {
            "measurements": [
                {
                    "assay_chembl_id": "ASSAY-1",
                    "document_chembl_id": "DOC-1",
                    "endpoint_type": "IC50",
                    "value": 12.0,
                    "unit": "nM",
                }
            ]
        },
        "interaction": {
            "measurements": [
                {
                    "target": "CYP2D6",
                    "value": 4.2,
                    "unit": "pChEMBL (dimensionless)",
                    "assay_chembl_ids": ["ASSAY-2"],
                    "document_chembl_ids": ["DOC-2"],
                    "contributing_activity_count": 1,
                },
                {
                    "target": "CYP3A4",
                    "value": 5.3,
                    "unit": "pChEMBL (dimensionless)",
                    "assay_chembl_ids": ["ASSAY-3"],
                    "document_chembl_ids": ["DOC-2"],
                    "contributing_activity_count": 1,
                },
            ]
        },
        "exposure": {
            "measurements": [
                {
                    "assay_chembl_id": "ASSAY-4",
                    "assay_system": "Human hepatocytes",
                    "value": 7.0,
                    "unit": "uL.min-1.(10^6cells)-1",
                }
            ]
        },
    }


def test_measured_family_links_keep_values_and_sources() -> None:
    chain = make_chain(profile())  # type: ignore[arg-type]
    assert chain["counts"] == {"measured": 3, "absent": 0, "constructed": 0, "not covered": 5}
    assert chain["first_non_measured"] == "mechanism"
    assert chain["supports_claim"] is False
    assert chain["links"][2]["measurements"][0]["value"] == 12.0
    assert chain["links"][3]["measurements"][0]["document_chembl_id"] == "DOC-2"
    assert chain["links"][4]["measurements"][0]["document_chembl_id"] == "CHEMBL3301361"
    audit_chains([chain])


def test_missing_activity_is_absent_with_no_default() -> None:
    source = profile()
    source["efficacy"] = None
    chain = make_chain(source)  # type: ignore[arg-type]
    assert chain["links"][2]["state"] == "absent"
    assert chain["links"][2]["measurements"] == []
    assert chain["links"][2]["scope"] is None
    assert chain["counts"]["absent"] == 1
    audit_chains([chain])


def test_unmatched_cyp_document_does_not_create_selectivity() -> None:
    source = copy.deepcopy(profile())
    source["interaction"]["measurements"][1]["document_chembl_ids"] = ["OTHER-DOC"]  # type: ignore[index]
    chain = make_chain(source)  # type: ignore[arg-type]
    assert chain["links"][3]["state"] == "absent"
    assert chain["links"][3]["measurements"] == []


def test_claim_stops_at_first_non_measured_link() -> None:
    chain = make_chain(profile())  # type: ignore[arg-type]
    chain["first_non_measured"] = "target"
    with pytest.raises(ValueError, match="first non-measured"):
        audit_chains([chain])


def test_hypothetical_complete_chain_cannot_expand_first_scope() -> None:
    chain = make_chain(profile())  # type: ignore[arg-type]
    for link in chain["links"]:
        if link["state"] != "measured":
            link["state"] = "measured"
            link["scope"] = "One named assay only"
            link["source"] = "synthetic-test-source"
            link["measurements"] = [
                {
                    "value": 1.0,
                    "unit": "test unit",
                    "assay_chembl_id": "TEST-ASSAY",
                    "document_chembl_id": "TEST-DOC",
                }
            ]
    chain["counts"] = {"measured": 8, "absent": 0, "constructed": 0, "not covered": 0}
    chain["first_non_measured"] = None
    chain["supports_claim"] = True
    chain["bounded_claim"] = "Development candidate"
    with pytest.raises(ValueError, match="first measured link's scope"):
        audit_chains([chain])
    chain["bounded_claim"] = "One named assay only"
    audit_chains([chain])
