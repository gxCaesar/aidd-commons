"""The frozen contract for the decision-unit-scope lab, in compiled-in form.

This module is the authority for every load-bearing field of
`labs/decision_unit_scope/protocol.json`. The on-disk `protocol.json` must
match it exactly; `validate_protocol_document` refuses to let the pipeline run
otherwise, which is what makes a mutated contract fail loudly instead of
silently changing what the lab measures.

The contract is descriptive. Nothing here fits a model, tunes a threshold or
selects a split: the whole point of the lab is to count real measurements
against a declared unit of inference.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROTOCOL_ID = "chembl37-decision-unit-scope-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.decision-unit-scope-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.decision-unit-scope-summary.v1"
ISSUED_ON = "2026-10-21"

# The only number in this protocol that is not a count of something in ChEMBL.
# It is a fixed tie-break order for the named examples; no stochastic step
# happens anywhere in this lab.
SEED = 20261021

CHEMBL_VERSION = "ChEMBL_37"
CHEMBL_RELEASE_DATE = "2026-05-01"
CHEMBL_API_ROOT = "https://www.ebi.ac.uk"
CHEMBL_STATUS_URL = f"{CHEMBL_API_ROOT}/chembl/api/data/status.json"
CHEMBL_LICENSE_NAME = "Creative Commons Attribution-ShareAlike 3.0 Unported"
CHEMBL_LICENSE_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/LICENSE"
)
CHEMBL_RELEASE_README_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/README"
)
CHEMBL_SCHEMA_DOCUMENTATION_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/"
    "schema_documentation.txt"
)

# The declared cohort. Fifteen ChEMBL molecule identifiers, resolved through
# `molecule_hierarchy.parent_chembl_id` to ten distinct parent molecules.
#
# Selection rule: declared by the author before any activity row was fetched,
# so that every branch of the protocol's counting rule is exercised on real
# rows. Five of the fifteen seeds are salt formulations whose parent is also a
# seed (so the declared set of molecules is larger than the set of units of
# inference); three of the seeds are formulations rather than single molecules,
# two stored as two-component structures that ChEMBL keeps as their own parent
# and one named as a salt but stored with a single component; one seed has four
# ChEMBL rows and no admissible measurement; one has two admissible
# measurements; one has several thousand. This is a teaching cohort, not a
# random sample, and no proportion computed over it estimates a population
# rate.
COHORT_SEEDS: tuple[tuple[str, str], ...] = (
    ("CHEMBL929", "DELAVIRDINE MESYLATE"),
    ("CHEMBL593", "DELAVIRDINE"),
    ("CHEMBL1026", "FENOLDOPAM MESYLATE"),
    ("CHEMBL588", "FENOLDOPAM"),
    ("CHEMBL433", "VALPROATE SODIUM"),
    ("CHEMBL109", "VALPROIC ACID"),
    ("CHEMBL690", "PRAVASTATIN SODIUM"),
    ("CHEMBL1144", "PRAVASTATIN"),
    ("CHEMBL109745", "DARBUFELONE MESYLATE"),
    ("CHEMBL275835", "DARBUFELONE"),
    ("CHEMBL23393", "SODIUM LAURYL SULFATE"),
    ("CHEMBL13829", "MIXTURE OF MMC AND TA"),
    ("CHEMBL906", "MINOXIDIL SULFATE"),
    ("CHEMBL441", "THIOPENTAL"),
    ("CHEMBL25", "ASPIRIN"),
)

#: The distinct parent molecules the declared seeds resolve to, in sorted order.
COHORT_PARENTS: tuple[str, ...] = (
    "CHEMBL109",
    "CHEMBL1144",
    "CHEMBL13829",
    "CHEMBL23393",
    "CHEMBL25",
    "CHEMBL275835",
    "CHEMBL441",
    "CHEMBL588",
    "CHEMBL593",
    "CHEMBL906",
)

#: The ChEMBL standard types this protocol treats as one potency family.
ENDPOINT_TYPES: tuple[str, ...] = ("AC50", "EC50", "IC50", "Kd", "Ki")

#: The one unit this protocol admits. Rows in other units are excluded and
#: counted, never converted.
STANDARD_UNITS = "nM"

#: The relation that makes a row a point measurement.
POINT_RELATION = "="

#: Relations that make a row a bound rather than a point measurement.
BOUND_RELATIONS: tuple[str, ...] = ("<", "<=", ">", ">=")

#: Exclusion reasons, in the order they are applied to a row. The first reason
#: that matches is the row's reason, so the counts partition the input rows.
#: The order runs from what the row reports, to how ChEMBL curated it, to what
#: the row says about its own independence, to its quality flags.
EXCLUSION_PRIORITY: tuple[str, ...] = (
    "outside_endpoint_family",
    "non_nanomolar_units",
    "non_standard_activity",
    "potential_duplicate",
    "data_validity_comment",
    "missing_value",
    "missing_structure",
    "missing_relation",
)

#: The grouping unit. Two admitted point measurements are the same measurement
#: when they share all three of these fields.
GROUPING_FIELDS: tuple[str, ...] = ("assay_chembl_id", "document_chembl_id", "standard_type")

#: The experiment unit, reported alongside the grouping unit.
EXPERIMENT_FIELDS: tuple[str, ...] = ("assay_chembl_id", "document_chembl_id")

#: The activity fields fetched from the ChEMBL REST API. `only=` pins the
#: payload so that the cached artefact does not drift with API defaults.
ACTIVITY_FIELDS: tuple[str, ...] = (
    "activity_id",
    "assay_chembl_id",
    "assay_type",
    "canonical_smiles",
    "data_validity_comment",
    "document_chembl_id",
    "document_journal",
    "document_year",
    "molecule_chembl_id",
    "parent_molecule_chembl_id",
    "pchembl_value",
    "potential_duplicate",
    "standard_flag",
    "standard_relation",
    "standard_type",
    "standard_units",
    "standard_value",
    "target_chembl_id",
    "target_organism",
    "target_pref_name",
    "toid",
)

#: The assay fields fetched from the ChEMBL REST API.
ASSAY_FIELDS: tuple[str, ...] = (
    "assay_chembl_id",
    "assay_organism",
    "assay_tax_id",
    "assay_type",
    "bao_format",
    "confidence_score",
    "document_chembl_id",
    "relationship_type",
    "target_chembl_id",
)

#: How many assay identifiers are put into one REST request.
ASSAY_BATCH_SIZE = 200

#: How many activity rows are put into one REST request.
ACTIVITY_PAGE_SIZE = 1000

#: The byte length of every cached artefact at the frozen ChEMBL 37 release.
#: Filled in once the snapshot has been fetched; an empty entry means the
#: artefact is always re-fetched.
ARTIFACT_BYTE_LENGTHS: dict[str, int] = {
    "status.json": 231,
    "molecules.json": 4003,
    "activities-CHEMBL109.json": 5440753,
    "activities-CHEMBL1144.json": 1491763,
    "activities-CHEMBL13829.json": 2030,
    "activities-CHEMBL23393.json": 116508,
    "activities-CHEMBL25.json": 3504249,
    "activities-CHEMBL275835.json": 23503,
    "activities-CHEMBL441.json": 97917,
    "activities-CHEMBL588.json": 218661,
    "activities-CHEMBL593.json": 730939,
    "activities-CHEMBL906.json": 3616,
    "assays.json": 248931,
}


class ProtocolContractError(ValueError):
    """Raised when the on-disk protocol departs from the compiled-in contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolContractError(message)


