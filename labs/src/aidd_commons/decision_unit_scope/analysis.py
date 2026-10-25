"""Count real measurements against a declared unit of inference.

Nothing here fits a model, tunes a threshold or draws a split. Every number is
a count of something that is either in ChEMBL 37 or a declared grouping of it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .data import ActivityRow, AssayRecord, CohortDataset, ParentDataset
from .protocol import EXCLUSION_PRIORITY


class AnalysisContractError(ValueError):
    """Raised when the census cannot be built from the cached records."""


@dataclass(frozen=True)
class SeedResolution:
    """One declared seed molecule and the parent it resolves to."""

    molecule_chembl_id: str
    pref_name: str
    parent_molecule_chembl_id: str
    is_own_parent: bool
    fragment_count: int

    @property
    def is_multi_component(self) -> bool:
        return self.fragment_count > 1


@dataclass(frozen=True)
class MeasurementContext:
    """One reported value together with everything needed to talk about it."""

    parent_molecule_chembl_id: str
    parent_pref_name: str
    activity_id: int
    tested_molecule_chembl_id: str
    tested_form: str
    standard_type: str
    standard_value: float
    standard_units: str
    standard_relation: str
    pchembl_value: float | None
    assay_chembl_id: str
    assay_type: str | None
    assay_organism: str | None
    confidence_score: int | None
    document_chembl_id: str
    document_journal: str | None
    document_year: int | None
    target_chembl_id: str | None
    target_pref_name: str | None
    target_organism: str | None
    toid: str | None


@dataclass(frozen=True)
class ParentCensus:
    """The measurement census of one parent molecule."""

    parent_molecule_chembl_id: str
    pref_name: str
    reported_row_count: int
    admitted_point_count: int
    admitted_bound_count: int
    independent_measurement_count: int
    independent_experiment_count: int
    distinct_assay_count: int
    distinct_document_count: int
    distinct_target_count: int
    parent_form_point_count: int
    salt_form_point_count: int
    child_molecule_ids: tuple[str, ...]
    exclusion_counts: Mapping[str, int]
    endpoint_type_counts: Mapping[str, int]
    assay_type_counts: Mapping[str, int]
    confidence_score_counts: Mapping[str, int]
    assay_organism_counts: Mapping[str, int]
    target_organism_counts: Mapping[str, int]
    bound_relation_counts: Mapping[str, int]
    toid_point_row_count: int
    replicate_point_row_count: int
    assay_type_disagreement_count: int


@dataclass(frozen=True)
class CohortCensus:
    """The cohort-wide census and the entity resolution that produced it."""

    seeds: tuple[SeedResolution, ...]
    parents: tuple[ParentCensus, ...]
    reported_row_count: int
    admitted_point_count: int
    admitted_bound_count: int
    independent_measurement_count: int
    independent_experiment_count: int
    parent_form_point_count: int
    salt_form_point_count: int
    exclusion_counts: Mapping[str, int]
    admission_funnel: tuple[Mapping[str, Any], ...]


def resolve_entities(cohort: CohortDataset) -> tuple[SeedResolution, ...]:
    """Resolve every declared seed molecule to the parent it belongs to."""
    return tuple(
        SeedResolution(
            molecule_chembl_id=record.molecule_chembl_id,
            pref_name=record.pref_name,
            parent_molecule_chembl_id=record.parent_molecule_chembl_id,
            is_own_parent=record.is_own_parent,
            fragment_count=record.fragment_count,
        )
        for record in sorted(
            cohort.molecules.values(), key=lambda item: item.molecule_chembl_id
        )
    )


def ordered_exclusions(counts: Mapping[str, int]) -> dict[str, int]:
    """The exclusion counts, in the protocol's declared priority order."""
    ordered = {reason: counts.get(reason, 0) for reason in EXCLUSION_PRIORITY}
    for reason in sorted(counts):
        if reason not in ordered:
            ordered[reason] = counts[reason]
    return ordered


