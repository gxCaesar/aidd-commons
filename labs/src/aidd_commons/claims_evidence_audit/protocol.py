"""Keep the laboratory's selection and state rules frozen."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aidd-commons.claims-evidence-audit-protocol.v1"
PROTOCOL_ID = "aidd-commons.claims-evidence-audit-v1"
STATES = ("direct-observation", "bounded-inference", "unsupported-claim", "unresolved-field")
PROVIDERS = (
    "agil",
    "aidd-commons",
    "build-ai-drug-discovery-pipelines",
    "chembl-training",
    "deepchem-tutorials",
    "european-aidd-network",
    "ml4drug-book",
    "o3dc",
    "openmm-cookbook",
    "practical-cheminformatics",
    "rdkit-cookbook",
    "teachopencadd",
    "therapeutics-data-commons",
)
TOPICS = (
    "t01-evidence-claim-unknown",
    "t01-aidd-decision-unit",
    "t01-source-review-scope",
    "t01-entity-glossary",
)


class ProtocolError(ValueError):
    """The protocol no longer matches the declared frozen contract."""


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(value, dict):
        raise ProtocolError("protocol must be an object")
    expected = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": "2026-10-23",
        "sources": {
            "systems": "catalog/comparisons/systems/*.yaml",
            "taxonomy": "catalog/comparisons/taxonomy.yaml",
            "independent_reading": (
                "catalog/comparisons/reviews/aidd-commons-blind-2026-09-11.yaml"
            ),
            "comparison_record": "site/public/data/comparison.v1.json",
        },
        "states": list(STATES),
        "state_rules": {
            "direct-observation": (
                "Explicit depth with resolvable evidence entries and no depth interval"
            ),
            "bounded-inference": (
                "Explicit unverified depth with resolvable evidence and a lower-upper interval"
            ),
            "unsupported-claim": (
                "Explicit depth with missing evidence, an undeclared evidence reference, "
                "or a missing repository file"
            ),
            "unresolved-field": "Declared default with unverified depth and no evidence",
        },
        "provider_ids": list(PROVIDERS),
        "track": {
            "id": "foundations",
            "strong_provider": "aidd-commons",
            "weak_provider": "agil",
            "topic_ids": list(TOPICS),
        },
        "claims": {
            "most_comprehensive": {
                "condition": (
                    "Own explained lower bound exceeds every external explained upper bound"
                ),
                "correction_window": "Public 30-day correction window must be completed",
            },
            "most_detailed": {
                "condition": (
                    "At least 12 own tracks are executable or assessed and own worked lower bound "
                    "exceeds every external worked upper bound"
                ),
                "correction_window": "Public 30-day correction window must be completed",
            },
        },
        "excluded_by_design": [
            "No ranking on a topic left unresolved by a provider",
            "No re-scoring of any provider or the independent reading",
            "No inference that a laboratory state measures teaching quality",
            "No inference that a default unknown means the provider lacks the topic",
        ],
    }
    if value != expected:
        changed = [key for key in expected if value.get(key) != expected[key]]
        raise ProtocolError(
            f"changed frozen protocol fields: {', '.join(changed) or 'extra field'}"
        )
    return value
