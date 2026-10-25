"""Validate the frozen selection and vocabulary before reading the catalogue."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

PROTOCOL_ID = "asset-openness-seven-fields-v1"
SCHEMA_VERSION = "aidd-commons.asset-openness-audit-protocol.v1"
DIMENSIONS = (
    "inference_code",
    "training_code",
    "weights",
    "architecture",
    "data_recipe",
    "training_data",
    "evaluation_code",
)
OPENNESS_VALUES = ("available", "not_available", "not_applicable", "unverified")
LIFECYCLE_VALUES = ("active", "legacy", "superseded", "unmaintained", "withdrawn", "unverified")
ACCESS_VALUES = (
    "open_source",
    "open_weights",
    "source_available",
    "research_only",
    "gated",
    "api_only",
    "closed",
    "unverified",
)
EXAMINED_IDS = (
    "db-alphafold-db",
    "model-alphafold-2",
    "model-alphafold-3-inference",
    "model-boltz-1",
    "model-boltz-2",
    "model-chai-1",
    "model-chai-2",
    "model-protenix",
    "model-openfold",
    "model-rfdiffusion",
    "model-rfdiffusion2",
    "model-esm-c",
    "model-esmc",
    "model-boltzgen",
    "model-alphaproteo",
    "tool-bindcraft",
    "tool-gnina",
    "tool-smina",
    "tool-openmm",
    "tool-rdkit",
    "tool-psi4",
    "db-rcsb-pdb",
    "db-uniprot",
    "db-skempi",
)
REVIEW_DATE_RULE = "last_verified is a valid YYYY-MM-DD calendar date"
EXCLUSIONS = (
    "Prediction of what a resource licence permits in a specific use",
    "Legal opinion about whether a licence is enforceable",
    "A claim that a resource is usable, safe or appropriate for a purpose",
)


class ProtocolError(ValueError):
    """The protocol differs from the declared frozen contract."""


def calendar_date(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(value, dict):
        raise ProtocolError("protocol must be an object")
    expected: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": "2026-10-23",
        "source": "catalog/resources/*.yaml",
        "dimensions": list(DIMENSIONS),
        "claim_values": {
            "openness": list(OPENNESS_VALUES),
            "lifecycle_status": list(LIFECYCLE_VALUES),
            "access_level": list(ACCESS_VALUES),
            "license_fields": ["name", "scope", "evidence"],
        },
        "examined_record_ids": list(EXAMINED_IDS),
        "review_date_rule": REVIEW_DATE_RULE,
        "excluded_by_design": list(EXCLUSIONS),
    }
    if value != expected:
        changed = [key for key in expected if value.get(key) != expected[key]]
        detail = ", ".join(changed) or "extra field"
        raise ProtocolError(f"changed frozen protocol fields: {detail}")
    return value
