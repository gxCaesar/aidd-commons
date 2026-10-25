"""Build the compact projection only after live contract checks pass."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .analysis import analyze, check_invariants
from .protocol import AuditError, load_protocol, load_sources

SCHEMA_VERSION = "aidd-commons.open-question-audit-summary.v1"
FALLBACK_PACKAGE_VERSION = "0.2.0rc1"
BOUNDARY = (
    "This audit measures whether the paired records still name a falsifying observation "
    "or missing measurement. It does not establish that any scientific question has been "
    "answered or that the named measurement was performed."
)


def software_versions() -> dict[str, str]:
    try:
        package = version("aidd-commons-labs")
    except PackageNotFoundError:
        package = FALLBACK_PACKAGE_VERSION
    return {
        "python": platform.python_version(),
        "pyyaml": yaml.__version__,
        "aidd-commons-labs": package,
    }


def build_summary(
    root: Path,
    protocol_path: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    result = analyze(load_sources(root, protocol), protocol)
    failures = check_invariants(result, protocol)
    if failures:
        raise AuditError("; ".join(failures))
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or software_versions(),
        "counted_unit": protocol["counted_unit"],
        "topic_count": result["topic_count"],
        "state_counts": result["state_counts"],
        "state_topics": result["state_topics"],
        "open_with_falsifier": result["open_with_falsifier"],
        "open_without_falsifier": result["open_without_falsifier"],
        "held_without_falsifier": result["held_without_falsifier"],
        "missing_measurement": result["missing_measurement"],
        "lowered_topics": result["lowered_topics"],
        "boundary_statement": BOUNDARY,
        "enforced_rules": [
            protocol["falsifier_rule"]["decision"],
            "Every taxonomy topic appears once in each comparison record and one question state.",
            "Open questions without a named falsifier remain in open_without_falsifier.",
        ],
    }
    if output is not None:
        output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary
