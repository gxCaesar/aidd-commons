"""Frozen multi-endpoint contract, checked before data are read or output is written."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope.protocol import (
    ARTIFACT_BYTE_LENGTHS,
    BOUND_RELATIONS,
    CHEMBL_LICENSE_NAME,
    CHEMBL_LICENSE_URL,
    CHEMBL_RELEASE_DATE,
    CHEMBL_STATUS_URL,
    CHEMBL_VERSION,
    COHORT_PARENTS,
    COHORT_SEEDS,
    ENDPOINT_TYPES,
    EXCLUSION_PRIORITY,
    POINT_RELATION,
    expected_artifacts,
)
from aidd_commons.decision_unit_scope.protocol import (
    STANDARD_UNITS as DECISION_STANDARD_UNITS,
)

PROTOCOL_ID = "chembl37-multi-endpoint-tradeoff-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.multi-endpoint-tradeoff-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.multi-endpoint-tradeoff-summary.v1"
ISSUED_ON = "2026-10-23"
STANDARD_UNITS = DECISION_STANDARD_UNITS
NAMED_FAMILIES = ("efficacy", "toxicity", "exposure")
FAMILIES = (*NAMED_FAMILIES, "other")
# These are response-potency proxies, not demonstrations of therapeutic efficacy.
# Affinity types have no unambiguous home in the three named families.
TYPE_TO_FAMILY = {
    "AC50": "efficacy",
    "EC50": "efficacy",
    "IC50": "efficacy",
    "Kd": "other",
    "Ki": "other",
}
UNMAPPED_FAMILY = "other"
STATISTICS = (
    "independent_measurement_count",
    "distinct_document_count",
    "distinct_assay_count",
    "median",
    "interquartile_range",
    "compounds_without_measurement_count",
)
QUANTILE_METHOD = "linear"
FAMILY_INTERPRETATION = (
    "AC50, EC50 and IC50 are response-potency proxies only, not proof of therapeutic efficacy. "
    "Kd and Ki enter other as affinity measurements. The admitted type vocabulary cannot "
    "identify toxicity or exposure, so those families remain unmeasured in this snapshot."
)
STATISTICS_DEFINITION = (
    "One independent point measurement is one parent, assay, document and standard type. "
    "Replicate rows sharing this key are represented by their median. Family medians and "
    "linear 25th and 75th percentiles summarize these measurements in nM. Empty families "
    "have null statistics. The IQR is Q3 minus Q1. Counts are exact for this declared cohort, "
    "not population estimates."
)
EXCLUDED_BY_DESIGN = [
    "any blended or weighted score across endpoint families",
    "any performance estimate or clinical efficacy, toxicity or exposure inference",
    "any claim that endpoint families can be combined into a single ranking",
    "treating an unmeasured family as safe, clean or bioavailable",
    "pooling censored bounds with point values or treating response potency as a "
    "target-independent effect",
]


class ProtocolContractError(ValueError):
    """The on-disk contract differs from the compiled-in protocol."""


def expected_contract() -> dict[str, Any]:
    """Return every load-bearing field and its fixed value."""
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "source": {
            "database": CHEMBL_VERSION,
            "release_date": CHEMBL_RELEASE_DATE,
            "status_url": CHEMBL_STATUS_URL,
            "licence": {"name": CHEMBL_LICENSE_NAME, "url": CHEMBL_LICENSE_URL},
        },
        "cohort": {
            "seeds": [
                {"molecule_chembl_id": molecule_id, "pref_name": name}
                for molecule_id, name in COHORT_SEEDS
            ],
            "resolved_parents": list(COHORT_PARENTS),
        },
        "endpoint": {
            "standard_types": list(ENDPOINT_TYPES),
            "standard_units": STANDARD_UNITS,
            "point_relation": POINT_RELATION,
            "bound_relations": list(BOUND_RELATIONS),
            "exclusion_priority": list(EXCLUSION_PRIORITY),
            "measurement_key": ["assay_chembl_id", "document_chembl_id", "standard_type"],
        },
        "family_rule": {
            "families": list(FAMILIES),
            "type_to_family": TYPE_TO_FAMILY,
            "unmapped_family": UNMAPPED_FAMILY,
            "interpretation": FAMILY_INTERPRETATION,
        },
        "statistics": {
            "per_family": list(STATISTICS),
            "quantile_method": QUANTILE_METHOD,
            "unit": STANDARD_UNITS,
            "definition": STATISTICS_DEFINITION,
        },
        "artifacts": expected_artifacts(),
        "excluded_by_design": EXCLUDED_BY_DESIGN,
    }


def validate_protocol_document(document: dict[str, Any]) -> None:
    """Refuse changes to any decision-bearing field or missing disclosures."""
    for field, expected in expected_contract().items():
        if document.get(field) != expected:
            raise ProtocolContractError(f"protocol {field} differs from the frozen contract")
    excluded = document.get("excluded_by_design")
    if (
        not isinstance(excluded, list)
        or len(excluded) < 3
        or not all(isinstance(item, str) and item.strip() for item in excluded)
    ):
        raise ProtocolContractError("protocol excluded_by_design is incomplete")


def load_protocol_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError(f"cannot read protocol: {error}") from error
    if not isinstance(document, dict):
        raise ProtocolContractError("protocol must be a JSON object")
    validate_protocol_document(document)
    return document


def validate_cache_lengths(cache_dir: Path) -> None:
    """Use the sibling reader's frozen byte-length contract for every artefact."""
    for name, expected in ARTIFACT_BYTE_LENGTHS.items():
        path = cache_dir / name
        if not path.is_file() or path.stat().st_size != expected:
            raise ProtocolContractError(f"{name}: missing or different frozen byte length")