def census_parent(
    dataset: ParentDataset, assays: Mapping[str, AssayRecord], pref_name: str
) -> ParentCensus:
    """Count the measurements of one parent molecule."""
    rows = dataset.rows
    point = [row for row in rows if row.classification == "point"]
    bound = [row for row in rows if row.classification == "bound"]

    grouping_keys = {row.grouping_key for row in point}
    experiment_keys = {row.experiment_key for row in point}

    exclusions: Counter[str] = Counter()
    for row in rows:
        reason = row.classification
        if reason not in ("point", "bound"):
            exclusions[reason] += 1

    child_ids = sorted({row.molecule_chembl_id for row in point if row.is_child_form})
    assay_type_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    assay_organism_counts: Counter[str] = Counter()
    target_organism_counts: Counter[str] = Counter()
    disagreement = 0
    for row in point:
        assay = assays.get(row.assay_chembl_id)
        assay_type_counts[row.assay_type or "not recorded"] += 1
        if assay is None:
            confidence_counts["assay record not fetched"] += 1
            assay_organism_counts["assay record not fetched"] += 1
        else:
            confidence_counts[str(assay.confidence_score)] += 1
            assay_organism_counts[assay.assay_organism or "not recorded"] += 1
            if assay.assay_type is not None and row.assay_type is not None:
                if assay.assay_type != row.assay_type:
                    disagreement += 1
        target_organism_counts[row.target_organism or "not recorded"] += 1

    return ParentCensus(
        parent_molecule_chembl_id=dataset.parent_molecule_chembl_id,
        pref_name=pref_name,
        reported_row_count=len(rows),
        admitted_point_count=len(point),
        admitted_bound_count=len(bound),
        independent_measurement_count=len(grouping_keys),
        independent_experiment_count=len(experiment_keys),
        distinct_assay_count=len({row.assay_chembl_id for row in point}),
        distinct_document_count=len({row.document_chembl_id for row in point}),
        distinct_target_count=len({row.target_chembl_id for row in point}),
        parent_form_point_count=sum(1 for row in point if not row.is_child_form),
        salt_form_point_count=sum(1 for row in point if row.is_child_form),
        child_molecule_ids=tuple(child_ids),
        exclusion_counts=ordered_exclusions(exclusions),
        endpoint_type_counts=dict(
            sorted(Counter(row.standard_type or "" for row in point).items())
        ),
        assay_type_counts=dict(sorted(assay_type_counts.items())),
        confidence_score_counts=dict(sorted(confidence_counts.items())),
        assay_organism_counts=dict(sorted(assay_organism_counts.items())),
        target_organism_counts=dict(sorted(target_organism_counts.items())),
        bound_relation_counts=dict(
            sorted(Counter(row.standard_relation or "" for row in bound).items())
        ),
        toid_point_row_count=sum(1 for row in point if row.toid is not None),
        replicate_point_row_count=len(point) - len(grouping_keys),
        assay_type_disagreement_count=disagreement,
    )


def _parent_pref_names(cohort: CohortDataset) -> dict[str, str]:
    """The name to call each parent by.

    A parent's own record is preferred over the name of one of its salt
    children, so that a parent is never reported under the name of a
    formulation of itself.
    """
    names: dict[str, str] = {}
    for record in cohort.molecules.values():
        if record.is_own_parent:
            names[record.parent_molecule_chembl_id] = record.pref_name
    for record in cohort.molecules.values():
        names.setdefault(record.parent_molecule_chembl_id, record.pref_name)
    return names


def census_cohort(cohort: CohortDataset) -> CohortCensus:
    """Build the cohort-wide census from the cached records."""
    names = _parent_pref_names(cohort)
    censuses = [
        census_parent(cohort.parents[parent_id], cohort.assays, names[parent_id])
        for parent_id in sorted(cohort.parents)
    ]

    exclusions: Counter[str] = Counter()
    for census in censuses:
        exclusions.update(census.exclusion_counts)

    total_rows = sum(census.reported_row_count for census in censuses)
    total_point = sum(census.admitted_point_count for census in censuses)
    total_bound = sum(census.admitted_bound_count for census in censuses)

    funnel: list[Mapping[str, Any]] = [
        {"stage": "reported_rows", "removed": 0, "remaining": total_rows}
    ]
    remaining = total_rows
    for reason in EXCLUSION_PRIORITY:
        removed = exclusions.get(reason, 0)
        remaining -= removed
        funnel.append({"stage": reason, "removed": removed, "remaining": remaining})
    funnel.append(
        {"stage": "admitted_total", "removed": 0, "remaining": remaining}
    )
    funnel.append(
        {
            "stage": "admitted_bound",
            "removed": total_bound,
            "remaining": remaining - total_bound,
        }
    )
    funnel.append(
        {"stage": "admitted_point", "removed": 0, "remaining": remaining - total_bound}
    )

    return CohortCensus(
        seeds=resolve_entities(cohort),
        parents=tuple(censuses),
        reported_row_count=total_rows,
        admitted_point_count=total_point,
        admitted_bound_count=total_bound,
        independent_measurement_count=sum(
            census.independent_measurement_count for census in censuses
        ),
        independent_experiment_count=sum(
            census.independent_experiment_count for census in censuses
        ),
        parent_form_point_count=sum(census.parent_form_point_count for census in censuses),
        salt_form_point_count=sum(census.salt_form_point_count for census in censuses),
        exclusion_counts=ordered_exclusions(exclusions),
        admission_funnel=tuple(funnel),
    )


