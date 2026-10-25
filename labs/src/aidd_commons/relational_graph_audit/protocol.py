"""Freeze the graph interpretation independently of catalogue content."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aidd-commons.relational-graph-audit-protocol.v1"
PROTOCOL_ID = "aidd-commons.relational-graph-audit-v1"
NODE_TYPES = (
    "agent",
    "benchmark",
    "database",
    "dataset",
    "model",
    "model-asset",
    "paper",
    "software",
    "standard",
    "tutorial",
)
EDGE_TYPES = (
    "analyses",
    "measured-by",
    "demonstrates",
    "implements",
    "reproduces",
    "successor-to",
    "surfaced-by",
    "used-by",
    "uses",
)
EXPECTED_NODE_COUNT = 228


class ProtocolError(ValueError):
    """The local protocol differs from the frozen interpretation."""


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProtocolError(f"cannot read protocol: {path}") from error
    if not isinstance(value, dict):
        raise ProtocolError("protocol must be an object")
    expected: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": "2026-10-23",
        "source": "catalog/resources/*.yaml",
        "expected_node_count": EXPECTED_NODE_COUNT,
        "node_types": list(NODE_TYPES),
        "edge_types": list(EDGE_TYPES),
        "candidate_edge_rule": (
            "An unordered pair is a candidate when its records share at least one task or at "
            "least one stage and neither record declares a relation to the other. "
            "A candidate is not a declared relation."
        ),
        "provenance_rule": (
            "A directed edge is evidenced only by evidence entries in its declaring source "
            "record whose supports list names relations. Without such an entry it is unevidenced."
        ),
        "isolated_node_rule": (
            "A record is isolated when it declares no outgoing relation, even if another record "
            "points to it."
        ),
        "degree_rule": (
            "Total degree counts incoming and outgoing declared edge instances; "
            "candidate edges do not contribute."
        ),
        "excluded_by_design": [
            "Inference of causality or mechanism from a declared relation",
            "A claim that two candidate edges should be merged",
            "Prediction of a relation the catalogue does not declare",
        ],
    }
    if value != expected:
        changed = [key for key in expected if value.get(key) != expected[key]]
        raise ProtocolError(
            f"changed frozen protocol fields: {', '.join(changed) or 'extra field'}"
        )
    return value
