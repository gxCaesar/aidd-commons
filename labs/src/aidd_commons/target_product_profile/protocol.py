"""Frozen target product profile, declared independently of observed values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.multi_endpoint_integration.protocol import expected_contract as source_contract

PROTOCOL_ID = "chembl37-target-product-profile-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.target-product-profile-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.target-product-profile-summary.v1"
ISSUED_ON = "2026-10-23"
PACKAGE_VERSION_FALLBACK = "0.2.0rc1"
BOUNDARY_STATEMENT = (
    "This illustrative profile judges only admitted in vitro response potency, intrinsic "
    "clearance and CYP inhibition measurements in the joined cohort. These are not clinical "
    "efficacy, systemic exposure, clinical safety or development-candidate evidence. "
    "Clinical efficacy and immunogenicity remain unmeasured. Microsome clearance per gram "
    "of protein and hepatocyte clearance per million cells are never divided."
)
RULES = {
    "gate_failure": (
        "Any measured mandatory gate failure excludes a parent from the profile-satisfying set."
    ),
    "preference_miss": "A missed preference is reported separately and does not exclude a parent.",
    "unmeasured": (
        "A requirement without a matching measurement is unmeasured, never passed or satisfied."
    ),
    "satisfaction": "Only a parent passing every mandatory gate is profile-satisfying.",
}
REQUIREMENTS: list[dict[str, Any]] = [
    {
        "id": "response_ic50",
        "kind": "gate",
        "family": "efficacy",
        "measurement": "IC50 response-potency point in each admitted assay and document",
        "selector": {"endpoint_type": "IC50"},
        "comparison": "all_lte",
        "threshold": 1000,
        "unit": "nM",
    },
    {
        "id": "human_microsome_clearance",
        "kind": "gate",
        "family": "exposure",
        "measurement": "Intrinsic clearance in human liver microsomes",
        "selector": {"assay_system": "Human liver microsomes"},
        "comparison": "all_lte",
        "threshold": 50,
        "unit": "mL.min-1.g-1",
    },
    {
        "id": "cyp3a4_inhibition",
        "kind": "gate",
        "family": "interaction",
        "measurement": "CYP3A4 inhibition potency",
        "selector": {"target": "CYP3A4"},
        "comparison": "all_lte",
        "threshold": 5,
        "unit": "pChEMBL (dimensionless)",
    },
    {
        "id": "rat_hepatocyte_clearance",
        "kind": "preference",
        "family": "exposure",
        "measurement": "Intrinsic clearance in rat hepatocytes",
        "selector": {"assay_system": "Rat hepatocytes"},
        "comparison": "all_lte",
        "threshold": 30,
        "unit": "uL.min-1.(10^6cells)-1",
    },
    {
        "id": "cyp2d6_inhibition",
        "kind": "preference",
        "family": "interaction",
        "measurement": "CYP2D6 inhibition potency",
        "selector": {"target": "CYP2D6"},
        "comparison": "all_lte",
        "threshold": 5,
        "unit": "pChEMBL (dimensionless)",
    },
    {
        "id": "clinical_response",
        "kind": "gate",
        "family": "clinical_efficacy",
        "measurement": "Objective response rate in the intended population",
        "selector": None,
        "comparison": "all_gte",
        "threshold": 30,
        "unit": "%",
    },
    {
        "id": "immunogenicity",
        "kind": "preference",
        "family": "immunogenicity",
        "measurement": "Treatment-emergent anti-drug antibody incidence",
        "selector": None,
        "comparison": "all_lte",
        "threshold": 5,
        "unit": "%",
    },
]


class ProtocolContractError(ValueError):
    """The on-disk profile differs from its frozen declaration."""


def expected_contract() -> dict[str, Any]:
    upstream = source_contract()
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "source_release_date": upstream["source_release_date"],
        "sources": upstream["sources"],
        "run_basis": (
            "This illustrative profile and every threshold were declared before cached "
            "measurements are read. Thresholds are teaching decisions, not estimates or "
            "cutoffs derived or tuned from this cohort. The three owning readers and the "
            "multi-endpoint integration join are reused without download or parsing."
        ),
        "profile": {
            "intended_population": "Illustrative adults with advanced solid tumours",
            "intended_route": "oral",
            "requirements": REQUIREMENTS,
        },
        "counted_unit": {
            "name": "one admitted ChEMBL parent molecule",
            "cohort_rule": (
                "Parents with at least two measured families in the existing integration join"
            ),
            "join_rule": upstream["counted_unit"]["join_rule"],
        },
        "rules": RULES,
        "excluded_by_design": [
            "any claim that passing measured gates makes a compound a development candidate",
            "any ranking of compounds by the number of gates they pass",
            "any claim that a requirement without a measurement has been met",
            "any fold change between microsome and hepatocyte clearance bases",
            "any clinical conclusion from in vitro response, clearance or CYP measurements",
        ],
    }


def load_protocol_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError(f"cannot read protocol: {error}") from error
    if not isinstance(document, dict) or document != expected_contract():
        raise ProtocolContractError("protocol differs from the frozen profile contract")
    return document
