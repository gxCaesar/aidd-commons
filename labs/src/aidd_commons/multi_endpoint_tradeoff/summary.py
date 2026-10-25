"""Build and audit the committed summary of the frozen ChEMBL cohort."""

from __future__ import annotations

import json
import platform
from datetime import date
from pathlib import Path
from typing import Any

import numpy
import rdkit

from aidd_commons.decision_unit_scope.analysis import census_cohort
from aidd_commons.decision_unit_scope.data import load_cached_cohort

from .analysis import admitted_measurements, analyse
from .protocol import (
    FAMILIES,
    NAMED_FAMILIES,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
    load_protocol_document,
    validate_cache_lengths,
)


class SummaryContractError(ValueError):
    """An independently checkable summary invariant failed."""


def software_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "rdkit": rdkit.__version__,
    }


def build_summary(
    cache_dir: Path, *, computed_on: str | None = None, software: dict[str, str] | None = None
) -> dict[str, Any]:
    validate_cache_lengths(cache_dir)
    cohort = load_cached_cohort(cache_dir)
    census = census_cohort(cohort)
    parent_names = {parent.parent_molecule_chembl_id: parent.pref_name for parent in census.parents}
    result = analyse(admitted_measurements(cohort), parent_names)
    if result["admitted_measurement_count"] != census.independent_measurement_count:
        raise SummaryContractError("measurement count differs from the decision-unit census")
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or software_versions(),
        "source": {"database": cohort.status["chembl_db_version"]},
        "cohort": {
            "declared_seed_count": len(cohort.molecules),
            "resolved_parent_count": len(cohort.parents),
        },
        "admitted_point_row_count": census.admitted_point_count,
        **result,
    }


def audit_summary(summary: dict[str, Any]) -> None:
    """Check totals, complete coverage, missingness and value context."""

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise SummaryContractError(message)

    require(summary.get("schema_version") == SUMMARY_SCHEMA_VERSION, "summary schema")
    require(summary.get("protocol_id") == PROTOCOL_ID, "summary protocol")
    require(summary.get("cohort", {}).get("declared_seed_count") == 15, "seed count")
    compounds = summary.get("per_compound_coverage", [])
    require(len(compounds) == 10, "parent count")
    require(
        summary.get("cohort", {}).get("resolved_parent_count") == len(compounds), "cohort count"
    )
    require(len({row["parent_molecule_chembl_id"] for row in compounds}) == 10, "unique parents")
    families = summary.get("families", {})
    require(set(families) == set(FAMILIES), "family set")
    count = summary.get("admitted_measurement_count")
    require(isinstance(count, int) and count >= 0, "measurement count")
    require(
        sum(families[family]["independent_measurement_count"] for family in FAMILIES) == count,
        "family partition",
    )
    require(summary.get("admitted_point_row_count", -1) >= count, "point rows")
    for family in FAMILIES:
        family_count = families[family]["independent_measurement_count"]
        require(
            sum(row["families"][family]["independent_measurement_count"] for row in compounds)
            == family_count,
            f"{family} compound counts",
        )
        require(
            families[family]["compounds_without_measurement_count"]
            == sum(
                row["families"][family]["independent_measurement_count"] == 0 for row in compounds
            ),
            f"{family} missing count",
        )
        for value in (families[family], *(row["families"][family] for row in compounds)):
            n = value["independent_measurement_count"]
            require(value["unit"] == "nM", f"{family} unit")
            require(
                (
                    n == 0
                    and all(
                        value[key] is None for key in ("median", "q1", "q3", "interquartile_range")
                    )
                )
                or (
                    n > 0
                    and value["q1"] <= value["median"] <= value["q3"]
                    and abs(value["interquartile_range"] - (value["q3"] - value["q1"])) < 1e-9
                ),
                f"{family} value and spread",
            )
    expected_empty = [
        {
            "parent_molecule_chembl_id": row["parent_molecule_chembl_id"],
            "pref_name": row["pref_name"],
            "missing_families": [
                family
                for family in NAMED_FAMILIES
                if row["families"][family]["independent_measurement_count"] == 0
            ],
            "present_named_family_count": sum(
                row["families"][family]["independent_measurement_count"] > 0
                for family in NAMED_FAMILIES
            ),
        }
        for row in compounds
    ]
    require(
        summary.get("compounds_with_empty_family")
        == [row for row in expected_empty if row["missing_families"]],
        "empty-family list",
    )


def export_summary(lab_dir: Path, cache_dir: Path, output_path: Path) -> dict[str, Any]:
    """Write only after protocol, cache and every invariant pass."""
    load_protocol_document(lab_dir / "protocol.json")
    summary = build_summary(cache_dir)
    audit_summary(summary)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
