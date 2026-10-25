"""Export only aggregate results after the frozen audit passes."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .analysis import AuditError, analyze, check_invariants, load_release
from .protocol import load_protocol

SCHEMA_VERSION = "aidd-commons.applicability-domain-audit-summary.v1"
LIMITS = (
    "This diagnostic does not decide whether a new molecule is inside a domain, "
    "fit a better model, or turn distance in the chosen representation into a claim "
    "about chemistry."
)


def build_summary(
    protocol_path: Path,
    data_path: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    result = analyze(load_release(data_path))
    failures = check_invariants(result)
    if failures:
        raise AuditError("; ".join(failures))
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or {},
        "cohort": {
            key: round(value, 6) if isinstance(value, float) else value
            for key, value in result.cohort.items()
        },
        "split": result.split,
        "distance_statistics": {
            key: round(value, 6) if isinstance(value, float) else value
            for key, value in result.distance_statistics.items()
        },
        "error_halves": {
            name: {
                key: round(value, 6) if isinstance(value, float) else value
                for key, value in half.items()
            }
            for name, half in result.error_halves.items()
        },
        "does_not_do": LIMITS,
    }
    if output is not None:
        output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
