"""Load the declared, local-only question audit protocol and source records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

SCHEMA_VERSION = "aidd-commons.open-question-audit-protocol.v1"
PROTOCOL_ID = "aidd-commons.open-question-audit-v1"
SOURCE_PATHS = {
    "self_record": "catalog/comparisons/systems/aidd-commons.yaml",
    "independent_reading": "catalog/comparisons/reviews/aidd-commons-blind-2026-09-11.yaml",
    "taxonomy": "catalog/comparisons/taxonomy.yaml",
}
STATES = (
    "open",
    "settled by measurement",
    "held by a reading",
    "lowered by a reading",
    "unexamined",
)
FAMILIES = (
    "runnable task",
    "empirical observation",
    "comparison and control",
    "scope and transfer",
    "uncertainty and independence",
    "record and provenance",
)


class AuditError(ValueError):
    """A source or audit contract cannot be used."""


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AuditError(f"cannot read protocol: {path}") from error
    if not isinstance(value, dict):
        raise AuditError("protocol must be an object")
    if value.get("schema_version") != SCHEMA_VERSION or value.get("protocol_id") != PROTOCOL_ID:
        raise AuditError("unexpected protocol identity")
    if value.get("issued_on") != "2026-10-23" or value.get("counted_unit") != "one taxonomy topic":
        raise AuditError("protocol date or counted unit changed")
    sources = value.get("sources")
    if (
        not isinstance(sources, dict)
        or {
            key: entry.get("path") if isinstance(entry, dict) else None
            for key, entry in sources.items()
        }
        != SOURCE_PATHS
    ):
        raise AuditError("protocol source selection changed")
    if value.get("question_states") != list(STATES) or set(
        value.get("missing_measurement_families", {})
    ) != set(FAMILIES):
        raise AuditError("protocol states or families changed")
    state_rule = value.get("state_rule", {})
    falsifier_rule = value.get("falsifier_rule", {})
    if state_rule.get("order") != [STATES[i] for i in (3, 2, 1, 0, 4)]:
        raise AuditError("protocol state priority changed")
    for block, keys in (
        (
            state_rule,
            (
                "lowered_phrases",
                "held_phrases",
                "measurement_subjects",
                "measurement_verbs",
                "closed_reason_phrases",
                "bounded_decision_phrases",
            ),
        ),
        (falsifier_rule, ("discriminating_phrases", "missing_cues", "generic_only")),
        (value["missing_measurement_families"], FAMILIES),
    ):
        for key in keys:
            words = block.get(key)
            if (
                not isinstance(words, list)
                or not words
                or not all(isinstance(word, str) and word.strip() for word in words)
            ):
                raise AuditError(f"protocol vocabulary is missing: {key}")
    if "more work is needed" not in falsifier_rule["generic_only"]:
        raise AuditError("generic-only counterexample is missing")
    return value


def load_sources(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    loaded = {}
    for key, relative in SOURCE_PATHS.items():
        declared = protocol["sources"][key]["path"]
        if declared != relative:
            raise AuditError(f"source route changed: {key}")
        try:
            record = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise AuditError(f"cannot read source: {relative}") from error
        if not isinstance(record, dict):
            raise AuditError(f"source must be a mapping: {relative}")
        loaded[key] = record
    return loaded
