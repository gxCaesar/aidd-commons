from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.chembl_egfr.protocol import (
    CHEMBL_RELEASE_DATE,
    CHEMBL_VERSION,
    DESCRIPTOR_EXCLUSIONS,
    EXTERNAL_ASSAY_ID,
    MORGAN_BITS,
    MORGAN_INCLUDE_CHIRALITY,
    MORGAN_RADIUS,
    PCHEMBL_CONSISTENCY_TOLERANCE,
    PRIMARY_ASSAY_ID,
    PROTOCOL_VERSION,
    RIDGE_ALPHAS,
    descriptor_names,
    execution_amendment_payload,
    protocol_payload,
)
from rdkit.Chem import Descriptors

REPOSITORY_ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = REPOSITORY_ROOT / "labs" / "chembl_egfr" / "protocol.json"


def test_protocol_freezes_release_assays_representations_and_model_selection() -> None:
    assert PROTOCOL_VERSION == "chembl37-egfr-representation-v1"
    assert CHEMBL_VERSION == "ChEMBL_37"
    assert CHEMBL_RELEASE_DATE == "2026-05-01"
    assert PRIMARY_ASSAY_ID == "CHEMBL5736995"
    assert EXTERNAL_ASSAY_ID == "CHEMBL3705421"
    assert (MORGAN_RADIUS, MORGAN_BITS, MORGAN_INCLUDE_CHIRALITY) == (2, 2048, True)
    assert PCHEMBL_CONSISTENCY_TOLERANCE == 0.011
    assert RIDGE_ALPHAS == (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)


def test_descriptor_registry_is_explicit_complete_and_excludes_morgan_summaries() -> None:
    names = descriptor_names()
    installed_names = tuple(
        name for name, _ in Descriptors._descList if name not in DESCRIPTOR_EXCLUSIONS
    )

    assert DESCRIPTOR_EXCLUSIONS == frozenset(
        {"FpDensityMorgan1", "FpDensityMorgan2", "FpDensityMorgan3"}
    )
    assert names == installed_names
    assert len(names) == 214
    assert len(names) == len(set(names))
    assert set(names).isdisjoint(DESCRIPTOR_EXCLUSIONS)


def test_public_protocol_matches_the_runtime_contract_exactly() -> None:
    on_disk = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    assert on_disk == protocol_payload()
    assert on_disk["split"]["scaffold_include_chirality"] is True
    assert on_disk["labels"]["parent_aggregation"] == "median"
    assert on_disk["labels"]["pchembl_consistency_tolerance"] == 0.011
    assert on_disk["locked_evaluation"]["state"] == "not_run"


def test_execution_amendment_distributed_to_readers_matches_locked_runtime():
    amendment_path = PROTOCOL_PATH.with_name("execution-amendment.json")
    assert json.loads(amendment_path.read_text()) == execution_amendment_payload()
