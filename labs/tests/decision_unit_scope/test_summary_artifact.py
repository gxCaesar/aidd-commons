"""The committed summary must be internally consistent on its own.

This test does not need the local cache and does not need a network: the
committed `summary.json` has to stand up as an artefact on its own, because
that is what a reader and a continuous-integration job see.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope.protocol import (
    COHORT_PARENTS,
    COHORT_SEEDS,
    EXCLUSION_PRIORITY,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = ROOT / "labs/decision_unit_scope/summary.json"
PROTOCOL_PATH = ROOT / "labs/decision_unit_scope/protocol.json"


def load_summary() -> dict[str, Any]:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def load_protocol() -> dict[str, Any]:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_the_summary_matches_the_frozen_protocol() -> None:
    summary = load_summary()
    protocol = load_protocol()
    assert summary["protocol_id"] == PROTOCOL_ID
    assert summary["protocol_id"] == protocol["protocol_id"]
    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert summary["computed_on"]
    assert summary["software"]
    assert summary["source"]["database"] == protocol["source"]["database"]
    assert summary["source"]["release_date"] == protocol["source"]["release_date"]
    assert summary["source"]["licence"] == protocol["source"]["licence"]["name"]
    assert summary["endpoint"]["standard_types"] == protocol["endpoint"]["standard_types"]
    assert summary["endpoint"]["standard_units"] == protocol["endpoint"]["standard_units"]


def test_the_summary_declares_the_whole_cohort_and_its_resolution() -> None:
    summary = load_summary()
    resolution = summary["entity_resolution"]
    assert resolution["declared_seed_count"] == len(COHORT_SEEDS)
    assert resolution["distinct_parent_count"] == len(COHORT_PARENTS)
    declared = {(seed["molecule_chembl_id"], seed["pref_name"]) for seed in resolution["seeds"]}
    assert declared == set(COHORT_SEEDS)
    assert {seed["parent_molecule_chembl_id"] for seed in resolution["seeds"]} == set(
        COHORT_PARENTS
    )
    for seed in resolution["seeds"]:
        assert seed["stored_fragment_count"] >= 1
        assert seed["is_own_parent"] == (
            seed["molecule_chembl_id"] == seed["parent_molecule_chembl_id"]
        )


def test_the_collapsed_seed_groups_explain_the_difference_in_size() -> None:
    summary = load_summary()
    resolution = summary["entity_resolution"]
    groups = resolution["seed_groups_sharing_one_parent"]
    collapsed = {member for group in groups for member in group["molecule_chembl_ids"]}
    assert len(collapsed) + resolution["distinct_parent_count"] - len(groups) == (
        resolution["declared_seed_count"]
    )
    assert collapsed <= {seed["molecule_chembl_id"] for seed in resolution["seeds"]}


def test_every_parent_entry_is_internally_consistent() -> None:
    summary = load_summary()
    entries = summary["cohort"]["parents"]
    assert {entry["parent_molecule_chembl_id"] for entry in entries} == set(COHORT_PARENTS)
    for entry in entries:
        excluded = sum(entry["exclusion_counts"].values())
        assert (
            excluded + entry["admitted_point_count"] + entry["admitted_bound_count"]
            == entry["reported_row_count"]
        )
        assert entry["independent_measurement_count"] <= entry["admitted_point_count"]
        assert entry["independent_experiment_count"] <= entry["independent_measurement_count"]
        assert entry["distinct_assay_count"] <= entry["independent_experiment_count"]
        assert entry["distinct_document_count"] <= entry["distinct_assay_count"]
        assert entry["distinct_target_count"] <= entry["distinct_assay_count"]
        assert (
            entry["parent_form_point_count"] + entry["salt_form_point_count"]
            == entry["admitted_point_count"]
        )
        assert set(entry["exclusion_counts"]) == set(EXCLUSION_PRIORITY)
        assert entry["replicate_point_row_count"] >= 0
        assert entry["toid_point_row_count"] <= entry["admitted_point_count"]


def test_the_cohort_totals_are_the_sums_of_the_parents() -> None:
    summary = load_summary()
    cohort = summary["cohort"]
    entries = cohort["parents"]
    for field in (
        "reported_row_count",
        "admitted_point_count",
        "admitted_bound_count",
        "independent_measurement_count",
        "independent_experiment_count",
        "parent_form_point_count",
        "salt_form_point_count",
    ):
        assert cohort[field] == sum(entry[field] for entry in entries), field
    totals: dict[str, int] = {}
    for entry in entries:
        for reason, count in entry["exclusion_counts"].items():
            totals[reason] = totals.get(reason, 0) + count
    assert totals == dict(cohort["exclusion_counts"])


def test_the_admission_funnel_ends_at_the_admitted_point_measurements() -> None:
    summary = load_summary()
    cohort = summary["cohort"]
    funnel = cohort["admission_funnel"]
    assert funnel[0]["stage"] == "reported_rows"
    assert funnel[0]["remaining"] == cohort["reported_row_count"]
    for previous, stage in zip(funnel, funnel[1:], strict=False):
        assert stage["remaining"] == previous["remaining"] - stage["removed"], stage["stage"]
    assert funnel[-1]["stage"] == "admitted_point"
    assert funnel[-1]["remaining"] == cohort["admitted_point_count"]
    bound_stage = next(stage for stage in funnel if stage["stage"] == "admitted_bound")
    assert bound_stage["removed"] == cohort["admitted_bound_count"]
    stages = [stage["stage"] for stage in funnel]
    for reason in EXCLUSION_PRIORITY:
        assert stages.index(reason) < stages.index("admitted_bound")


def test_the_named_examples_are_present_and_bounded() -> None:
    summary = load_summary()
    examples = summary["named_examples"]
    gap = examples["largest_row_to_measurement_gap"]
    assert gap["parent_molecule_chembl_id"] in set(COHORT_PARENTS)
    assert gap["reported_row_count"] >= gap["independent_measurement_count"]
    assert gap["rows_per_independent_measurement"] >= 1.0

    salt = examples["highest_salt_form_share"]
    assert salt["parent_molecule_chembl_id"] in set(COHORT_PARENTS)
    assert 0.0 <= salt["salt_form_share"] <= 1.0
    assert salt["salt_form_point_count"] <= salt["admitted_point_count"]

    for empty in examples["parents_without_admitted_measurement"]:
        assert empty["parent_molecule_chembl_id"] in set(COHORT_PARENTS)

    context = examples["one_reported_value_in_full_context"]
    assert context["parent_molecule_chembl_id"] in set(COHORT_PARENTS)
    assert context["assay_chembl_id"]
    assert context["document_chembl_id"]
    assert context["standard_relation"] == "="
    assert context["standard_units"] == "nM"


def test_the_summary_carries_no_raw_rows_and_no_structures() -> None:
    summary = load_summary()
    serialized = json.dumps(summary)
    assert "canonical_smiles" not in serialized
    assert '"activities"' not in serialized
    assert len(serialized) < 200_000
