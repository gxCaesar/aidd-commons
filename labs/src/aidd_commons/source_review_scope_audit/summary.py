"""Export a compact projection only after source checks pass."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .analysis import AuditError, analyze, check_invariants
from .protocol import EXAMINED_IDS, load_protocol
from .records import load_catalogue, load_reading

SCHEMA_VERSION = "aidd-commons.source-review-scope-audit-summary.v1"


def build_summary(
    root: Path,
    protocol_path: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    reading = load_reading(root, protocol)
    result = analyze(load_catalogue(root / "catalog/resources", EXAMINED_IDS), EXAMINED_IDS)
    failures = check_invariants(result, EXAMINED_IDS)
    if failures:
        raise AuditError("; ".join(failures))
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or {},
        "examined_record_ids": list(EXAMINED_IDS),
        "independent_reading": reading,
        "records": [
            {
                "id": row["id"],
                "evidence_entries": row["evidence_entries"],
                "part_counts": row["part_counts"],
                "special_counts": row["special_counts"],
                "claim_counts": row["claim_counts"],
            }
            for row in result["records"]
        ],
        "totals": result["totals"],
        "unresolved_claim_references": result["unresolved_claim_references"],
        "unmeasurable_routes": protocol["unmeasurable_routes"],
        "excluded_by_design": protocol["excluded_by_design"],
        "interpretation_limits": [
            "The audit does not open linked pages and cannot confirm what they say.",
            "An entry without a date does not establish that it is unreliable.",
        ],
    }
    if output is not None:
        output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary
