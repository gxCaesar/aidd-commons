"""Build and audit the small, score-free integration summary."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy
import rdkit

from aidd_commons.az_clearance_system.data import load_cached_systems
from aidd_commons.cyp_assay_system.data import load_cached_targets
from aidd_commons.decision_unit_scope.analysis import census_cohort
from aidd_commons.decision_unit_scope.data import load_cached_cohort
from aidd_commons.multi_endpoint_tradeoff.analysis import (
    admitted_measurements,
    independent_measurements,
)

from .analysis import analyse
from .protocol import (
    ALL_FAMILIES,
    BOUNDARY_STATEMENT,
    FAMILIES,
    PACKAGE_VERSION_FALLBACK,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
    load_protocol_document,
    validate_cache_lengths,
)
from .protocol import expected_contract as expected_protocol


class SummaryContractError(ValueError):
    """The summary violates an invariant or differs from the cached computation."""


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
    """Load the three validated caches through their owning readers."""
    validate_cache_lengths(cache_root)
    cohort = load_cached_cohort(cache_root / "decision_unit_scope")
    systems = load_cached_systems(cache_root / "az_clearance_system")
    targets = load_cached_targets(cache_root / "cyp_assay_system")
    census = census_cohort(cohort)
    measurements = independent_measurements(admitted_measurements(cohort))
    if len(measurements) != census.independent_measurement_count:
        raise SummaryContractError("activity measurement count differs from the source census")
    names = {parent.parent_molecule_chembl_id: parent.pref_name for parent in census.parents}
    result = analyse(measurements, names, systems, targets)
    protocol = expected_protocol()
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": software_versions(),
        "families": protocol["families"],
        **result,
        "boundary_statement": BOUNDARY_STATEMENT,
        "rules": protocol["rules"],
    }
    audit_summary(summary)
    return summary


def _refuse_numeric_collapse(value: Any, *, under_rules: bool = False) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                not under_rules
                and key != "rules"
                and any(
                    word in key.lower()
                    for word in ("score", "rank", "weighted", "desirability", "fold_change")
                )
            ):
                raise SummaryContractError(f"combined numeric field refused: {key}")
            _refuse_numeric_collapse(child, under_rules=under_rules or key == "rules")
    elif isinstance(value, list):
        for child in value:
            _refuse_numeric_collapse(child, under_rules=under_rules)


def audit_summary(summary: dict[str, Any]) -> None:
    """Refuse a score, a filled missing family or inconsistent counts."""
    _refuse_numeric_collapse(summary)
    required = {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "families",
        "family_coverage_matrix",
        "profiles",
        "single_family_compounds",
        "counts",
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
    protocol = expected_protocol()
    if (
        summary["families"] != protocol["families"]
        or summary["rules"] != protocol["rules"]
        or summary["boundary_statement"] != BOUNDARY_STATEMENT
    ):
        raise SummaryContractError("family, rule or boundary contract differs")
    counts = summary["counts"]
    coverage = summary["family_coverage_matrix"]
    profiles = summary["profiles"]
    single = summary["single_family_compounds"]
    expected_profile_keys = {
        "parent_chembl_id",
        "pref_name",
        "present_families",
        "missing_families",
        "efficacy",
        "exposure",
        "interaction",
        "toxicity",
    }
    expected_family_keys = {
        "efficacy": {"measurements", "spread_by_endpoint"},
        "exposure": {"measurements", "spread_by_unit"},
        "interaction": {"measurements", "spread"},
    }
    expected_measurement_keys = {
        "efficacy": {"assay_chembl_id", "document_chembl_id", "endpoint_type", "value", "unit"},
        "exposure": {
            "assay_chembl_id",
            "assay_system",
            "value",
            "unit",
            "contributing_activity_count",
            "within_assay_range",
        },
        "interaction": {
            "target_chembl_id",
            "target",
            "assay_chembl_ids",
            "document_chembl_ids",
            "value",
            "unit",
            "contributing_activity_count",
            "within_target_range",
        },
    }
    expected_spread_keys = {"count", "median", "minimum", "maximum", "range", "unit"}
    if set(single) != set(FAMILIES):
        raise SummaryContractError("single-family list is incomplete")
    if sum(coverage.values()) != counts["cohort_compound_count"]:
        raise SummaryContractError("coverage matrix does not count the cohort")
    if sum(len(ids) for ids in single.values()) != counts["one_family_compound_count"]:
        raise SummaryContractError("single-family compounds do not match the count")
    if len(profiles) != counts["profile_count"] or len(profiles) != (
        counts["two_family_compound_count"] + counts["three_family_compound_count"]
    ):
        raise SummaryContractError("profile counts do not match coverage")
    if counts["source_independent_activity_measurement_count"] != (
        counts["family_measurement_counts"]["efficacy"] + counts["affinity_outside_efficacy_count"]
    ):
        raise SummaryContractError("activity measurements do not partition")
    if (
        counts["family_measurement_counts"]["toxicity"] != 0
        or counts["family_compound_counts"]["toxicity"] != 0
    ):
        raise SummaryContractError("toxicity is not measured")
    thinnest = min(FAMILIES, key=lambda family: counts["family_measurement_counts"][family])
    if counts["thinnest_measured_family"] != thinnest or counts[
        "measurement_count_gaps_from_thinnest"
    ] != {
        family: counts["family_measurement_counts"][family]
        - counts["family_measurement_counts"][thinnest]
        for family in FAMILIES
        if family != thinnest
    }:
        raise SummaryContractError("thinnest measured family or count gaps differ")
    if counts["toxicity_unmeasured_compound_count"] != counts["cohort_compound_count"]:
        raise SummaryContractError("toxicity missingness differs from cohort")
    for family in FAMILIES:
        if counts["missing_available_family_counts"][family] != (
            counts["cohort_compound_count"] - counts["family_compound_counts"][family]
        ):
            raise SummaryContractError(f"{family} missingness differs from coverage")
    if any(set(profile) != expected_profile_keys for profile in profiles):
        raise SummaryContractError("profile has an undeclared field")
    ids = [parent_id for family_ids in single.values() for parent_id in family_ids]
    ids.extend(profile["parent_chembl_id"] for profile in profiles)
    if len(ids) != len(set(ids)) or len(ids) != counts["cohort_compound_count"]:
        raise SummaryContractError("parent identifiers are duplicated or omitted")
    for profile in profiles:
        present = profile["present_families"]
        missing = profile["missing_families"]
        if (
            len(present) < 2
            or missing != [family for family in ALL_FAMILIES if family not in present]
            or profile["toxicity"] is not None
        ):
            raise SummaryContractError("profile family presence is inconsistent")
        for family in FAMILIES:
            if (profile[family] is None) == (family in present):
                raise SummaryContractError("missing family has a value or present family is empty")
            entry = profile[family]
            if entry is None:
                continue
            if set(entry) != expected_family_keys[family] or any(
                set(measurement) != expected_measurement_keys[family]
                for measurement in entry["measurements"]
            ):
                raise SummaryContractError(f"{family} profile has an undeclared field")
            spreads = (
                [entry["spread"]]
                if family == "interaction"
                else list(
                    entry[
                        "spread_by_endpoint" if family == "efficacy" else "spread_by_unit"
                    ].values()
                )
            )
            if any(set(spread) != expected_spread_keys for spread in spreads):
                raise SummaryContractError(f"{family} spread has an undeclared field")
        exposure = profile["exposure"]
        if exposure is not None:
            grouped_units = {
                unit: [row["value"] for row in exposure["measurements"] if row["unit"] == unit]
                for unit in exposure["spread_by_unit"]
            }
            if set(grouped_units) != {row["unit"] for row in exposure["measurements"]}:
                raise SummaryContractError("clearance unit grouping is incomplete")
            for unit, values in grouped_units.items():
                spread = exposure["spread_by_unit"][unit]
                if spread["count"] != len(values) or spread["unit"] != unit:
                    raise SummaryContractError("clearance spread crosses physical units")


def check_summary(committed: dict[str, Any], computed: dict[str, Any]) -> None:
    audit_summary(committed)
    audit_summary(computed)
    for field, value in computed.items():
        if field not in {"computed_on", "software"} and committed.get(field) != value:
            raise SummaryContractError(f"committed {field} differs from cached computation")


def export_summary(
    lab_dir: Path,
    cache_root: Path,
    output_path: Path,
    *,
    candidate: dict[str, Any] | None = None,
) -> None:
    """Write only after contract, source and candidate audits all pass."""
    load_protocol_document(lab_dir / "protocol.json")
    computed = build_summary(cache_root)
    selected = candidate if candidate is not None else computed
    check_summary(selected, computed)
    output_path.write_text(
        json.dumps(selected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
