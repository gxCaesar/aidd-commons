"""Frozen authority for the nomination-readiness teaching rule."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope import protocol as source

PROTOCOL_ID = "chembl37-nomination-readiness-v1"
SCHEMA_VERSION = "aidd-commons.nomination-readiness-audit-protocol.v1"
ISSUED_ON = "2026-10-23"
THRESHOLDS = {
    "independent_measurements": 5,
    "distinct_assays": 3,
    "distinct_documents": 2,
}
MEASUREMENT_FIELDS = {
    "independent_measurements": [
        "assay_chembl_id",
        "document_chembl_id",
        "standard_type",
    ],
    "distinct_assays": ["assay_chembl_id"],
    "distinct_documents": ["document_chembl_id"],
}
EXCLUDED_BY_DESIGN = [
    "Any prediction of activity, safety or exposure for a compound.",
    "Any claim that this readiness rule is the right rule for candidate nomination.",
    "Any change of the thresholds after cohort counts are seen.",
    "Any claim that go means candidate, or stop means inactive.",
]


class ProtocolError(ValueError):
    """The on-disk protocol differs from the frozen authority."""


def expected_fields() -> dict[str, Any]:
    """Return all load-bearing fields, including the inherited source contract."""
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "source": {
            "database": source.CHEMBL_VERSION,
            "release_date": source.CHEMBL_RELEASE_DATE,
            "status_url": source.CHEMBL_STATUS_URL,
            "api_root": source.CHEMBL_API_ROOT,
            "licence": {
                "name": source.CHEMBL_LICENSE_NAME,
                "url": source.CHEMBL_LICENSE_URL,
            },
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
        "artifacts": source.expected_artifacts(),
        "readiness_rule": {
            "fixed_before_counting": True,
            "declaration_scope": (
                "Author-defined teaching thresholds fixed before this audit counted readiness "
                "states. The decision-unit source census already existed, so this is not an "
                "independently blinded threshold choice."
            ),
            "thresholds": dict(THRESHOLDS),
            "conditions": [
                {"metric": metric, "minimum": minimum} for metric, minimum in THRESHOLDS.items()
            ],
            "states": {
                "go": "All three conditions meet their minima.",
                "hold": "At least one but not all conditions meet their minima.",
                "stop": "None of the conditions meet their minima.",
            },
            "missing_measurement_rule": {
                "origin": "This laboratory's teaching rule, not a ChEMBL or clinical rule.",
                "selection": (
                    "Name every failed condition and the count needed to reach its minimum."
                ),
                "record_kind": "A newly admitted ChEMBL activity point record.",
                "fields_by_condition": MEASUREMENT_FIELDS,
                "independence": (
                    "A new independent measurement needs an unseen assay, document, "
                    "and endpoint-type key for this parent. Assay and document deficits "
                    "need new distinct identifiers in those fields."
                ),
            },
            "closest_to_go": (
                "Among non-go parents, fewest failed conditions, then smallest sum "
                "of missing counts, then lexicographic parent identifier."
            ),
        },
        "excluded_by_design": EXCLUDED_BY_DESIGN,
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(document, dict):
        raise ProtocolError("protocol must be an object")
    expected = expected_fields()
    for field, value in expected.items():
        if document.get(field) != value:
            raise ProtocolError(f"changed protocol field: {field}")
    if set(document) != set(expected):
        raise ProtocolError("unexpected protocol field")
    return document
