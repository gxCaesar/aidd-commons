"""Build and audit the small profile summary against the existing join."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy
import rdkit

from aidd_commons.multi_endpoint_integration.summary import build_summary as build_joined_summary

from .analysis import apply_profile
from .protocol import (
    BOUNDARY_STATEMENT,
    PACKAGE_VERSION_FALLBACK,
    PROTOCOL_ID,
    REQUIREMENTS,
    RULES,
    SUMMARY_SCHEMA_VERSION,
    load_protocol_document,
)
from .protocol import expected_contract as expected_protocol


class SummaryContractError(ValueError):
    """A result violates the profile or differs from the cached measurements."""


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


def compute(
    cache_root: Path, *, computed_on: str | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Use the owning readers and the existing parent join without network access."""
    joined = build_joined_summary(cache_root)
    evaluations, result = apply_profile(REQUIREMENTS, joined["profiles"])
    result["counts"].update(
        {
            "source_union_compound_count": joined["counts"]["cohort_compound_count"],
            "single_family_excluded_count": joined["counts"]["one_family_compound_count"],
        }
    )
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": software_versions(),
        "profile": expected_protocol()["profile"],
        **result,
        "boundary_statement": BOUNDARY_STATEMENT,
        "rules": RULES,
    }
    audit_summary(summary)
    return summary, evaluations


def build_summary(cache_root: Path, *, computed_on: str | None = None) -> dict[str, Any]:
    return compute(cache_root, computed_on=computed_on)[0]


def audit_summary(summary: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "profile",
        "counts",
        "per_gate",
        "per_preference",
        "unmeasured_requirements",
        "satisfying_parent_ids",
        "no_contradictions_note",
        "boundary_statement",
        "rules",
    }
    if set(summary) != required:
        raise SummaryContractError("summary has missing or undeclared fields")
    if summary["schema_version"] != SUMMARY_SCHEMA_VERSION or summary["protocol_id"] != PROTOCOL_ID:
        raise SummaryContractError("summary schema or protocol differs")
    try:
        date.fromisoformat(summary["computed_on"])
    except (TypeError, ValueError) as error:
        raise SummaryContractError("invalid computation date") from error
    if (
        summary["profile"] != expected_protocol()["profile"]
        or summary["rules"] != RULES
        or summary["boundary_statement"] != BOUNDARY_STATEMENT
    ):
        raise SummaryContractError("profile, rule or boundary contract differs")
    counts = summary["counts"]
    if set(counts) != {
        "cohort_compound_count",
        "contradicted_compound_count",
        "no_observed_gate_failure_count",
        "profile_satisfying_compound_count",
        "source_union_compound_count",
        "single_family_excluded_count",
    }:
        raise SummaryContractError("count fields differ")
    cohort = counts["cohort_compound_count"]
    if (
        cohort != counts["source_union_compound_count"] - counts["single_family_excluded_count"]
        or cohort
        != counts["contradicted_compound_count"] + counts["no_observed_gate_failure_count"]
        or counts["profile_satisfying_compound_count"] != len(summary["satisfying_parent_ids"])
    ):
        raise SummaryContractError("cohort or satisfying counts do not partition")
    if len(summary["satisfying_parent_ids"]) != len(set(summary["satisfying_parent_ids"])):
        raise SummaryContractError("duplicate satisfying parent")
    gates = {requirement["id"] for requirement in REQUIREMENTS if requirement["kind"] == "gate"}
    preferences = {
        requirement["id"] for requirement in REQUIREMENTS if requirement["kind"] == "preference"
    }
    if set(summary["per_gate"]) != gates or set(summary["per_preference"]) != preferences:
        raise SummaryContractError("requirement counts are incomplete")
    failed_ids: set[str] = set()
    for identifier, item in summary["per_gate"].items():
        if set(item) != {"pass", "fail", "unmeasured", "failing_parent_ids"}:
            raise SummaryContractError(f"gate fields differ for {identifier}")
        if item["pass"] + item["fail"] + item["unmeasured"] != cohort:
            raise SummaryContractError(f"gate counts do not partition for {identifier}")
        ids = item["failing_parent_ids"]
        if item["fail"] != len(ids) or len(ids) != len(set(ids)):
            raise SummaryContractError(f"failing parents differ for {identifier}")
        failed_ids.update(ids)
    for identifier, item in summary["per_preference"].items():
        if set(item) != {"met", "miss", "unmeasured"}:
            raise SummaryContractError(f"preference fields differ for {identifier}")
        if item["met"] + item["miss"] + item["unmeasured"] != cohort:
            raise SummaryContractError(f"preference counts do not partition for {identifier}")
    if len(failed_ids) != counts["contradicted_compound_count"]:
        raise SummaryContractError("contradicted parent count differs from failed gates")
    if failed_ids.intersection(summary["satisfying_parent_ids"]):
        raise SummaryContractError("a gate-failing compound is reported as profile-satisfying")
    if len(summary["satisfying_parent_ids"]) > min(
        item["pass"] for item in summary["per_gate"].values()
    ):
        raise SummaryContractError("an unmeasured gate is reported as profile-satisfying")
    expected_unmeasured = [
        item["id"]
        for item in REQUIREMENTS
        if (
            summary["per_gate"].get(item["id"], summary["per_preference"].get(item["id"]))[
                "unmeasured"
            ]
            == cohort
        )
    ]
    if summary["unmeasured_requirements"] != expected_unmeasured:
        raise SummaryContractError("unmeasured requirement list differs")
    if summary["no_contradictions_note"] is None and not failed_ids:
        raise SummaryContractError("a profile passed by every compound must say so")
    if summary["no_contradictions_note"] is not None and failed_ids:
        raise SummaryContractError("no-contradictions note conflicts with failed gates")


def check_summary(committed: dict[str, Any], computed: dict[str, Any]) -> None:
    audit_summary(committed)
    audit_summary(computed)
    for field, value in computed.items():
        if field not in {"computed_on", "software"} and committed[field] != value:
            raise SummaryContractError(f"committed {field} differs from cached computation")


def export_summary(
    lab_dir: Path,
    cache_root: Path,
    output_path: Path,
    *,
    candidate: dict[str, Any] | None = None,
) -> None:
    """Never write if protocol, data, candidate or invariants fail validation."""
    load_protocol_document(lab_dir / "protocol.json")
    computed = build_summary(cache_root)
    selected = candidate if candidate is not None else computed
    check_summary(selected, computed)
    output_path.write_text(
        json.dumps(selected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