def _require_sequence(value: Any, message: str) -> Sequence[Any]:
    _require(isinstance(value, (list, tuple)), message)
    assert isinstance(value, (list, tuple))
    return value


def _require_mapping(value: Any, message: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), message)
    assert isinstance(value, Mapping)
    return value


def _require_str(value: Any, message: str) -> str:
    _require(isinstance(value, str) and value.strip() != "", message)
    assert isinstance(value, str)
    return value


def _require_equal(value: Any, expected: Any, message: str) -> None:
    _require(value == expected, f"{message}: expected {expected!r}, found {value!r}")


def _require_date(value: Any, message: str) -> str:
    text = _require_str(value, message)
    _require(
        len(text) == 10 and text[4] == "-" and text[7] == "-" and text[:4].isdigit(),
        f"{message}: must be an ISO calendar date",
    )
    return text


def load_protocol_document(path: Path) -> dict[str, Any]:
    """Load the on-disk protocol and refuse it if it departs from this module."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolContractError(
            f"could not read the protocol document {path}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise ProtocolContractError(f"the protocol document {path} is not a JSON object")
    validate_protocol_document(payload)
    return payload


def expected_artifacts() -> list[dict[str, Any]]:
    """The artefact table the on-disk protocol must declare."""
    artifacts: list[dict[str, Any]] = [
        {
            "path": "status.json",
            "source_url": CHEMBL_STATUS_URL,
            "byte_length": ARTIFACT_BYTE_LENGTHS.get("status.json"),
        },
        {
            "path": "molecules.json",
            "source_url": f"{CHEMBL_API_ROOT}/chembl/api/data/molecule/{{molecule_chembl_id}}.json",
            "byte_length": ARTIFACT_BYTE_LENGTHS.get("molecules.json"),
        },
    ]
    for parent_id in COHORT_PARENTS:
        artifacts.append(
            {
                "path": f"activities-{parent_id}.json",
                "source_url": (
                    f"{CHEMBL_API_ROOT}/chembl/api/data/activity.json"
                    f"?parent_molecule_chembl_id={parent_id}"
                ),
                "byte_length": ARTIFACT_BYTE_LENGTHS.get(f"activities-{parent_id}.json"),
            }
        )
    artifacts.append(
        {
            "path": "assays.json",
            "source_url": f"{CHEMBL_API_ROOT}/chembl/api/data/assay.json",
            "byte_length": ARTIFACT_BYTE_LENGTHS.get("assays.json"),
        }
    )
    return artifacts


def validate_protocol_document(document: Mapping[str, Any]) -> None:
    """Refuse a protocol document that departs from the compiled-in contract.

    Every load-bearing field is compared. The prose fields are required to be
    present and non-empty, because a contract that cannot explain itself is
    not a contract, but their wording is the author's to write.
    """
    _require_equal(
        document.get("schema_version"), PROTOCOL_SCHEMA_VERSION, "protocol schema_version"
    )
    _require_equal(document.get("protocol_id"), PROTOCOL_ID, "protocol id")
    _require_equal(document.get("issued_on"), ISSUED_ON, "protocol issued_on")
    _require_equal(document.get("seed"), SEED, "protocol seed")

    for field in ("declared_question", "run_basis"):
        _require_str(document.get(field), f"protocol {field} must be a non-empty string")

    source = _require_mapping(document.get("source"), "protocol source must be a mapping")
    _require_equal(source.get("database"), CHEMBL_VERSION, "source database")
    _require_equal(source.get("release_date"), CHEMBL_RELEASE_DATE, "source release_date")
    _require_equal(source.get("status_url"), CHEMBL_STATUS_URL, "source status_url")
    _require_equal(source.get("api_root"), CHEMBL_API_ROOT, "source api_root")
    licence = _require_mapping(source.get("licence"), "source licence must be a mapping")
    _require_equal(licence.get("name"), CHEMBL_LICENSE_NAME, "source licence name")
    _require_equal(licence.get("url"), CHEMBL_LICENSE_URL, "source licence url")

    cohort = _require_mapping(document.get("cohort"), "protocol cohort must be a mapping")
    _require_str(cohort.get("selection_rule"), "cohort selection_rule must be a non-empty string")
    declared_seeds = _require_sequence(cohort.get("seeds"), "cohort seeds must be a sequence")
    _require_equal(
        [(entry.get("molecule_chembl_id"), entry.get("pref_name")) for entry in declared_seeds],
        list(COHORT_SEEDS),
        "cohort seeds",
    )
    _require_equal(
        list(cohort.get("resolved_parents") or []),
        list(COHORT_PARENTS),
        "cohort resolved_parents",
    )

    entity = _require_mapping(document.get("entity_rule"), "entity_rule must be a mapping")
    for field in (
        "unit_of_inference",
        "child_parent_rule",
        "salt_rule",
        "mixture_rule",
        "contrast_with_sibling_lab",
    ):
        _require_str(entity.get(field), f"entity_rule.{field} must be a non-empty string")

    endpoint = _require_mapping(document.get("endpoint"), "endpoint must be a mapping")
    _require_str(endpoint.get("definition"), "endpoint definition must be a non-empty string")
    _require_equal(
        list(endpoint.get("standard_types") or []), list(ENDPOINT_TYPES), "endpoint standard_types"
    )
    _require_equal(endpoint.get("standard_units"), STANDARD_UNITS, "endpoint standard_units")
    _require_equal(endpoint.get("point_relation"), POINT_RELATION, "endpoint point_relation")
    _require_equal(
        list(endpoint.get("bound_relations") or []),
        list(BOUND_RELATIONS),
        "endpoint bound_relations",
    )
    _require_equal(
        list(endpoint.get("exclusion_priority") or []),
        list(EXCLUSION_PRIORITY),
        "endpoint exclusion_priority",
    )

    grouping = _require_mapping(
        document.get("split_and_grouping"), "split_and_grouping must be a mapping"
    )
    for field in ("split", "preprocessing_fit_scope", "assay_artefact_scope"):
        _require_str(grouping.get(field), f"split_and_grouping.{field} must be a non-empty string")
    _require_equal(
        list(grouping.get("grouping_unit") or []), list(GROUPING_FIELDS), "grouping_unit"
    )
    _require_equal(
        list(grouping.get("experiment_unit") or []), list(EXPERIMENT_FIELDS), "experiment_unit"
    )

    baselines = _require_sequence(document.get("baselines"), "baselines must be a sequence")
    _require(len(baselines) >= 1, "baselines must declare at least one baseline")
    metrics = _require_sequence(document.get("metrics"), "metrics must be a sequence")
    _require(len(metrics) >= 1, "metrics must declare at least one metric")

    selection = _require_mapping(
        document.get("selection_and_stop_policy"), "selection_and_stop_policy must be a mapping"
    )
    for field in ("calibration_rule", "selection_budget", "stop_rule"):
        _require_str(
            selection.get(field), f"selection_and_stop_policy.{field} must be a non-empty string"
        )

    declared_artifacts = _require_sequence(
        document.get("artifacts"), "artifacts must be a sequence"
    )
    expected = expected_artifacts()
    _require_equal(
        len(declared_artifacts), len(expected), "the number of declared artefacts"
    )
    for declared, reference in zip(declared_artifacts, expected, strict=True):
        entry = _require_mapping(declared, "each artefact must be a mapping")
        _require_equal(entry.get("path"), reference["path"], "artefact path")
        _require_equal(entry.get("source_url"), reference["source_url"], "artefact source_url")
        declared_length = entry.get("byte_length")
        expected_length = reference["byte_length"]
        _require_equal(
            declared_length,
            expected_length,
            f"artefact byte_length for {reference['path']}",
        )
        if expected_length is not None:
            _require(
                isinstance(declared_length, int) and declared_length > 0,
                f"artefact byte_length for {reference['path']} must be a positive integer",
            )

    excluded = _require_sequence(
        document.get("excluded_by_design"), "excluded_by_design must be a sequence"
    )
    _require(len(excluded) >= 1, "excluded_by_design must declare at least one exclusion")
