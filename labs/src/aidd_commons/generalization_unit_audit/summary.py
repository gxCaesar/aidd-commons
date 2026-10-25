"""Build and validate the compact count artifact."""

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

from .analysis import audit_measurements, check_invariants, measurements_from_cohort
from .protocol import (
    PROTOCOL_ID,
    RDKIT_VERSION,
    SUMMARY_SCHEMA_VERSION,
    load_protocol,
)


def build_summary(
    lab_dir: Path, cache_dir: Path, *, computed_on: str | None = None
) -> dict[str, Any]:
    load_protocol(lab_dir / "protocol.json")
    cohort = load_cached_cohort(cache_dir)
    census = census_cohort(cohort)
    result = audit_measurements(measurements_from_cohort(cohort))
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {"python": platform.python_version(), "rdkit": rdkit.__version__},
        "source": {"database": "ChEMBL_37", "release_date": "2026-05-01"},
        "cohort": {"declared_seeds": len(census.seeds), "resolved_parents": len(census.parents)},
        "admitted_point_row_count": census.admitted_point_count,
        **result,
    }
    failures = validate_summary(summary)
    if failures:
        raise ValueError("; ".join(failures))
    return summary


def validate_summary(summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary schema version")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary protocol id")
    if summary.get("cohort") != {"declared_seeds": 15, "resolved_parents": 10}:
        failures.append("cohort size")
    if summary.get("source") != {"database": "ChEMBL_37", "release_date": "2026-05-01"}:
        failures.append("source release")
    software = summary.get("software")
    if not isinstance(software, dict) or not software.get("python") or not software.get("rdkit"):
        failures.append("software versions")
    computed_on = summary.get("computed_on")
    try:
        if (
            not isinstance(computed_on, str)
            or date.fromisoformat(computed_on).isoformat() != computed_on
        ):
            failures.append("computation date")
    except ValueError:
        failures.append("computation date")
    count = summary.get("admitted_measurement_count")
    point_count = summary.get("admitted_point_row_count")
    if (
        not isinstance(count, int)
        or not isinstance(point_count, int)
        or not (0 < count <= point_count)
    ):
        failures.append("admitted measurements and point rows")
    failures.extend(check_invariants(summary))
    serialized = json.dumps(summary)
    if '"activities"' in serialized or "canonical_smiles" in serialized:
        failures.append("raw activity data in summary")
    return failures


def export_summary(lab_dir: Path, cache_dir: Path, output: Path) -> dict[str, Any]:
    """Complete all checks before touching the output path."""
    summary = build_summary(lab_dir, cache_dir)
    if summary["software"]["rdkit"] != RDKIT_VERSION:
        raise ValueError("RDKit version differs from the frozen scaffold computation")
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
