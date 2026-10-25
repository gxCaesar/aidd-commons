"""Make parallel profiles from already-admitted parent records."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from statistics import median
from typing import Any

from aidd_commons.az_clearance_system.data import ParentClearanceRecord, SystemDataset
from aidd_commons.az_clearance_system.protocol import SYSTEMS
from aidd_commons.cyp_assay_system.data import ParentActivityRecord, TargetDataset
from aidd_commons.cyp_assay_system.protocol import TARGETS
from aidd_commons.multi_endpoint_tradeoff.analysis import Measurement, family_for_type

from .protocol import ALL_FAMILIES, FAMILIES


def _spread(values: list[float], unit: str) -> dict[str, Any]:
    """Descriptive range of admitted values, without an uncertainty interval."""
    return {
        "count": len(values),
        "median": float(median(values)),
        "minimum": min(values),
        "maximum": max(values),
        "range": max(values) - min(values),
        "unit": unit,
    }


def _efficacy_profile(rows: list[Measurement]) -> dict[str, Any]:
    by_type: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_type[row.standard_type].append(row.value)
    return {
        "measurements": [
            {
                "assay_chembl_id": row.assay_id,
                "document_chembl_id": row.document_id,
                "endpoint_type": row.standard_type,
                "value": row.value,
                "unit": row.unit,
            }
            for row in sorted(rows, key=lambda r: (r.standard_type, r.assay_id, r.document_id))
        ],
        "spread_by_endpoint": {
            endpoint: _spread(values, "nM") for endpoint, values in sorted(by_type.items())
        },
    }


def _exposure_profile(rows: list[ParentClearanceRecord]) -> dict[str, Any]:
    by_unit: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_unit[row.standard_units].append(row.intrinsic_clearance)
    return {
        "measurements": [
            {
                "assay_chembl_id": row.assay_chembl_id,
                "assay_system": SYSTEMS[row.assay_chembl_id][0],
                "value": row.intrinsic_clearance,
                "unit": row.standard_units,
                "contributing_activity_count": row.replicate_count,
                "within_assay_range": row.value_range,
            }
            for row in sorted(rows, key=lambda r: r.assay_chembl_id)
        ],
        "spread_by_unit": {unit: _spread(values, unit) for unit, values in sorted(by_unit.items())},
    }


def _interaction_profile(rows: list[ParentActivityRecord]) -> dict[str, Any]:
    values = [row.target_pchembl for row in rows]
    return {
        "measurements": [
            {
                "target_chembl_id": row.target_chembl_id,
                "target": TARGETS[row.target_chembl_id],
                "assay_chembl_ids": list(row.assay_chembl_ids),
                "document_chembl_ids": list(row.document_chembl_ids),
                "value": row.target_pchembl,
                "unit": "pChEMBL (dimensionless)",
                "contributing_activity_count": row.replicate_count,
                "within_target_range": row.pchembl_range,
            }
            for row in sorted(rows, key=lambda r: r.target_chembl_id)
        ],
        "spread": _spread(values, "pChEMBL (dimensionless)"),
    }


def _coverage_keys() -> list[str]:
    return [
        "+".join(group)
        for size in range(1, len(FAMILIES) + 1)
        for group in combinations(FAMILIES, size)
    ]


def analyse(
    measurements: tuple[Measurement, ...],
    parent_names: dict[str, str],
    systems: dict[str, SystemDataset],
    targets: dict[str, TargetDataset],
) -> dict[str, Any]:
    """Join solely on the reader-provided parent identifier, never on structure."""
    efficacy: dict[str, list[Measurement]] = defaultdict(list)
    affinity_count = 0
    for row in measurements:
        if family_for_type(row.standard_type) == "efficacy":
            efficacy[row.parent_id].append(row)
        else:
            affinity_count += 1

    exposure: dict[str, list[ParentClearanceRecord]] = defaultdict(list)
    for system_dataset in systems.values():
        for clearance_record in system_dataset.records:
            exposure[clearance_record.parent_molecule_chembl_id].append(clearance_record)

    interaction: dict[str, list[ParentActivityRecord]] = defaultdict(list)
    for target_dataset in targets.values():
        for activity_record in target_dataset.records:
            interaction[activity_record.parent_molecule_chembl_id].append(activity_record)

    parents = sorted(set(efficacy) | set(exposure) | set(interaction))
    by_family: dict[str, set[str]] = {
        "efficacy": set(efficacy),
        "exposure": set(exposure),
        "interaction": set(interaction),
    }
    coverage: Counter[str] = Counter()
    single: dict[str, list[str]] = {family: [] for family in FAMILIES}
    profiles: list[dict[str, Any]] = []
    for parent_id in parents:
        present = [family for family in FAMILIES if parent_id in by_family[family]]
        missing = [family for family in ALL_FAMILIES if family not in present]
        coverage["+".join(present)] += 1
        if len(present) == 1:
            single[present[0]].append(parent_id)
        else:
            profiles.append(
                {
                    "parent_chembl_id": parent_id,
                    "pref_name": parent_names.get(parent_id),
                    "present_families": present,
                    "missing_families": missing,
                    "efficacy": _efficacy_profile(efficacy[parent_id])
                    if parent_id in efficacy
                    else None,
                    "exposure": _exposure_profile(exposure[parent_id])
                    if parent_id in exposure
                    else None,
                    "interaction": (
                        _interaction_profile(interaction[parent_id])
                        if parent_id in interaction
                        else None
                    ),
                    "toxicity": None,
                }
            )

    family_measurement_counts = {
        "efficacy": sum(map(len, efficacy.values())),
        "exposure": sum(map(len, exposure.values())),
        "interaction": sum(map(len, interaction.values())),
        "toxicity": 0,
    }
    thinnest = min(FAMILIES, key=lambda family: family_measurement_counts[family])
    family_compound_counts = {
        **{family: len(by_family[family]) for family in FAMILIES},
        "toxicity": 0,
    }
    missing_available_family_counts = {
        family: len(parents) - len(by_family[family]) for family in FAMILIES
    }
    return {
        "family_coverage_matrix": {key: coverage[key] for key in _coverage_keys()},
        "profiles": profiles,
        "single_family_compounds": single,
        "counts": {
            "cohort_compound_count": len(parents),
            "one_family_compound_count": sum(map(len, single.values())),
            "two_family_compound_count": sum(len(p["present_families"]) == 2 for p in profiles),
            "three_family_compound_count": sum(len(p["present_families"]) == 3 for p in profiles),
            "profile_count": len(profiles),
            "source_independent_activity_measurement_count": len(measurements),
            "affinity_outside_efficacy_count": affinity_count,
            "family_measurement_counts": family_measurement_counts,
            "thinnest_measured_family": thinnest,
            "measurement_count_gaps_from_thinnest": {
                family: family_measurement_counts[family] - family_measurement_counts[thinnest]
                for family in FAMILIES
                if family != thinnest
            },
            "family_compound_counts": family_compound_counts,
            "missing_available_family_counts": missing_available_family_counts,
            "toxicity_unmeasured_compound_count": len(parents),
        },
    }
