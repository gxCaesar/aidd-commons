"""Compiled authority for the split and leakage audit protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aidd_commons.decision_unit_scope import protocol as source_contract

PROTOCOL_ID = "chembl37-split-leakage-routes-v1"
PROTOCOL_SCHEMA_VERSION = "aidd-commons.split-leakage-audit-protocol.v1"
SUMMARY_SCHEMA_VERSION = "aidd-commons.split-leakage-audit-summary.v1"
ISSUED_ON = "2026-10-23"
SEED = 20261023
TRAIN_FRACTION = 0.8
#: The RDKit release the committed reading was computed with. It is frozen here
#: rather than read from the running environment, so the protocol stays valid
#: on a machine that carries another release, and the environment is compared
#: with it instead.
RDKIT_VERSION = "2025.09.6"
ROUTES = {
    "parent": "parent_molecule_chembl_id",
    "scaffold": "Bemis-Murcko scaffold of canonical_smiles",
    "assay": "assay_chembl_id",
    "target": "target_chembl_id",
    "standard_form": "RDKit canonical isomeric SMILES of canonical_smiles",
}
UNTESTABLE = {
    "temporal": "The activity rows have no measurement date.",
    "donor": "The activity rows have no donor identifier.",
    "patient": "The activity rows have no patient identifier.",
    "site": "The activity rows have no collection site identifier.",
    "target-family": (
        "The activity rows carry a target identifier and not a protein family, and the "
        "snapshot carries no target-to-family mapping, so a route through a family of "
        "related targets cannot be measured here."
    ),
    "fitted-preprocessing": (
        "The table holds measurements rather than a fitted transformation, so a "
        "preprocessing step fitted on the test set cannot be observed here."
    ),
}
EXCLUDED_BY_DESIGN = (
    "A claim that a split is free of leakage beyond the routes measured here.",
    "A performance estimate or a claim of prediction for a new compound.",
    "Selecting a split because it improves a reported number.",
)


class ProtocolError(ValueError):
    """The on-disk document differs from the frozen compiled contract."""


def expected_fields() -> dict[str, Any]:
    """All fields that can change the cohort, split, route or interpretation."""
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "issued_on": ISSUED_ON,
        "source": {
            "database": source_contract.CHEMBL_VERSION,
            "release_date": source_contract.CHEMBL_RELEASE_DATE,
            "status_url": source_contract.CHEMBL_STATUS_URL,
            "api_root": source_contract.CHEMBL_API_ROOT,
            "licence": {
                "name": source_contract.CHEMBL_LICENSE_NAME,
                "url": source_contract.CHEMBL_LICENSE_URL,
            },
        },
        "cohort": {
            "seeds": [
                {"molecule_chembl_id": identifier, "pref_name": name}
                for identifier, name in source_contract.COHORT_SEEDS
            ],
            "resolved_parents": list(source_contract.COHORT_PARENTS),
        },
        "endpoint": {
            "standard_types": list(source_contract.ENDPOINT_TYPES),
            "standard_units": source_contract.STANDARD_UNITS,
            "point_relation": source_contract.POINT_RELATION,
            "bound_relations": list(source_contract.BOUND_RELATIONS),
            "exclusion_priority": list(source_contract.EXCLUSION_PRIORITY),
            "measurement_grouping_fields": [
                "parent_molecule_chembl_id",
                *source_contract.GROUPING_FIELDS,
            ],
        },
        "split": {
            "row_rule": (
                "Sort independent measurement keys, shuffle with Python random.Random(seed), "
                "and assign the first floor(train_fraction * count) to training."
            ),
            "group_rule": (
                "Sort parent identifiers, shuffle with Python random.Random(seed), "
                "and assign the first floor(train_fraction * parent_count) to training."
            ),
            "seed": SEED,
            "train_fraction": TRAIN_FRACTION,
        },
        "tested_routes": [{"route": route, "field": field} for route, field in ROUTES.items()],
        "rdkit_version": RDKIT_VERSION,
        "untestable_routes": [
            {"route": route, "reason": reason} for route, reason in UNTESTABLE.items()
        ],
        "artifacts": source_contract.expected_artifacts(),
        "excluded_by_design": list(EXCLUDED_BY_DESIGN),
    }


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ProtocolError("protocol cannot be read") from error
    if not isinstance(document, dict):
        raise ProtocolError("protocol must be an object")
    for field, expected in expected_fields().items():
        if document.get(field) != expected:
            raise ProtocolError(f"changed protocol field: {field}")
    return document
