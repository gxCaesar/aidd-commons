"""Frozen entity-reading contract, tied to the decision-unit admission rule."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope import protocol as source

PROTOCOL_ID = "chembl37-entity-glossary-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.entity-glossary-audit-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.entity-glossary-audit-summary.v1"
ISSUED_ON = "2026-10-23"
KIND_FIELDS = {
    "molecule_record": "molecule_chembl_id",
    "parent_molecule": "parent_molecule_chembl_id",
    "assay": "assay_chembl_id",
    "target": "target_chembl_id",
    "document": "document_chembl_id",
}
UNNAMED_KINDS = {
    "complex": "No complex identifier occurs in the cached activity rows.",
    "cell_state": "No cell-state identifier occurs in the cached activity rows.",
    "patient": "No patient identifier occurs in the cached activity rows.",
    "therapeutic_candidate": (
        "No candidate designation occurs in the cached activity rows; activity is not nomination."
    ),
}
ROW_RULE = (
    "This laboratory reads each admitted point row as a measurement of its molecule record, "
    "grouped under the parent to which that record resolves. Its assay names the measurement "
    "system, its target names what was measured against, and its document names the publication. "
    "Independent measurements use the decision-unit (parent, assay, document, endpoint) key; "
    "one such group may contain more than one molecule record."
)
EXCLUSIONS = (
    "Any claim that two identifiers name the same thing.",
    "Any prediction of what a compound does.",
    "Any selection of a cohort because it gives a convenient answer.",
    "Any claim that a target identifier names a disease or a document validates a measurement.",
)


class ProtocolError(ValueError):
    """The on-disk protocol differs from its compiled frozen contract."""


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
        "artifacts": source.expected_artifacts(),
        "named_kinds": KIND_FIELDS,
        "unnamed_kinds": UNNAMED_KINDS,
        "row_rule": ROW_RULE,
        "excluded_by_design": list(EXCLUSIONS),
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(document, dict):
        raise ProtocolError("protocol must be an object")
    expected = expected_fields()
    if document != expected:
        changed = [key for key in expected if document.get(key) != expected[key]]
        raise ProtocolError(
            f"changed frozen protocol fields: {', '.join(changed) or 'extra field'}"
        )
    return document
