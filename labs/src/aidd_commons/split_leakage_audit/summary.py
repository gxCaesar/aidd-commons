"""Build and validate the small public count summary."""

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

from .analysis import audit_rows, measurements_from_cohort
from .protocol import (
    PROTOCOL_ID,
    RDKIT_VERSION,
    ROUTES,
    SEED,
    SUMMARY_SCHEMA_VERSION,
    TRAIN_FRACTION,
    UNTESTABLE,
    load_protocol,
)


def build_summary(
    lab_dir: Path, cache_dir: Path, *, computed_on: str | None = None
) -> dict[str, Any]:
    load_protocol(lab_dir / "protocol.json")
    cohort = load_cached_cohort(cache_dir)
    census = census_cohort(cohort)
    result = audit_rows(measurements_from_cohort(cohort), seed=SEED, train_fraction=TRAIN_FRACTION)
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {"python": platform.python_version(), "rdkit": rdkit.__version__},
        "source": {"database": "ChEMBL_37", "release_date": "2026-05-01"},
        "cohort": {"declared_seeds": 15, "resolved_parents": 10},
        "admitted_point_row_count": census.admitted_point_count,
        **result,
    }


def validate_summary(summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary schema version")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary protocol id")
    if not summary.get("computed_on") or not summary.get("software"):
        failures.append("summary date or software")
    try:
        count = summary["admitted_measurement_count"]
        split = summary["row_split"]
        grouped = summary["grouped_parent_split"]
        routes = summary["routes"]
        aggregate = summary["aggregate"]
        if split["seed"] != SEED or split["train_rows"] + split["test_rows"] != count:
            failures.append("row split counts")
        if (
            grouped["train_rows"] + grouped["test_rows"] != count
            or grouped["unseen_parent_test_rows"] != grouped["test_rows"]
        ):
            failures.append("grouped split counts")
        if set(routes) != set(ROUTES) or summary["untestable_routes"] != UNTESTABLE:
            failures.append("route declarations")
        if summary["highest_overlap_route"] != max(
            ROUTES, key=lambda name: routes[name]["test_rows_with_train_group"]
        ):
            failures.append("highest overlap route")
        contributing = 0
        maximum = 0
        for name in ROUTES:
            values = routes[name]
            hits = values["test_rows_with_train_group"]
            if not 0 <= hits <= split["test_rows"]:
                failures.append(f"{name} test overlap")
            if not 0 <= values["train_rows_to_hold_out"] <= split["train_rows"]:
                failures.append(f"{name} train holdout")
            if not 0 <= values["shared_groups"] <= min(split["train_rows"], split["test_rows"]):
                failures.append(f"{name} shared groups")
            contributing += hits > 0
            maximum = max(maximum, hits)
        if (
            aggregate["contributing_routes"] != contributing
            or not maximum <= aggregate["contaminated_test_rows"] <= split["test_rows"]
        ):
            failures.append("aggregate counts")
        if (
            count != 486
            or summary["admitted_point_row_count"] != 488
            or summary["cohort"] != {"declared_seeds": 15, "resolved_parents": 10}
        ):
            failures.append("cohort census")
    except (KeyError, TypeError, ValueError) as error:
        failures.append(f"missing or invalid summary count: {error}")
    if '"activities"' in json.dumps(summary) or "canonical_smiles" in json.dumps(summary):
        failures.append("raw activity data in summary")
    return failures


def export_summary(lab_dir: Path, cache_dir: Path, output: Path) -> dict[str, Any]:
    """Check everything before writing, so a refused contract leaves no output."""
    summary = build_summary(lab_dir, cache_dir)
    failures = validate_summary(summary)
    if failures:
        raise ValueError("; ".join(failures))
    # The scaffold route depends on the RDKit release, so the committed reading
    # is only re-based on a run that used the declared one.
    if summary.get("software", {}).get("rdkit") != RDKIT_VERSION:
        raise ValueError(
            "this environment runs RDKit "
            f"{summary['software']['rdkit']} and the protocol declares {RDKIT_VERSION}; "
            "the committed reading is not re-based on another release"
        )
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