def measurement_context(
    row: ActivityRow, assay: AssayRecord | None, parent_pref_name: str
) -> MeasurementContext:
    """Assemble the full context of one reported value."""
    return MeasurementContext(
        parent_molecule_chembl_id=row.parent_molecule_chembl_id,
        parent_pref_name=parent_pref_name,
        activity_id=row.activity_id,
        tested_molecule_chembl_id=row.molecule_chembl_id,
        tested_form="parent structure" if not row.is_child_form else "child (salt or mixture) form",
        standard_type=row.standard_type or "",
        standard_value=row.standard_value if row.standard_value is not None else 0.0,
        standard_units=row.standard_units or "",
        standard_relation=row.standard_relation or "",
        pchembl_value=row.pchembl_value,
        assay_chembl_id=row.assay_chembl_id,
        assay_type=assay.assay_type if assay else None,
        assay_organism=assay.assay_organism if assay else None,
        confidence_score=assay.confidence_score if assay else None,
        document_chembl_id=row.document_chembl_id,
        document_journal=row.document_journal,
        document_year=row.document_year,
        target_chembl_id=row.target_chembl_id,
        target_pref_name=row.target_pref_name,
        target_organism=row.target_organism,
        toid=row.toid,
    )


def first_admitted_point_row(dataset: ParentDataset) -> ActivityRow:
    """The lowest-activity-id admitted point measurement of a parent."""
    point = [row for row in dataset.rows if row.classification == "point"]
    if not point:
        raise AnalysisContractError(
            f"parent {dataset.parent_molecule_chembl_id} has no admitted point measurement"
        )
    return min(point, key=lambda row: row.activity_id)


def largest_row_to_measurement_gap(census: CohortCensus) -> ParentCensus:
    """The parent whose reported row count overstates its measurement count most."""
    candidates = [
        item
        for item in census.parents
        if item.admitted_point_count > 0 and item.reported_row_count > item.admitted_point_count
    ]
    if not candidates:
        raise AnalysisContractError("no parent shows a gap between rows and measurements")
    return max(
        candidates,
        key=lambda item: (item.reported_row_count / item.admitted_point_count, item.pref_name),
    )


def highest_salt_form_share(census: CohortCensus) -> ParentCensus:
    """The parent whose admitted measurements are most often reported on a salt."""
    candidates = [item for item in census.parents if item.admitted_point_count > 0]
    if not candidates:
        raise AnalysisContractError("no parent has an admitted measurement")
    return max(
        candidates,
        key=lambda item: (
            item.salt_form_point_count / item.admitted_point_count,
            item.salt_form_point_count,
            item.pref_name,
        ),
    )


def parents_with_no_admitted_measurement(census: CohortCensus) -> tuple[ParentCensus, ...]:
    """The parents ChEMBL has rows for but that this protocol admits nothing for."""
    return tuple(item for item in census.parents if item.admitted_point_count == 0)


def seeds_sharing_a_parent(census: CohortCensus) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """The declared seed groups that collapse onto one unit of inference."""
    grouped: dict[str, list[str]] = {}
    for resolution in census.seeds:
        grouped.setdefault(resolution.parent_molecule_chembl_id, []).append(
            resolution.molecule_chembl_id
        )
    return tuple(
        (parent_id, tuple(sorted(members)))
        for parent_id, members in sorted(grouped.items())
        if len(members) > 1
    )
