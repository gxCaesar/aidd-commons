"""Frozen rules for auditing committed laboratory return records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROTOCOL_ID = "aidd-commons-lab-return-contract-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.tool-contract-audit-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.tool-contract-audit-summary.v1"
ISSUED_ON = "2026-10-23"
BOUNDARY = (
    "A passing return record establishes a self-describing laboratory artefact. "
    "It does not establish that its measurement is true, that the tool ran in the "
    "environment it names, or that a reader can reproduce the result from the record alone."
)
LIMIT_FIELDS = (
    "boundary",
    "does_not_do",
    "does_not_show",
    "excluded_by_design",
    "interpretation_limits",
    "limit_statement",
    "limits",
)
ERROR_FIELDS = ("run_status", "status", "error", "errors")
REQUIRED_FIELDS = (
    "schema_version",
    "protocol_id",
    "computed_on",
    "software",
    "environment",
    "side_effects",
    "outcome_status",
    "scientific_meaning",
)
NESTED_FIELDS = (
    "software.python",
    "environment.requires",
    "environment.unavailable",
    "environment.can_attest_external_execution",
    "side_effects.allowed_writes",
    "scientific_meaning.licenses",
    "scientific_meaning.does_not_license",
)


class ProtocolError(ValueError):
    """The protocol differs from the frozen decision rules."""


def expected_fields() -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "run_basis": (
            "Fresh independent CPU computation over committed local laboratory return records. "
            "No network, download or accelerator is used."
        ),
        "source": {
            "audited_directory": "labs",
            "exclude_laboratory": "tool_contract_audit",
            "return_glob": "*/summary.json",
            "protocol_file": "protocol.json",
            "readme_file": "README.md",
            "reader": "Local pathlib glob and JSON read at run time",
            "network": "none",
            "download": "none",
        },
        "contract": {
            "schema": {
                "required": {
                    "schema_version": "nonempty_string",
                    "protocol_id": "nonempty_string",
                    "computed_on": "iso_date",
                    "software": "version_map",
                    "environment": "object",
                    "side_effects": "object",
                    "outcome_status": "status",
                    "scientific_meaning": "object",
                },
                "field_coverage": list(
                    dict.fromkeys((*REQUIRED_FIELDS, *NESTED_FIELDS, *LIMIT_FIELDS, *ERROR_FIELDS))
                ),
                "rule": (
                    "Each required field must be present with its declared type and a value. "
                    "Missing and empty or invalid values are distinct failures. "
                    "Extra result fields "
                    "are allowed because laboratories have different outputs."
                ),
            },
            "version": {
                "fields": ["schema_version", "protocol_id"],
                "rule": (
                    "Both fields must be nonempty strings. Without either field the record "
                    "cannot be read as a versioned artefact. This does not validate "
                    "the protocol's science."
                ),
            },
            "environment": {
                "required": [
                    "software.python",
                    "environment.requires",
                    "environment.unavailable",
                    "environment.can_attest_external_execution",
                ],
                "unavailable": [
                    "external execution attestation",
                    "proof of runtime hardware from a return record",
                ],
                "rule": (
                    "The return must name a Python software version and nonempty requirement and "
                    "unavailable lists. can_attest_external_execution must be false. These are "
                    "declarations, not an independent process trace."
                ),
            },
            "side_effects": {
                "field": "side_effects.allowed_writes",
                "rule": (
                    "Declare a list of repository-relative paths that the tool may write. "
                    "An empty list makes a no-write claim checkable against a separate trace. "
                    "The return record alone cannot prove that actual writes obeyed it."
                ),
            },
            "error_states": {
                "field": "outcome_status",
                "statuses": ["complete", "no_result", "halt"],
                "no_usable_result": ["no_result", "halt"],
                "must_stop": ["halt"],
                "observed_field_names": list(ERROR_FIELDS),
                "rule": (
                    "The outcome_status field must have one declared value. no_result licenses no "
                    "usable result and halt requires stopping. Missing status cannot be inferred "
                    "as complete. Existing laboratories have no uniform top-level error field."
                ),
            },
            "scientific_meaning": {
                "field": "scientific_meaning",
                "required": ["licenses", "does_not_license"],
                "limit_field_names": list(LIMIT_FIELDS),
                "rule": (
                    "Both meaning statements must be nonempty strings. A pass licenses only "
                    "a self-describing artefact, not measurement truth or independent "
                    "reproduction. Count existing limit declarations separately without "
                    "treating them as this full statement."
                ),
            },
        },
        "counted_unit": {
            "record": "One laboratory return record at labs/*/summary.json.",
            "admission": (
                "Every immediate laboratory directory with a summary.json, except this "
                "audit, whose return record is the file this audit writes; no sample or "
                "ranking."
            ),
        },
        "excluded_by_design": [
            (
                "Any claim that a passing record establishes that the laboratory's "
                "measurement is correct."
            ),
            "Any claim that a return record proves a tool ran in its named environment.",
            "Any claim that a reader can reproduce a result from the return record alone.",
            "Any ranking of laboratories by record completeness.",
        ],
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(document, dict):
        raise ProtocolError("protocol must be an object")
    expected = expected_fields()
    for key, value in expected.items():
        if document.get(key) != value:
            raise ProtocolError(f"changed protocol field: {key}")
    if set(document) != set(expected):
        raise ProtocolError("unexpected protocol field")
    return document
