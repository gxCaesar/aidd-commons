"""Frozen contract for the generalization-unit audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope import protocol as source

PROTOCOL_ID = "chembl37-generalization-unit-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.generalization-unit-audit-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.generalization-unit-audit-summary.v1"
ISSUED_ON = "2026-10-23"
RDKIT_VERSION = "2025.09.6"
UNITS = {
    "molecule_record": "molecule_chembl_id",
    "parent_molecule": "parent_molecule_chembl_id",
    "bemis_murcko_scaffold": "chirality-aware RDKit Bemis-Murcko scaffold of canonical_smiles",
    "assay": "assay_chembl_id",
    "target": "target_chembl_id",
    "document": "document_chembl_id",
}
CANNOT_NAME = {
    "time_point": "The activity snapshot has no measurement time point.",
    "site": "The activity snapshot has no collection site identifier.",
    "patient": "The activity snapshot has no patient identifier.",
}
RULE = {
    "measurement": (
        "Admitted point rows sharing parent, assay, document and endpoint type "
        "form one independent measurement."
    ),
    "membership": (
        "Every distinct unit value on a measurement's source rows carries that "
        "measurement once. One measurement may belong to multiple molecule "
        "or scaffold values."
    ),
    "counts": (
        "For each candidate unit count distinct values, measurement memberships, "
        "median, inclusive-interpolated first and third quartiles of memberships "
        "per value, and values with exactly one measurement."
    ),
    "comparison": (
        "Compare the candidate units with the most and fewest distinct values. "
        "Ties follow declared unit order."
    ),
}
EXCLUDED_BY_DESIGN = (
    "Any performance estimate or prediction score.",
    "Any claim that a split by one candidate unit is correct rather than declared.",
    "Any selection of a unit because it separates these data well.",
    "Any population estimate from this deliberately selected teaching cohort.",
)


class ProtocolError(ValueError):
    """The protocol differs from the frozen contract."""


def expected_fields() -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "source": {
            "database": source.CHEMBL_VERSION,
            "release_date": source.CHEMBL_RELEASE_DATE,
            "status_url": source.CHEMBL_STATUS_URL,
            "api_root": source.CHEMBL_API_ROOT,
            "licence": {"name": source.CHEMBL_LICENSE_NAME, "url": source.CHEMBL_LICENSE_URL},
        },
        "cohort": {
            "seeds": [
                {"molecule_chembl_id": identifier, "pref_name": name}
                for identifier, name in source.COHORT_SEEDS
            ],
            "resolved_parents": list(source.COHORT_PARENTS),
        },
        "endpoint": {
            "standard_types": list(source.ENDPOINT_TYPES),
            "standard_units": source.STANDARD_UNITS,
            "point_relation": source.POINT_RELATION,
            "bound_relations": list(source.BOUND_RELATIONS),
            "exclusion_priority": list(source.EXCLUSION_PRIORITY),
            "measurement_grouping_fields": [
                "parent_molecule_chembl_id",
                *source.GROUPING_FIELDS,
            ],
        },
        "candidate_units": [{"unit": unit, "field": field} for unit, field in UNITS.items()],
        "units_table_cannot_name": [
            {"unit": unit, "reason": reason} for unit, reason in CANNOT_NAME.items()
        ],
        "measurement_rule": RULE,
        "rdkit_version": RDKIT_VERSION,
        "artifacts": source.expected_artifacts(),
        "excluded_by_design": list(EXCLUDED_BY_DESIGN),
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    expected = expected_fields()
    if not isinstance(document, dict):
        raise ProtocolError("protocol must be an object")
    if document != expected:
        changed = [key for key in expected if document.get(key) != expected[key]]
        raise ProtocolError(f"changed protocol fields: {', '.join(changed) or 'extra field'}")
    return document
