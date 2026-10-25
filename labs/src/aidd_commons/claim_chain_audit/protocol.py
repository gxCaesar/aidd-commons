"""Load the frozen selection and claim boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aidd-commons.claim-chain-audit-protocol.v1"
PROTOCOL_ID = "aidd-commons.claim-chain-audit-v1"
ROLES = (
    "mechanism",
    "target",
    "activity",
    "selectivity",
    "exposure",
    "safety",
    "synthesis",
    "reproducibility",
)
DEPTH_ORDER = ("absent", "mentioned", "explained", "worked", "executable", "assessed")
CHAINS = {
    "candidate-evidence": (
        "t06-mechanism-hypothesis-counterevidence",
        "t06-causal-target-evidence",
        "t07-endpoint-definition",
        "t13-specificity-negative-selection",
        "t08-exposure-pk-endpoint",
        "t08-safety-toxicity-endpoint",
        "t14-route-feasibility-material-safety",
        "t17-reproduction-reporting-receipt",
    ),
    "decision-handoff": (
        "t06-perturbation-genetic-validation",
        "t06-tractability-target-risk",
        "t09-affinity-ranking",
        "t09-screening-selection-repurposing-transfer",
        "t08-pkpd-translational-assumption",
        "t08-metabolism-ddi-risk",
        "t14-retrosynthetic-disconnection",
        "t04-provenance-versioning",
    ),
}
SOURCE_PATHS = {
    "self_record": "catalog/comparisons/systems/aidd-commons.yaml",
    "independent_reading": "catalog/comparisons/reviews/aidd-commons-blind-2026-09-11.yaml",
    "taxonomy": "catalog/comparisons/taxonomy.yaml",
}
BOUNDARY = (
    "A chain establishes that each named link's material exists and says what it says. "
    "It does not establish a claim about a compound, a target or a therapy. "
    "Its endpoints are only the topics it names."
)
RULES = {
    "link_resolution": (
        "A link is resolved only when its self-record evidence list names at least one "
        "declared entry with access opened and a local repository file. An empty "
        "list or only non-opened entries leaves it unresolved. A missing opened "
        "file is refused."
    ),
    "depth_order": list(DEPTH_ORDER),
    "assessed_without_runnable_basis": "worked",
    "licence": (
        "Use the ordinal depth after mapping assessed with no runnable basis to "
        "worked. Worked licenses a worked case or written exercise, not a "
        "measurement. Executable and assessed with a runnable basis license "
        "only the declared task over that basis."
    ),
    "weakest_link": (
        "An unresolved link is weakest. Otherwise the minimum effective depth "
        "sets the chain depth. Report the first topic at that minimum and count "
        "links below the maximum effective depth."
    ),
    "unresolved_breaks_chain": (
        "A chain with any unresolved link cannot be reported as a supported claim."
    ),
    "no_biological_conclusion": (
        "A chain cannot establish a conclusion about a compound, target or therapy."
    ),
}
EXCLUSIONS = [
    "Any claim that a chain establishes a compound, a target or a therapy",
    "Any ranking of chains by completeness",
    "Any use of the self record's depth as evidence that the underlying material is correct",
    "Any conclusion beyond the named topic endpoints",
]


class ProtocolError(ValueError):
    """The protocol no longer matches the declared contract."""


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
            key: {"path": source, "route": "read committed local YAML with PyYAML"}
            for key, source in SOURCE_PATHS.items()
        },
        "network": "none",
        "download": "none",
        "link_roles": list(ROLES),
        "chains": [
            {"id": chain_id, "topic_ids": list(topic_ids)} for chain_id, topic_ids in CHAINS.items()
        ],
        "rules": RULES,
        "counted_unit": "one link in one chain",
        "boundary_statement": BOUNDARY,
        "excluded_by_design": EXCLUSIONS,
    }
    if value != expected:
        changed = [key for key in expected if value.get(key) != expected[key]]
        raise ProtocolError(
            f"changed frozen protocol fields: {', '.join(changed) or 'extra field'}"
        )
    return value
