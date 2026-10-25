"""Project the cached census into the small, committed public summary.

The summary carries counts, audits and a few named examples. It carries no raw
activity rows, no SMILES strings and no bulk compound list.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .analysis import (
    CohortCensus,
    first_admitted_point_row,
    highest_salt_form_share,
    largest_row_to_measurement_gap,
    measurement_context,
    parents_with_no_admitted_measurement,
    seeds_sharing_a_parent,
)
from .data import CohortDataset
from .protocol import (
    CHEMBL_LICENSE_NAME,
    CHEMBL_LICENSE_URL,
    CHEMBL_RELEASE_DATE,
    CHEMBL_VERSION,
    ENDPOINT_TYPES,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
)


def _parent_entry(census: CohortCensus, index: int) -> dict[str, Any]:
    item = census.parents[index]
    return {
        "parent_molecule_chembl_id": item.parent_molecule_chembl_id,
        "pref_name": item.pref_name,
        "reported_row_count": item.reported_row_count,
        "admitted_point_count": item.admitted_point_count,
        "admitted_bound_count": item.admitted_bound_count,
        "independent_measurement_count": item.independent_measurement_count,
        "independent_experiment_count": item.independent_experiment_count,
        "distinct_assay_count": item.distinct_assay_count,
        "distinct_document_count": item.distinct_document_count,
        "distinct_target_count": item.distinct_target_count,
        "parent_form_point_count": item.parent_form_point_count,
        "salt_form_point_count": item.salt_form_point_count,
        "child_molecule_ids": list(item.child_molecule_ids),
        "exclusion_counts": dict(item.exclusion_counts),
        "endpoint_type_counts": dict(item.endpoint_type_counts),
        "assay_type_counts": dict(item.assay_type_counts),
        "confidence_score_counts": dict(item.confidence_score_counts),
        "assay_organism_counts": dict(item.assay_organism_counts),
        "target_organism_counts": dict(item.target_organism_counts),
        "bound_relation_counts": dict(item.bound_relation_counts),
        "toid_point_row_count": item.toid_point_row_count,
        "replicate_point_row_count": item.replicate_point_row_count,
        "assay_type_disagreement_count": item.assay_type_disagreement_count,
    }


def build_summary(
    cohort: CohortDataset,
    census: CohortCensus,
    *,
    computed_on: str,
    software: Mapping[str, str],
) -> dict[str, Any]:
    """Build the committed summary from the cached cohort and its census."""
    entries = [_parent_entry(census, index) for index in range(len(census.parents))]

    gap = largest_row_to_measurement_gap(census)
    salt = highest_salt_form_share(census)
    empty = parents_with_no_admitted_measurement(census)

    context_parent = cohort.parents[gap.parent_molecule_chembl_id]
    context_row = first_admitted_point_row(context_parent)
    context = measurement_context(
        context_row,
        cohort.assays.get(context_row.assay_chembl_id),
        gap.pref_name,
    )

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on,
        "software": dict(sorted(software.items())),
        "source": {
            "database": CHEMBL_VERSION,
            "release_date": CHEMBL_RELEASE_DATE,
            "licence": CHEMBL_LICENSE_NAME,
            "licence_url": CHEMBL_LICENSE_URL,
        },
        "endpoint": {
            "standard_types": list(ENDPOINT_TYPES),
            "standard_units": "nM",
        },
        "entity_resolution": {
            "declared_seed_count": len(census.seeds),
            "distinct_parent_count": len(census.parents),
            "seeds": [
                {
                    "molecule_chembl_id": resolution.molecule_chembl_id,
                    "pref_name": resolution.pref_name,
                    "parent_molecule_chembl_id": resolution.parent_molecule_chembl_id,
                    "is_own_parent": resolution.is_own_parent,
                    "stored_fragment_count": resolution.fragment_count,
                }
                for resolution in census.seeds
            ],
            "seed_groups_sharing_one_parent": [
                {"parent_molecule_chembl_id": parent_id, "molecule_chembl_ids": list(members)}
                for parent_id, members in seeds_sharing_a_parent(census)
            ],
        },
        "cohort": {
            "reported_row_count": census.reported_row_count,
            "admitted_point_count": census.admitted_point_count,
            "admitted_bound_count": census.admitted_bound_count,
            "independent_measurement_count": census.independent_measurement_count,
            "independent_experiment_count": census.independent_experiment_count,
            "parent_form_point_count": census.parent_form_point_count,
            "salt_form_point_count": census.salt_form_point_count,
            "exclusion_counts": dict(census.exclusion_counts),
            "admission_funnel": [dict(stage) for stage in census.admission_funnel],
            "parents": entries,
        },
        "named_examples": {
            "largest_row_to_measurement_gap": {
                "parent_molecule_chembl_id": gap.parent_molecule_chembl_id,
                "pref_name": gap.pref_name,
                "reported_row_count": gap.reported_row_count,
                "admitted_point_count": gap.admitted_point_count,
                "independent_measurement_count": gap.independent_measurement_count,
                "rows_per_independent_measurement": (
                    gap.reported_row_count / gap.independent_measurement_count
                    if gap.independent_measurement_count
                    else None
                ),
            },
            "highest_salt_form_share": {
                "parent_molecule_chembl_id": salt.parent_molecule_chembl_id,
                "pref_name": salt.pref_name,
                "admitted_point_count": salt.admitted_point_count,
                "salt_form_point_count": salt.salt_form_point_count,
                "child_molecule_ids": list(salt.child_molecule_ids),
                "salt_form_share": (
                    salt.salt_form_point_count / salt.admitted_point_count
                    if salt.admitted_point_count
                    else None
                ),
            },
            "parents_without_admitted_measurement": [
                {
                    "parent_molecule_chembl_id": item.parent_molecule_chembl_id,
                    "pref_name": item.pref_name,
                    "reported_row_count": item.reported_row_count,
                }
                for item in empty
            ],
            "one_reported_value_in_full_context": {
                "parent_molecule_chembl_id": context.parent_molecule_chembl_id,
                "parent_pref_name": context.parent_pref_name,
                "activity_id": context.activity_id,
                "tested_molecule_chembl_id": context.tested_molecule_chembl_id,
                "tested_form": context.tested_form,
                "standard_type": context.standard_type,
                "standard_value": context.standard_value,
                "standard_units": context.standard_units,
                "standard_relation": context.standard_relation,
                "pchembl_value": context.pchembl_value,
                "assay_chembl_id": context.assay_chembl_id,
                "assay_type": context.assay_type,
                "assay_organism": context.assay_organism,
                "confidence_score": context.confidence_score,
                "document_chembl_id": context.document_chembl_id,
                "document_journal": context.document_journal,
                "document_year": context.document_year,
                "target_chembl_id": context.target_chembl_id,
                "target_pref_name": context.target_pref_name,
                "target_organism": context.target_organism,
                "toid": context.toid,
            },
        },
    }
