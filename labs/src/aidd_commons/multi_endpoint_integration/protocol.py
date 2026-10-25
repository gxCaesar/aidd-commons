"""Frozen contract for the multi-endpoint integration laboratory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope.protocol import (
    ARTIFACT_BYTE_LENGTHS,
    CHEMBL_LICENSE_NAME,
    CHEMBL_LICENSE_URL,
    CHEMBL_RELEASE_DATE,
    CHEMBL_VERSION,
)

PROTOCOL_ID = "chembl37-multi-endpoint-integration-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.multi-endpoint-integration-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.multi-endpoint-integration-summary.v1"
ISSUED_ON = "2026-10-23"
PACKAGE_VERSION_FALLBACK = "0.2.0rc1"
FAMILIES = ("efficacy", "exposure", "interaction")
ALL_FAMILIES = (*FAMILIES, "toxicity")
ARCHIVE = "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/"
LICENCE = {"name": CHEMBL_LICENSE_NAME, "url": CHEMBL_LICENSE_URL}

# The owning readers validate content and admission. These lengths additionally
# freeze the exact local snapshots that this join was computed from.
SNAPSHOT_FILES = {
    "decision_unit_scope": dict(ARTIFACT_BYTE_LENGTHS),
    "az_clearance_system": {
        "status.json": 231,
        "activities-CHEMBL3301370.json": 701737,
        "activities-CHEMBL3301371.json": 549808,
        "activities-CHEMBL3301372.json": 266453,
    },
    "cyp_assay_system": {
        "status.json": 231,
        "activities-CHEMBL289.json": 2231098,
        "activities-CHEMBL340.json": 4462282,
    },
}
READ_ROUTES = {
    "decision_unit_scope": "aidd_commons.decision_unit_scope.data.load_cached_cohort",
    "az_clearance_system": "aidd_commons.az_clearance_system.data.load_cached_systems",
    "cyp_assay_system": "aidd_commons.cyp_assay_system.data.load_cached_targets",
}
READ_DATES = {
    "decision_unit_scope": "2026-10-21",
    "az_clearance_system": "2026-09-12",
    "cyp_assay_system": "2026-09-12",
}
COMPOSITE_RULE = (
    "Refuse every composite, weighted sum, overall desirability value or rank across families. "
    "Report the measured axes side by side."
)
MISSING_RULE = (
    "An absent family is null and remains missing. It is never filled with a no-risk, "
    "adequate-exposure or other default."
)
BOUNDARY_STATEMENT = (
    "The efficacy axis contains in vitro response-potency proxies, exposure contains in vitro "
    "intrinsic clearance rather than systemic exposure, and interaction contains CYP inhibition "
    "potency rather than a clinical interaction outcome. No toxicity measurement is available. "
    "The constructed examples in labs/safety_evidence/ are not compound measurements. "
    "Observed ranges describe the admitted records, not confidence intervals. Microsome clearance "
    "per gram of protein cannot be divided by hepatocyte clearance per million cells to claim "
    "a fold change."
)
EXCLUDED_BY_DESIGN = [
    "any composite score, weighted sum or combined numeric value across families",
    "any overall desirability ranking of compounds",
    "any claim that a compound measured in one family is free of another family's risk",
    "any default value for a family absent from a compound",
    "any claim that constructed safety data in labs/safety_evidence/ measure toxicity",
    "any fold change between microsome and hepatocyte clearance with incompatible bases",
    "any claim of therapeutic efficacy, systemic exposure or clinical drug interaction",
]


class ProtocolContractError(ValueError):
    """The on-disk contract or cached snapshot differs from its frozen form."""


def expected_contract() -> dict[str, Any]:
    sources = [
        {
            "name": name,
            "snapshot": CHEMBL_VERSION,
            "snapshot_byte_length": sum(files.values()),
            "archive": ARCHIVE,
            "licence": LICENCE,
            "read_route": READ_ROUTES[name],
            "read_on": READ_DATES[name],
            "cache_directory": f".cache/{name}",
            "files": files,
        }
        for name, files in SNAPSHOT_FILES.items()
    ]
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "source_release_date": CHEMBL_RELEASE_DATE,
        "sources": sources,
        "families": {
            "efficacy": {
                "reader": READ_ROUTES["decision_unit_scope"],
                "unit": "nM",
                "measurement_rule": (
                    "Independent exact AC50, EC50 and IC50 response-potency points, grouped by "
                    "parent, assay, document and endpoint type. Kd and Ki affinity points are "
                    "counted separately and do not establish efficacy."
                ),
            },
            "exposure": {
                "reader": READ_ROUTES["az_clearance_system"],
                "unit": ["mL.min-1.g-1", "uL.min-1.(10^6cells)-1"],
                "measurement_rule": (
                    "Admitted intrinsic-clearance median for one parent in one named assay "
                    "system, with the contributing-activity range retained."
                ),
            },
            "interaction": {
                "reader": READ_ROUTES["cyp_assay_system"],
                "unit": "pChEMBL (dimensionless)",
                "measurement_rule": (
                    "Admitted exact IC50 median for one parent against CYP3A4 or CYP2D6, "
                    "with contributing assay IDs and pChEMBL range retained."
                ),
            },
            "toxicity": {
                "reader": None,
                "unit": None,
                "measurement_rule": (
                    "No measured toxicity snapshot exists here. labs/safety_evidence/ holds "
                    "constructed teaching data and contributes no compound measurement."
                ),
            },
        },
        "counted_unit": {
            "name": "one ChEMBL parent molecule",
            "join_rule": (
                "Join families only by equal parent_molecule_chembl_id returned by their "
                "validated readers. Never join by structure, name, assay or row position."
            ),
        },
        "rules": {"composite_score": COMPOSITE_RULE, "missing_family": MISSING_RULE},
        "excluded_by_design": EXCLUDED_BY_DESIGN,
    }


def validate_protocol_document(document: dict[str, Any]) -> None:
    expected = expected_contract()
    for field, value in expected.items():
        if document.get(field) != value:
            raise ProtocolContractError(f"protocol {field} differs from the frozen contract")
    if set(document) != set(expected):
        raise ProtocolContractError("protocol has undeclared fields")


def load_protocol_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError(f"cannot read protocol: {error}") from error
    if not isinstance(document, dict):
        raise ProtocolContractError("protocol must be a JSON object")
    validate_protocol_document(document)
    return document


def validate_cache_lengths(cache_root: Path) -> None:
    for name, files in SNAPSHOT_FILES.items():
        for filename, expected in files.items():
            path = cache_root / name / filename
            if not path.is_file() or path.stat().st_size != expected:
                raise ProtocolContractError(f"{name}/{filename}: missing or different byte length")
