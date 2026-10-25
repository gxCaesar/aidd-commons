"""Build the compact committed result only after all contracts pass."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .analysis import AuditError, analyze, check_invariants
from .protocol import EXAMINED_IDS, load_protocol
from .records import load_catalogue

SCHEMA_VERSION = "aidd-commons.asset-openness-audit-summary.v1"


def build_summary(
    protocol_path: Path,
    catalogue_dir: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    result = analyze(load_catalogue(catalogue_dir, EXAMINED_IDS), EXAMINED_IDS)
    failures = check_invariants(result, EXAMINED_IDS)
    if failures:
        raise AuditError("; ".join(failures))
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or {},
        "examined_record_ids": list(EXAMINED_IDS),
        "scope_limit_rule": (
            "Case-insensitive whole-word match for only, not, no separate terms or does not; "
            "this is a text flag, not legal interpretation."
        ),
        "records": [
            {
                "id": row["id"],
                "openness": {name: claim["value"] for name, claim in row["dimensions"].items()},
                "license_names": [item["name"] for item in row["licenses"]],
                "access_level": row["access_level"]["value"],
                "last_verified": row["last_verified"],
                "seven_fields_separate": row["seven_fields_separate"],
                "all_claim_evidence_resolves": row["all_claim_evidence_resolves"],
                "all_licenses_scoped": row["all_licenses_scoped"],
                "scope_limits_grant": row["scope_limits_grant"],
            }
            for row in result["records"]
        ],
        "examined_counts": result["examined_counts"],
        "whole_catalogue": result["whole_catalogue"],
    }
    if output is not None:
        output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary
