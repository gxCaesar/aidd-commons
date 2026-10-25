"""Frozen interpretation rule for the functional validation audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from aidd_commons.assay_endpoint_controls.protocol import ASSAYS, DECLARED_ASSAYS
from aidd_commons.decision_unit_scope import protocol as decision

PROTOCOL_ID = "chembl37-pubchem-functional-validation-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.functional-validation-audit-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.functional-validation-audit-summary.v1"
ISSUED_ON = "2026-10-23"
KIND_POINT = "point_measurement"
KIND_BOUND = "bound"
KIND_RESPONSE = "concentration_response_table"
KIND_NONE = "no_licensed_claim"
KINDS = (KIND_POINT, KIND_BOUND, KIND_RESPONSE, KIND_NONE)
ENDPOINT_LABELS = ("AC50", "EC50", "IC50", "Ki", "MIC")
UNMEASURABLE_ROUTES = {
    "clinical_outcome": "Neither snapshot carries a clinical endpoint or an outcome observation.",
    "binding_to_response_transfer": (
        "The snapshots do not pair a direct binding measurement with a response "
        "record for the same entity under a matched experiment."
    ),
    "response_to_clinical_transfer": (
        "Neither snapshot links a response record to a clinical outcome record."
    ),
}
RULE_STATEMENT = (
    "A point with a stated endpoint type and unit licenses its reported value. "
    "A stated relation bound licenses only a bound. A numeric concentration "
    "series with a stated response definition licenses an observed response "
    "in that assay. A direct binding claim additionally requires a binding "
    "assay and Kd or Ki. No record here licenses a clinical outcome."
)
LIMIT_STATEMENT = (
    "The audit does not turn a measurement into a response or a response into "
    "an outcome. A record without a clinical endpoint says nothing about a "
    "clinical result."
)
EXCLUDED_BY_DESIGN = (
    "Any prediction of a clinical result.",
    "Any claim that either table licenses a clinical statement.",
    "Selection of a record because it supports a convenient conclusion.",
)


class ProtocolError(ValueError):
    """The on-disk interpretation differs from the frozen compiled rule."""


def expected_fields() -> dict[str, Any]:
    """Return every field that can change the population or a claim."""
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "sources": {
            "chembl": {
                "database": decision.CHEMBL_VERSION,
                "release_date": decision.CHEMBL_RELEASE_DATE,
                "source_protocol_id": decision.PROTOCOL_ID,
                "artifacts": decision.expected_artifacts(),
            },
            "pubchem": {
                "database": "PubChem BioAssay",
                "read_on": "2026-10-21",
                "source_protocol_id": "pubchem-bioassay-endpoint-controls-v1",
                "assays": {
                    str(aid): {
                        "data_bytes": ASSAYS[aid].source_data.record_bytes,
                        "description_bytes": ASSAYS[aid].source_description.record_bytes,
                        "endpoint_labels": list(ASSAYS[aid].endpoint_labels),
                        "endpoint_units": list(ASSAYS[aid].endpoint_units),
                        "response_definition": ASSAYS[aid].direction,
                    }
                    for aid in DECLARED_ASSAYS
                },
            },
        },
        "admitted_measurement": {
            "standard_types": list(decision.ENDPOINT_TYPES),
            "standard_units": decision.STANDARD_UNITS,
            "point_relation": decision.POINT_RELATION,
            "bound_relations": list(decision.BOUND_RELATIONS),
            "exclusion_priority": list(decision.EXCLUSION_PRIORITY),
            "admission_rule": (
                "Apply the decision-unit-scope reader's classification to each activity "
                "row and retain only point and bound rows."
            ),
        },
        "record_kinds": {
            KIND_POINT: (
                "An admitted single endpoint value with a stated type, unit and "
                "equality relation, without a numeric response series."
            ),
            KIND_BOUND: (
                "An admitted single endpoint value with a stated type, unit and "
                "bound relation, without a numeric response series."
            ),
            KIND_RESPONSE: (
                "An admitted assay row with at least five numeric concentration values "
                "and a stated response definition in its assay description."
            ),
            KIND_NONE: "A retained row that satisfies none of the three field rules above.",
        },
        "claim_rule": {
            "endpoint_point": (
                "Only a stated equality with an endpoint value and unit licenses "
                "a point-value statement."
            ),
            "endpoint_bound": (
                "Only a stated bound relation with an endpoint value and unit "
                "licenses a bound statement."
            ),
            "binding_point": (
                "A point additionally needs ChEMBL assay_type B and standard_type "
                "Kd or Ki; other point types are not binding measurements."
            ),
            "binding_bound": (
                "A bound additionally needs ChEMBL assay_type B and standard_type "
                "Kd or Ki; it never licenses an exact binding value."
            ),
            "functional_response": (
                "Only a numeric concentration series with at least five values and a "
                "stated activation or inhibition response definition licenses a "
                "response statement in its assay."
            ),
            "clinical_outcome": "No record in either snapshot licenses this claim.",
            "rule_statement": RULE_STATEMENT,
            "limit_statement": LIMIT_STATEMENT,
        },
        "unmeasurable_routes": UNMEASURABLE_ROUTES,
        "excluded_by_design": list(EXCLUDED_BY_DESIGN),
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(document, dict) or document != expected_fields():
        raise ProtocolError("protocol differs from the frozen field rule")
    return cast(dict[str, Any], document)
