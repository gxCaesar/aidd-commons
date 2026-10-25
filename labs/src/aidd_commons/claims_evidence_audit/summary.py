"""Build a compact projection only after the live source contracts pass."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .analysis import AuditError, analyze, check_invariants
from .protocol import load_protocol
from .records import load_sources

SCHEMA_VERSION = "aidd-commons.claims-evidence-audit-summary.v1"


def build_summary(
    root: Path,
    protocol_path: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    bundle = load_sources(root, protocol)
    result = analyze(bundle, protocol, root)
    failures = check_invariants(result, protocol)
    if failures:
        raise AuditError("; ".join(failures))
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or {},
        "examined_provider_ids": protocol["provider_ids"],
        "examined_track_id": protocol["track"]["id"],
        "examined_topic_ids": protocol["track"]["topic_ids"],
        "source_counts": result["source_counts"],
        "state_counts": result["state_counts"],
        "unsupported_claims": result["unsupported_claims"],
        "disagreements": result["disagreements"],
        "claims": result["claims"],
        "interpretation_limits": [
            "A default unknown does not establish that a provider lacks the topic.",
            "The project's own depth is its stated floor, not a measure of teaching quality.",
        ],
    }
    if output is not None:
        output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary
