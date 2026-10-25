"""Show and re-check the real measurement census of a declared ChEMBL cohort.

    python labs/decision_unit_scope/inspect_decision_unit_scope.py show
    python labs/decision_unit_scope/inspect_decision_unit_scope.py check

`show` prints the entity resolution, the admission funnel, the per-compound
measurement census and a handful of named examples. `check` recomputes the
invariants and exits non-zero on any violation. It runs without a network and
without the local cache: the committed summary is enough for the summary
invariants, and when the cache is present the census is recomputed from it and
compared with the summary.

Needs the cache at `.cache/decision_unit_scope/` for the cache-based checks.
If it is not, first run:

    python labs/decision_unit_scope/run_lab.py download
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aidd_commons.decision_unit_scope.analysis import (  # noqa: E402
    AnalysisContractError,
    census_cohort,
    seeds_sharing_a_parent,
)
from aidd_commons.decision_unit_scope.data import (  # noqa: E402
    CohortDataset,
    DataContractError,
    load_cached_cohort,
)
from aidd_commons.decision_unit_scope.protocol import (  # noqa: E402
    COHORT_PARENTS,
    COHORT_SEEDS,
    PROTOCOL_ID,
    SUMMARY_SCHEMA_VERSION,
    ProtocolContractError,
    load_protocol_document,
)

LAB = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB.parents[1]
DEFAULT_CACHE_DIR = REPOSITORY_ROOT / ".cache/decision_unit_scope"
SUMMARY_PATH = LAB / "summary.json"


def load_summary() -> dict[str, Any]:
    try:
        payload = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataContractError(f"could not read the committed summary: {error}") from error
    if not isinstance(payload, dict):
        raise DataContractError("the committed summary is not a JSON object")
    return payload


def show(protocol: Mapping[str, Any], summary: Mapping[str, Any]) -> None:
    print(f"Declared question: {protocol['declared_question']}")
    print()

    resolution = summary["entity_resolution"]
    print(
        f"Declared cohort: {resolution['declared_seed_count']} ChEMBL molecules resolve to "
        f"{resolution['distinct_parent_count']} units of inference."
    )
    print("  molecule      name                     parent      own parent  fragments")
    for seed in resolution["seeds"]:
        print(
            f"  {seed['molecule_chembl_id']:<13} {seed['pref_name']:<24} "
            f"{seed['parent_molecule_chembl_id']:<11} "
            f"{str(seed['is_own_parent']):<11} {seed['stored_fragment_count']}"
        )
    print()

    cohort = summary["cohort"]
    print("Cohort admission funnel:")
    for stage in cohort["admission_funnel"]:
        print(
            f"  {stage['stage']:<26} removed {stage['removed']:>6}"
            f"   remaining {stage['remaining']:>6}"
        )
    print()

    print(
        f"Cohort totals: {cohort['reported_row_count']} reported rows -> "
        f"{cohort['admitted_point_count']} point measurements and "
        f"{cohort['admitted_bound_count']} bounds; "
        f"{cohort['independent_measurement_count']} independent measurements in "
        f"{cohort['independent_experiment_count']} independent experiments."
    )
    print()
    print(
        f"{'compound':<26} {'rows':>6} {'point':>6} {'bound':>6} {'meas':>6} "
        f"{'exp':>5} {'assay':>6} {'doc':>5} {'tgt':>5} {'salt':>5}"
    )
    for parent in cohort["parents"]:
        print(
            f"{parent['pref_name']:<26} {parent['reported_row_count']:>6} "
            f"{parent['admitted_point_count']:>6} {parent['admitted_bound_count']:>6} "
            f"{parent['independent_measurement_count']:>6} "
            f"{parent['independent_experiment_count']:>5} "
            f"{parent['distinct_assay_count']:>6} {parent['distinct_document_count']:>5} "
            f"{parent['distinct_target_count']:>5} {parent['salt_form_point_count']:>5}"
        )
    print()

    examples = summary["named_examples"]
    gap = examples["largest_row_to_measurement_gap"]
    print(
        f"Largest gap between rows and measurements: {gap['pref_name']} "
        f"({gap['parent_molecule_chembl_id']}) has {gap['reported_row_count']} ChEMBL rows and "
        f"{gap['independent_measurement_count']} independent measurements, "
        f"{gap['rows_per_independent_measurement']:.1f} rows per measurement."
    )
    salt = examples["highest_salt_form_share"]
    print(
        f"Highest salt-form share: {salt['pref_name']} "
        f"({salt['parent_molecule_chembl_id']}) has {salt['salt_form_point_count']} of "
        f"{salt['admitted_point_count']} admitted measurements reported on a child form "
        f"{salt['child_molecule_ids']}."
    )
    for empty in examples["parents_without_admitted_measurement"]:
        print(
            f"No admissible measurement: {empty['pref_name']} "
            f"({empty['parent_molecule_chembl_id']}) has {empty['reported_row_count']} ChEMBL rows "
            f"and no admitted point measurement under this protocol."
        )
    print()

    context = examples["one_reported_value_in_full_context"]
    print("One reported value and everything that has to travel with it:")
    for field in (
        "parent_pref_name",
        "activity_id",
        "tested_molecule_chembl_id",
        "tested_form",
        "standard_type",
        "standard_value",
        "standard_units",
        "standard_relation",
        "pchembl_value",
        "assay_chembl_id",
        "assay_type",
        "assay_organism",
        "confidence_score",
        "document_chembl_id",
        "document_journal",
        "document_year",
        "target_chembl_id",
        "target_pref_name",
        "target_organism",
        "toid",
    ):
        print(f"  {field:<26} {context[field]}")
    print()

    print("What this does not show, by the frozen protocol's own declaration:")
    for item in protocol["excluded_by_design"]:
        print(f"  - {item}")


def _summary_checks(summary: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        print(f"  [{'PASS' if condition else 'FAIL'}] {message}")
        if not condition:
            failures.append(message)

    require(summary.get("protocol_id") == PROTOCOL_ID, "the summary carries the frozen protocol id")
    require(
        summary.get("schema_version") == SUMMARY_SCHEMA_VERSION,
        "the summary carries the frozen summary schema version",
    )
    require(bool(summary.get("computed_on")), "the summary records when it was computed")
    require(bool(summary.get("software")), "the summary records the software versions used")

    resolution = summary["entity_resolution"]
    require(
        resolution["declared_seed_count"] == len(COHORT_SEEDS),
        "the summary declares every seed of the protocol",
    )
    require(
        resolution["distinct_parent_count"] == len(COHORT_PARENTS),
        "the summary declares every parent of the protocol",
    )
    declared = {(seed["molecule_chembl_id"], seed["pref_name"]) for seed in resolution["seeds"]}
    require(declared == set(COHORT_SEEDS), "the declared seeds and their names match the protocol")
    parents = {seed["parent_molecule_chembl_id"] for seed in resolution["seeds"]}
    require(parents == set(COHORT_PARENTS), "the declared seeds resolve to the declared parents")
    grouped: set[str] = set()
    groups = resolution["seed_groups_sharing_one_parent"]
    for group in groups:
        grouped.update(group["molecule_chembl_ids"])
    require(
        len(grouped)
        + resolution["distinct_parent_count"]
        - len(groups)
        == resolution["declared_seed_count"],
        "the collapsed seed groups account for the difference in size",
    )

    cohort = summary["cohort"]
    entries = cohort["parents"]
    require(len(entries) == len(COHORT_PARENTS), "the summary carries one entry per parent")
    require(
        {entry["parent_molecule_chembl_id"] for entry in entries} == set(COHORT_PARENTS),
        "the parent entries are exactly the declared parents",
    )

    for entry in entries:
        name = entry["pref_name"]
        excluded = sum(entry["exclusion_counts"].values())
        require(
            excluded + entry["admitted_point_count"] + entry["admitted_bound_count"]
            == entry["reported_row_count"],
            f"{name}: the exclusion counts partition every reported row",
        )
        require(
            entry["independent_measurement_count"] <= entry["admitted_point_count"],
            f"{name}: independent measurements never exceed admitted point measurements",
        )
        require(
            entry["independent_experiment_count"] <= entry["independent_measurement_count"],
            f"{name}: independent experiments never exceed independent measurements",
        )
        require(
            entry["distinct_assay_count"] <= entry["independent_experiment_count"],
            f"{name}: the assay count never exceeds the experiment count",
        )
        require(
            entry["parent_form_point_count"] + entry["salt_form_point_count"]
            == entry["admitted_point_count"],
            f"{name}: the parent-form and salt-form measurements add up to the admitted count",
        )
        require(
            entry["distinct_document_count"] <= entry["distinct_assay_count"],
            f"{name}: the document count never exceeds the assay count",
        )
        require(
            entry["distinct_target_count"] <= entry["distinct_assay_count"],
            f"{name}: the target count never exceeds the assay count",
        )

    for field in (
        "reported_row_count",
        "admitted_point_count",
        "admitted_bound_count",
        "independent_measurement_count",
        "independent_experiment_count",
    ):
        require(
            cohort[field] == sum(entry[field] for entry in entries),
            f"the cohort total for {field} is the sum of the parents",
        )
    excluded_total: dict[str, int] = {}
    for entry in entries:
        for reason, count in entry["exclusion_counts"].items():
            excluded_total[reason] = excluded_total.get(reason, 0) + count
    require(
        excluded_total == dict(cohort["exclusion_counts"]),
        "the cohort exclusion counts are the sum of the parents' exclusion counts",
    )

    funnel = cohort["admission_funnel"]
    require(
        funnel[0]["stage"] == "reported_rows"
        and funnel[0]["remaining"] == cohort["reported_row_count"],
        "the funnel starts from the reported row count",
    )
    for previous, stage in zip(funnel, funnel[1:], strict=False):
        require(
            stage["remaining"] == previous["remaining"] - stage["removed"],
            f"the funnel stage {stage['stage']} accounts for its removed rows",
        )
    require(
        funnel[-1]["stage"] == "admitted_point"
        and funnel[-1]["remaining"] == cohort["admitted_point_count"],
        "the funnel ends at the admitted point measurement count",
    )
    bound_stage = next(stage for stage in funnel if stage["stage"] == "admitted_bound")
    require(
        bound_stage["removed"] == cohort["admitted_bound_count"],
        "the funnel sets aside exactly the admitted bounds",
    )

    examples = summary["named_examples"]
    gap = examples["largest_row_to_measurement_gap"]
    require(
        gap["parent_molecule_chembl_id"] in set(COHORT_PARENTS),
        "the largest-gap example names a declared parent",
    )
    require(
        gap["reported_row_count"] >= gap["independent_measurement_count"],
        "the largest-gap example has at least as many rows as measurements",
    )
    salt = examples["highest_salt_form_share"]
    require(
        salt["parent_molecule_chembl_id"] in set(COHORT_PARENTS),
        "the salt-form example names a declared parent",
    )
    require(
        0.0 <= salt["salt_form_share"] <= 1.0,
        "the salt-form share is a proportion",
    )
    context = examples["one_reported_value_in_full_context"]
    require(
        context["parent_molecule_chembl_id"] in set(COHORT_PARENTS),
        "the fully contextualised example names a declared parent",
    )
    require(
        bool(context["assay_chembl_id"]) and bool(context["document_chembl_id"]),
        "the fully contextualised example names its assay and its document",
    )

    serialized = json.dumps(summary)
    require("canonical_smiles" not in serialized, "the summary carries no structures")
    require('"activities"' not in serialized, "the summary carries no raw activity rows")
    require(
        len(serialized) < 200_000,
        "the summary stays small enough to be read in one sitting",
    )
    return failures


def _cache_checks(
    summary: Mapping[str, Any], cohort: CohortDataset
) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        print(f"  [{'PASS' if condition else 'FAIL'}] {message}")
        if not condition:
            failures.append(message)

    census = census_cohort(cohort)
    require(
        len(census.seeds) == summary["entity_resolution"]["declared_seed_count"],
        "the cached cohort declares the same number of seeds as the summary",
    )
    require(
        len(census.parents) == summary["entity_resolution"]["distinct_parent_count"],
        "the cached cohort declares the same number of parents as the summary",
    )
    resolved = {seed.parent_molecule_chembl_id for seed in census.seeds}
    require(resolved == set(COHORT_PARENTS), "the cached cohort resolves to the declared parents")
    require(
        set(seeds_sharing_a_parent(census))
        == {
            (group["parent_molecule_chembl_id"], tuple(group["molecule_chembl_ids"]))
            for group in summary["entity_resolution"]["seed_groups_sharing_one_parent"]
        },
        "the cached cohort collapses the same seed groups as the summary",
    )

    by_id = {entry["parent_molecule_chembl_id"]: entry for entry in summary["cohort"]["parents"]}
    for item in census.parents:
        entry = by_id[item.parent_molecule_chembl_id]
        require(
            entry["reported_row_count"] == item.reported_row_count
            and entry["admitted_point_count"] == item.admitted_point_count
            and entry["admitted_bound_count"] == item.admitted_bound_count
            and entry["independent_measurement_count"] == item.independent_measurement_count
            and entry["independent_experiment_count"] == item.independent_experiment_count
            and entry["distinct_assay_count"] == item.distinct_assay_count
            and entry["salt_form_point_count"] == item.salt_form_point_count
            and dict(entry["exclusion_counts"]) == dict(item.exclusion_counts),
            f"{item.pref_name}: the cached census reproduces the committed counts",
        )
    require(
        summary["cohort"]["reported_row_count"] == census.reported_row_count
        and summary["cohort"]["admitted_point_count"] == census.admitted_point_count
        and summary["cohort"]["admitted_bound_count"] == census.admitted_bound_count
        and summary["cohort"]["independent_measurement_count"]
        == census.independent_measurement_count,
        "the cached census reproduces the committed cohort totals",
    )
    return failures


def check(protocol: Mapping[str, Any], summary: Mapping[str, Any], cache_dir: Path) -> list[str]:
    print("DECISION-UNIT-SCOPE CHECKS")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        print(f"  [{'PASS' if condition else 'FAIL'}] {message}")
        if not condition:
            failures.append(message)

    require(
        summary.get("protocol_id") == protocol.get("protocol_id"),
        "the committed summary was computed under the protocol on disk",
    )
    print("Summary invariants:")
    failures.extend(_summary_checks(summary))
    if cache_dir.is_dir():
        print("Cache invariants:")
        try:
            cohort = load_cached_cohort(cache_dir)
        except DataContractError as error:
            print(f"  [FAIL] the cached cohort could not be loaded: {error}")
            failures.append("the cached cohort could not be loaded")
            return failures
        failures.extend(_cache_checks(summary, cohort))
    else:
        print(
            f"Cache invariants: skipped, {cache_dir} is not present. Run "
            "'python labs/decision_unit_scope/run_lab.py download' to fetch it."
        )
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args(argv)
    try:
        protocol = load_protocol_document(LAB / "protocol.json")
        summary = load_summary()
    except (DataContractError, ProtocolContractError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    if args.action == "show":
        try:
            show(protocol, summary)
        except (AnalysisContractError, KeyError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            sys.exit(1)
        print()
        print("Run 'check' to recompute these relationships.")
        return 0
    failures = check(protocol, summary, args.cache_dir)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print(
        "All checks passed. This verifies the admission rule, the entity resolution and the "
        "counting arithmetic; it does not verify that any compound is potent, selective or safe."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
