"""Build and audit the compact cross-domain decision summary."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy
import rdkit

from aidd_commons.multi_endpoint_integration.summary import build_summary as build_integration

from .analysis import (
    audit_decisions,
    blocking_input_counts,
    input_state_counts,
    make_decisions,
    next_decision_counts,
)
from .protocol import (
    BOUNDARY_STATEMENT,
    INPUTS,
    PACKAGE_VERSION_FALLBACK,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
    TEACHING_CASES,
    expected_contract,
    load_protocol_document,
)


class SummaryContractError(ValueError):
    """The summary violates the decision rule or differs from cached evidence."""


def software_versions() -> dict[str, str]:
    try:
        package_version = version("aidd-commons-labs")
    except PackageNotFoundError:
        package_version = PACKAGE_VERSION_FALLBACK
    return {
        "aidd_commons_labs": package_version,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "rdkit": rdkit.__version__,
    }


def build_summary(cache_root: Path, *, computed_on: str | None = None) -> dict[str, Any]:
    """Read the owning caches and execute the rule on both cohorts."""
    integration = build_integration(cache_root, computed_on=computed_on)
    teaching, measured = make_decisions(integration["profiles"], list(TEACHING_CASES))
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": software_versions(),
        "inputs": list(INPUTS),
        "teaching_decisions": teaching,
        "measured_decisions": measured,
        "teaching_blocking_counts": blocking_input_counts(teaching),
        "teaching_next_decision_counts": next_decision_counts(teaching),
        "measured_blocking_counts": blocking_input_counts(measured),
        "measured_next_decision_counts": next_decision_counts(measured),
        "measured_input_state_counts": input_state_counts(measured),
        "measured_complete_count": sum(decision["complete"] for decision in measured),
        "teaching_complete_count": sum(decision["complete"] for decision in teaching),
        "measured_candidate_count": len(measured),
        "boundary_statement": BOUNDARY_STATEMENT,
        "rules": expected_contract()["rules"],
    }
    audit_summary(summary)
    return summary


def audit_summary(summary: dict[str, Any]) -> None:
    """Check the decision accounting without reading a cache."""
    required = {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "inputs",
        "teaching_decisions",
        "measured_decisions",
        "teaching_blocking_counts",
        "teaching_next_decision_counts",
        "measured_blocking_counts",
        "measured_next_decision_counts",
        "measured_input_state_counts",
        "measured_complete_count",
        "teaching_complete_count",
        "measured_candidate_count",
        "boundary_statement",
        "rules",
    }
    if set(summary) != required:
        raise SummaryContractError("summary fields differ from contract")
    if summary["schema_version"] != SUMMARY_SCHEMA_VERSION or summary["protocol_id"] != PROTOCOL_ID:
        raise SummaryContractError("summary version differs")
    try:
        date.fromisoformat(summary["computed_on"])
    except (TypeError, ValueError) as error:
        raise SummaryContractError("invalid computation date") from error
    if (
        summary["inputs"] != list(INPUTS)
        or summary["rules"] != expected_contract()["rules"]
        or summary["boundary_statement"] != BOUNDARY_STATEMENT
    ):
        raise SummaryContractError("input, rule or boundary differs")
    if not isinstance(summary["software"], dict) or not all(
        isinstance(value, str) and value for value in summary["software"].values()
    ):
        raise SummaryContractError("software versions are invalid")
    teaching = summary["teaching_decisions"]
    measured = summary["measured_decisions"]
    if not teaching or not measured:
        raise SummaryContractError("no decision was executed")
    try:
        audit_decisions(teaching + measured)
    except (KeyError, TypeError, ValueError) as error:
        raise SummaryContractError(str(error)) from error
    if [decision["id"] for decision in teaching] != [case["id"] for case in TEACHING_CASES]:
        raise SummaryContractError("the teaching cases differ from the frozen table")
    if summary["teaching_blocking_counts"] != blocking_input_counts(teaching):
        raise SummaryContractError("teaching blocking counts differ")
    if summary["teaching_next_decision_counts"] != next_decision_counts(teaching):
        raise SummaryContractError("teaching next decision counts differ")
    if summary["measured_blocking_counts"] != blocking_input_counts(measured):
        raise SummaryContractError("measured blocking counts differ")
    if summary["measured_next_decision_counts"] != next_decision_counts(measured):
        raise SummaryContractError("measured next decision counts differ")
    if summary["measured_input_state_counts"] != input_state_counts(measured):
        raise SummaryContractError("measured input state counts differ")
    if summary["measured_candidate_count"] != len(measured):
        raise SummaryContractError("the measured candidate count differs")
    if summary["measured_complete_count"] != sum(decision["complete"] for decision in measured):
        raise SummaryContractError("the measured complete count differs")
    if summary["teaching_complete_count"] != sum(decision["complete"] for decision in teaching):
        raise SummaryContractError("the teaching complete count differs")


def check_summary(committed: dict[str, Any], computed: dict[str, Any]) -> None:
    """Refuse a committed summary that differs from the cached computation."""
    audit_summary(committed)
    audit_summary(computed)
    for field, value in computed.items():
        if field not in {"computed_on", "software"} and committed[field] != value:
            raise SummaryContractError(f"committed {field} differs from cached computation")


def export_summary(
    lab_dir: Path,
    cache_root: Path,
    output_path: Path,
) -> None:
    """Write the summary only after the frozen protocol and the cached checks pass."""
    load_protocol_document(lab_dir / "protocol.json")
    computed = build_summary(cache_root)
    check_summary(computed, computed)
    output_path.write_text(
        json.dumps(computed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
