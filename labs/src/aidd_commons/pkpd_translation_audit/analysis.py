"""Join the frozen assay records and propagate an illustrative species step."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from math import isclose
from pathlib import Path
from typing import Any

from aidd_commons.az_clearance_system.data import (
    ParentClearanceRecord,
    SystemDataset,
    load_cached_systems,
)

from .model import simulate
from .protocol import HEPATOCYTE_UNIT, HUMAN, MICROSOME, MICROSOME_UNIT, RAT


class AnalysisError(ValueError):
    """The cached cohort or propagated model violates its contract."""


@dataclass(frozen=True)
class CompoundResult:
    parent_molecule_chembl_id: str
    human_hepatocyte_clearance: float
    rat_hepatocyte_clearance: float
    observed_human_to_rat_ratio: float
    translation_factor: float
    translation_factor_lower: float
    translation_factor_upper: float
    modelled_clearance_l_h: float
    concentration_0h_umol_l: float
    concentration_12h_umol_l: float
    concentration_24h_umol_l: float
    free_concentration_24h_umol_l: float
    occupancy_24h: float
    effect_24h: float
    effect_24h_lower: float
    effect_24h_upper: float
    uncertainty_stage_widths: tuple[float, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalysisResult:
    cohort: dict[str, Any]
    uncarried_reasons: dict[str, int]
    modelled: tuple[CompoundResult, ...]


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def load_from_cache(cache_dir: Path, source: Mapping[str, Any]) -> dict[str, SystemDataset]:
    expected = source["snapshot_files_bytes"]
    if not isinstance(expected, dict):
        raise AnalysisError("snapshot byte contract is invalid")
    actual: dict[str, int] = {}
    for name, size in expected.items():
        path = cache_dir / name
        try:
            actual[name] = path.stat().st_size
        except OSError as error:
            raise AnalysisError(f"cached snapshot file unavailable: {name}") from error
        if actual[name] != size:
            raise AnalysisError(f"cached snapshot byte length changed: {name}")
    if sum(actual.values()) != source["snapshot_bytes"]:
        raise AnalysisError("cached snapshot total byte length changed")
    return load_cached_systems(cache_dir)


def analyse(datasets: Mapping[str, SystemDataset], protocol: Mapping[str, Any]) -> AnalysisResult:
    if set(datasets) != {HUMAN, RAT, MICROSOME}:
        raise AnalysisError("three declared assay systems are required")
    by_system: dict[str, dict[str, ParentClearanceRecord]] = {}
    for assay_id, dataset in datasets.items():
        if dataset.assay_chembl_id != assay_id:
            raise AnalysisError("assay identifier mismatch")
        expected_unit = MICROSOME_UNIT if assay_id == MICROSOME else HEPATOCYTE_UNIT
        if any(record.standard_units != expected_unit for record in dataset.records):
            raise AnalysisError(f"{assay_id} has an unexpected clearance basis")
        indexed = {record.parent_molecule_chembl_id: record for record in dataset.records}
        if len(indexed) != len(dataset.records):
            raise AnalysisError("duplicate parent in an admitted assay")
        by_system[assay_id] = indexed

    human, rat, microsome = (by_system[assay] for assay in (HUMAN, RAT, MICROSOME))
    human_ids, rat_ids, micro_ids = set(human), set(rat), set(microsome)
    paired_ids = sorted(human_ids & rat_ids)
    if len(paired_ids) < 3:
        raise AnalysisError("fewer than three paired hepatocyte parents")
    ratios = {
        parent: human[parent].intrinsic_clearance / rat[parent].intrinsic_clearance
        for parent in paired_ids
    }
    if any(not (ratio > 0) for ratio in ratios.values()):
        raise AnalysisError("paired clearance ratio must be positive")

    specs = protocol["model"]["parameters"]
    lower_q = specs["translation_lower_quantile"]["value"]
    upper_q = specs["translation_upper_quantile"]["value"]
    results: list[CompoundResult] = []
    for parent in paired_ids:
        reference = [value for other, value in ratios.items() if other != parent]
        factor = _quantile(reference, 0.5)
        factor_lower = _quantile(reference, lower_q)
        factor_upper = _quantile(reference, upper_q)
        model = simulate(
            rat[parent].intrinsic_clearance,
            rat[parent].standard_units,
            factor,
            factor_lower,
            factor_upper,
            specs,
        )
        if not (model.effect_lower <= model.effect <= model.effect_upper):
            raise AnalysisError("central effect escapes propagated interval")
        if any(
            left > right + 1e-12
            for left, right in zip(model.stage_widths, model.stage_widths[1:], strict=False)
        ):
            raise AnalysisError("uncertainty shrinks after adding an uncertain step")
        if isclose(model.stage_widths[-1], 0, abs_tol=1e-15):
            raise AnalysisError("propagated uncertainty vanished")
        results.append(
            CompoundResult(
                parent_molecule_chembl_id=parent,
                human_hepatocyte_clearance=human[parent].intrinsic_clearance,
                rat_hepatocyte_clearance=rat[parent].intrinsic_clearance,
                observed_human_to_rat_ratio=ratios[parent],
                translation_factor=factor,
                translation_factor_lower=factor_lower,
                translation_factor_upper=factor_upper,
                modelled_clearance_l_h=model.clearance_l_h,
                concentration_0h_umol_l=model.concentration_0h_umol_l,
                concentration_12h_umol_l=model.concentration_half_interval_umol_l,
                concentration_24h_umol_l=model.concentration_umol_l,
                free_concentration_24h_umol_l=model.free_concentration_umol_l,
                occupancy_24h=model.occupancy,
                effect_24h=model.effect,
                effect_24h_lower=model.effect_lower,
                effect_24h_upper=model.effect_upper,
                uncertainty_stage_widths=model.stage_widths,
            )
        )

    reasons = {
        "human_hepatocyte_without_rat_hepatocyte": len(human_ids - rat_ids),
        "rat_hepatocyte_without_human_hepatocyte": len(rat_ids - human_ids),
        "microsome_only_different_clearance_basis": len(micro_ids - (human_ids | rat_ids)),
    }
    unique = len(human_ids | rat_ids | micro_ids)
    if len(results) + sum(reasons.values()) != unique:
        raise AnalysisError("cohort partition does not reconcile")
    divergent = sum(ratio >= 3 or ratio <= 1 / 3 for ratio in ratios.values())
    if divergent == 0:
        raise AnalysisError("no cross-species divergent compound exists in the paired cohort")
    cohort = {
        "input_rows_by_assay": {
            assay: datasets[assay].audit.input_rows for assay in (MICROSOME, RAT, HUMAN)
        },
        "admitted_parents_by_assay": {
            assay: len(by_system[assay]) for assay in (MICROSOME, RAT, HUMAN)
        },
        "unique_admitted_parents": unique,
        "paired_human_rat_hepatocyte_parents": len(paired_ids),
        "modelled_parents": len(results),
        "not_modelled_parents": sum(reasons.values()),
        "paired_with_at_least_threefold_difference": divergent,
    }
    return AnalysisResult(cohort=cohort, uncarried_reasons=reasons, modelled=tuple(results))


def check_analysis(result: AnalysisResult) -> list[str]:
    failures: list[str] = []
    if result.cohort["modelled_parents"] != len(result.modelled):
        failures.append("modelled count differs from per-parent results")
    if result.cohort["not_modelled_parents"] != sum(result.uncarried_reasons.values()):
        failures.append("uncarried counts do not reconcile")
    if result.cohort["unique_admitted_parents"] != (
        result.cohort["modelled_parents"] + result.cohort["not_modelled_parents"]
    ):
        failures.append("unique cohort count does not reconcile")
    seen: set[str] = set()
    for row in result.modelled:
        if row.parent_molecule_chembl_id in seen:
            failures.append("duplicate modelled parent")
        seen.add(row.parent_molecule_chembl_id)
        if not (
            row.translation_factor_lower <= row.translation_factor <= row.translation_factor_upper
        ):
            failures.append(f"invalid species interval for {row.parent_molecule_chembl_id}")
        if not (row.effect_24h_lower <= row.effect_24h <= row.effect_24h_upper):
            failures.append(f"invalid effect interval for {row.parent_molecule_chembl_id}")
        if not (
            row.concentration_0h_umol_l
            >= row.concentration_12h_umol_l
            >= row.concentration_24h_umol_l
        ):
            failures.append(f"non-decaying concentration for {row.parent_molecule_chembl_id}")
        if any(
            a > b + 1e-12
            for a, b in zip(
                row.uncertainty_stage_widths, row.uncertainty_stage_widths[1:], strict=False
            )
        ):
            failures.append(f"uncertainty contracts for {row.parent_molecule_chembl_id}")
    return failures
