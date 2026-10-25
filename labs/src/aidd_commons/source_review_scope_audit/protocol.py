"""Validate the frozen source-review selection and field rules."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aidd-commons.source-review-scope-audit-protocol.v1"
PROTOCOL_ID = "aidd-commons.source-review-scope-audit-v1"
EXAMINED_IDS = ("db-rcsb-pdb", "db-uniprot", "tool-rdkit", "model-boltz-2")
PART_FIELDS = {
    "surface": "url",
    "version": "version",
    "date": "reviewed_on",
    "scope": "reviewed_scope",
}
PART_RULES = {
    "surface": (
        "An absolute HTTP(S) URL with a host names a page or repository surface; "
        "a label alone is only a name."
    ),
    "version": (
        "A nonempty dedicated release, tag or dated-policy value carries the version; "
        "text in the URL or label only names it in text."
    ),
    "date": (
        "A valid YYYY-MM-DD calendar date on the evidence entry carries the date; "
        "a date in its label is named in text, while record-level last_verified "
        "is not an entry date."
    ),
    "scope": (
        "A nonempty dedicated description of exact reviewed material carries scope; "
        "a label naming a document type is named-in-text, but a generic project "
        "or repository name is absent. supports maps claims, not reviewed material."
    ),
}
SOURCES = {
    "catalogue": "catalog/resources/*.yaml",
    "independent_reading": "catalog/comparisons/reviews/aidd-commons-blind-2026-09-11.yaml",
    "own_comparison_record": "catalog/comparisons/systems/aidd-commons.yaml",
}
ROUTES = (
    "linked-page-content",
    "moving-url-revision",
    "review-thoroughness",
    "licence-permission",
)
ROUTE_REASONS = (
    "The audit reads the evidence entry but does not open the linked page, "
    "so it cannot verify the page's content.",
    "A moving URL without an entry-level release or tag does not identify "
    "the exact revision reviewed.",
    "Catalogue fields do not record the completeness of a human review.",
    "A reference and a scope note do not determine the legal permission for a particular use.",
)
EXCLUSIONS = (
    "Any claim that a linked page says what its entry says it says",
    "Any legal reading of what a licence permits",
    "Any judgement about whether a review was thorough",
)


class ProtocolError(ValueError):
    """The protocol does not satisfy its frozen contract."""


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
    fixed = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": "2026-10-23",
        "sources": SOURCES,
        "topic_id": "t01-source-review-scope",
        "recorded_depth": "assessed",
        "independent_depth": "assessed",
        "examined_record_ids": list(EXAMINED_IDS),
        "missing_record_rule": "Refuse an identifier absent from the committed resource catalogue.",
        "parts": {
            part: {"field": field, "rule": PART_RULES[part]} for part, field in PART_FIELDS.items()
        },
        "unmeasurable_routes": [
            {"route": route, "reason": reason}
            for route, reason in zip(ROUTES, ROUTE_REASONS, strict=True)
        ],
        "excluded_by_design": list(EXCLUSIONS),
    }
    if value != fixed:
        changed = [key for key in fixed if value.get(key) != fixed[key]]
        raise ProtocolError(
            f"changed frozen protocol fields: {', '.join(changed) or 'extra field'}"
        )
    return value
