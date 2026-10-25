"""Compute and validate the compact nomination-readiness artifact."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope.analysis import census_cohort
from aidd_commons.decision_unit_scope.data import load_cached_cohort
from aidd_commons.decision_unit_scope.pipeline import default_software

from .analysis import AuditError, analyze, check_invariants
from .protocol import EXCLUDED_BY_DESIGN, PROTOCOL_ID, load_protocol

SCHEMA_VERSION = "aidd-commons.nomination-readiness-audit-summary.v1"
LIMITS = [
    "A measurement count does not say a compound is good.",
    "A go compound is not thereby a candidate.",
    "A stop compound is not thereby inactive.",
]


def build_summary(
    protocol_path: Path,
    cache_dir: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    """Validate the protocol and data, then write only a passing summary."""
    load_protocol(protocol_path)
    census = census_cohort(load_cached_cohort(cache_dir))
    result = analyze(census)
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or default_software(),
        "source": {"database": "ChEMBL_37", "release_date": "2026-05-01"},
        **result,
        "does_not_show": LIMITS,
        "excluded_by_design": EXCLUDED_BY_DESIGN,
    }
    failures = validate_summary(summary)
    if failures:
        raise AuditError("; ".join(failures))
    if output is not None:
        output.write_text(
            json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return summary


def validate_summary(summary: dict[str, Any]) -> list[str]:
    failures = check_invariants(summary)
    if summary.get("schema_version") != SCHEMA_VERSION:
        failures.append("wrong summary schema")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("wrong protocol identifier")
    if summary.get("does_not_show") != LIMITS:
        failures.append("missing interpretation limits")
    if summary.get("excluded_by_design") != EXCLUDED_BY_DESIGN:
        failures.append("changed exclusions")
    return failures
