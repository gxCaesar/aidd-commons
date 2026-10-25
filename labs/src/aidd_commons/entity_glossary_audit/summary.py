"""Build the compact result only after the frozen contracts pass."""

from __future__ import annotations

import json
import platform
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import rdkit

from aidd_commons.decision_unit_scope.analysis import census_cohort
from aidd_commons.decision_unit_scope.data import load_cached_cohort

from .analysis import AuditError, admitted_rows, audit_rows, check_invariants
from .protocol import (
    PROTOCOL_ID,
    ROW_RULE,
    SUMMARY_SCHEMA_VERSION,
    load_protocol,
)

LIMITS = (
    "The audit does not merge two identifiers, infer what a compound does, call a target a "
    "disease, or treat a document as proof that a measurement is true."
)


def build_summary(
    lab_dir: Path,
    cache_dir: Path,
    *,
    computed_on: str | None = None,
    software: Mapping[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    """Recompute the census and optionally write after all checks pass."""
    protocol = load_protocol(lab_dir / "protocol.json")
    cohort = load_cached_cohort(cache_dir)
    salts = {
        identifier: record.parent_molecule_chembl_id
        for identifier, record in cohort.molecules.items()
        if not record.is_own_parent
    }
    result = audit_rows(admitted_rows(cohort), declared_salts=salts)
    failures = check_invariants(result)
    census = census_cohort(cohort)
    if result["admitted_point_row_count"] != census.admitted_point_count:
        failures.append("point row count differs from decision-unit census")
    if result["admitted_measurement_count"] != census.independent_measurement_count:
        failures.append("measurement count differs from decision-unit census")
    if len(cohort.molecules) != len(protocol["cohort"]["seeds"]):
        failures.append("seed cohort size")
    if len(cohort.parents) != len(protocol["cohort"]["resolved_parents"]):
        failures.append("parent cohort size")
    if failures:
        raise AuditError("; ".join(failures))
    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": dict(software)
        if software is not None
        else {
            "python": platform.python_version(),
            "rdkit": rdkit.__version__,
        },
        "source": {
            "database": protocol["source"]["database"],
            "release_date": protocol["source"]["release_date"],
        },
        "cohort": {
            "declared_seeds": len(cohort.molecules),
            "resolved_parents": len(cohort.parents),
        },
        **result,
        "row_rule": ROW_RULE,
        "limits": LIMITS,
    }
    failures = validate_summary(summary)
    if failures:
        raise AuditError("; ".join(failures))
    if output is not None:
        output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def validate_summary(summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary schema")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary protocol")
    if summary.get("row_rule") != ROW_RULE or summary.get("limits") != LIMITS:
        failures.append("reading rule or limits")
    if not summary.get("computed_on") or not summary.get("software"):
        failures.append("computation date or software")
    if summary.get("cohort") != {"declared_seeds": 15, "resolved_parents": 10}:
        failures.append("cohort size")
    try:
        failures.extend(check_invariants(summary))
    except (KeyError, TypeError, ValueError) as error:
        failures.append(f"missing or invalid summary counts: {error}")
    if any(key in summary for key in ("activities", "canonical_smiles", "activity_ids")):
        failures.append("raw activity data in summary")
    return failures
