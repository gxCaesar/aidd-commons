"""Build and validate a compact task result without copying source bodies."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .analysis import BOUNDARY, audit
from .protocol import DIMENSIONS, AuditError, load_protocol, validate_protocol

SCHEMA_VERSION = "aidd-commons.agent-evaluation-taskset-summary.v1"
PACKAGE_VERSION_FALLBACK = "0.2.0rc1"


def software_versions() -> dict[str, str]:
    try:
        package = version("aidd-commons-labs")
    except PackageNotFoundError:
        package = PACKAGE_VERSION_FALLBACK
    return {"python": platform.python_version(), "aidd-commons-labs": package}


def assemble_summary(
    protocol: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    computed_on: str,
    software: dict[str, str],
) -> dict[str, Any]:
    """Count tasks once and retain incomplete dimensions explicitly."""
    pass_counts = {
        name: sum(result["dimensions"][name] == "pass" for result in results) for name in DIMENSIONS
    }
    incomplete = {
        result["id"]: [name for name in DIMENSIONS if result["dimensions"][name] == "incomplete"]
        for result in results
        if any(result["dimensions"][name] == "incomplete" for name in DIMENSIONS)
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on,
        "software": software,
        "counted_unit": protocol["counted_unit"],
        "task_count": len(results),
        "dimension_pass_counts": pass_counts,
        "passing_task_count": sum(result["passing"] for result in results),
        "per_task": results,
        "incomplete_tasks": incomplete,
        "authorization_boundary_tasks": [
            result["id"] for result in results if result["authorization_boundary_stated"]
        ],
        "boundary_statement": BOUNDARY,
        "enforced_rules": {
            "passing_rule": protocol["passing_rule"],
            "source_resolution": protocol["dimensions"]["source_resolution"],
            "action_authorization": protocol["dimensions"]["action_authorization"],
        },
        "limits": [
            "The set reads committed records and never observes a tool attempting these tasks.",
            "The PaperQA test does not regenerate the retained model answers or source review.",
            "The EGFR inspector does not recompute all locked metrics.",
            "The set has no retained human authorization receipt for the historical locked action.",
            "No task passes all five dimensions.",
        ],
    }
    validate_summary(summary, protocol)
    return summary


def validate_summary(summary: dict[str, Any], protocol: dict[str, Any]) -> None:
    """Refuse inflated passing claims, including a one-dimension false pass."""
    validate_protocol(protocol)
    results = summary.get("per_task")
    if (
        summary.get("schema_version") != SCHEMA_VERSION
        or summary.get("protocol_id") != protocol["protocol_id"]
        or not isinstance(results, list)
        or len(results) != len(protocol["tasks"])
        or summary.get("task_count") != len(results)
    ):
        raise AuditError("summary identity or task count changed")
    if [row.get("id") for row in results] != [task["id"] for task in protocol["tasks"]]:
        raise AuditError("summary task selection changed")
    for row in results:
        dimensions = row.get("dimensions")
        if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
            raise AuditError(f"five results required for {row['id']}")
        if any(value not in {"pass", "incomplete", "fail"} for value in dimensions.values()):
            raise AuditError(f"invalid dimension state for {row['id']}")
        truthful = all(dimensions[name] == "pass" for name in DIMENSIONS)
        if row.get("passing") is not truthful:
            raise AuditError(f"task with a nonpassing dimension reported passing: {row['id']}")
    for row, task in zip(results, protocol["tasks"], strict=True):
        if row["dimensions"] != task["expected_dimensions"]:
            raise AuditError(f"task result differs from frozen expectation: {row['id']}")
    counts = {
        name: sum(row["dimensions"][name] == "pass" for row in results) for name in DIMENSIONS
    }
    incomplete = {
        row["id"]: [name for name in DIMENSIONS if row["dimensions"][name] == "incomplete"]
        for row in results
        if any(row["dimensions"][name] == "incomplete" for name in DIMENSIONS)
    }
    if (
        summary.get("dimension_pass_counts") != counts
        or summary.get("passing_task_count") != sum(row["passing"] for row in results)
        or summary.get("incomplete_tasks") != incomplete
        or summary.get("boundary_statement") != BOUNDARY
        or summary.get("enforced_rules", {}).get("passing_rule") != protocol["passing_rule"]
    ):
        raise AuditError("summary counts or boundary disagree with task results")


def build_summary(
    root: Path,
    protocol_path: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
    protocol_override: dict[str, Any] | None = None,
    results_override: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    protocol = (
        validate_protocol(protocol_override) if protocol_override else load_protocol(protocol_path)
    )
    results = results_override if results_override is not None else audit(root, protocol)
    summary = assemble_summary(
        protocol,
        results,
        computed_on=computed_on or date.today().isoformat(),
        software=software or software_versions(),
    )
    if output is not None:
        output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary
