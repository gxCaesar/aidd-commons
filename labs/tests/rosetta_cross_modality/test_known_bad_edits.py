"""Known-bad edits of the frozen contract must stop the pipeline.

The contract is `labs/rosetta_cross_modality/protocol.json`. This test
mutates it in named ways and requires the pipeline to refuse each mutation.
A mutation the pipeline accepts is a failure, not a pass.

The pipeline is driven end to end on a self-contained synthetic snapshot
(`conftest.build_snapshot`), so no network and no 26 MiB cache are needed:
the contract's byte lengths and entity tags are computed from the synthetic
bytes, and the two objects are served by an injected fetcher. The mutations
that concern the data path therefore have to be caught by the data path, and
the ones that concern the contract by the contract reader.

The rejected run must leave nothing behind. The pipeline writes a results
directory and the committed summary, so neither may exist after a rejection,
and neither may a half-written object in the cache.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.rosetta_cross_modality.protocol import ContractError, load_contract
from aidd_commons.rosetta_cross_modality.summary import run_lab

from .conftest import build_snapshot, fetcher_for, write_contract

MUTATIONS = (
    "transcriptome_byte_length",
    "imaging_entity_tag",
    "source_url",
    "source_relative_path",
    "transcriptome_feature_pattern",
    "imaging_feature_pattern",
    "join_key_not_a_perturbation_column",
    "required_label_column_dropped",
    "join_key_collapses_the_catalogue",
    "control_pert_type",
    "empty_penalty_grid",
    "seed_is_not_an_integer",
    "outer_folds_of_one",
    "aggregation_the_code_does_not_implement",
)


def _mutate(document: dict[str, Any], mutation: str) -> dict[str, Any]:
    broken = copy.deepcopy(document)
    files = broken["source"]["files"]
    if mutation == "transcriptome_byte_length":
        files[0]["byte_length"] = files[0]["byte_length"] + 1
    elif mutation == "imaging_entity_tag":
        files[1]["s3_etag"] = "0" * 32
    elif mutation == "source_url":
        files[0]["url"] = files[0]["url"].replace("L1000/", "CellPainting/")
    elif mutation == "source_relative_path":
        files[0]["relative_path"] = "L1000/some_other_file.csv.gz"
    elif mutation == "transcriptome_feature_pattern":
        broken["label_contract"]["transcriptome_feature_pattern"] = "^probe_[0-9]+$"
    elif mutation == "imaging_feature_pattern":
        broken["label_contract"]["imaging_feature_pattern"] = "^compartment_[0-9]+$"
    elif mutation == "join_key_not_a_perturbation_column":
        broken["entity"]["join_key"]["transcriptome"] = "Metadata_Plate"
    elif mutation == "required_label_column_dropped":
        broken["entity"]["transcriptome_required_columns"] = [
            column
            for column in broken["entity"]["transcriptome_required_columns"]
            if column != "allele"
        ]
    elif mutation == "join_key_collapses_the_catalogue":
        broken["entity"]["join_key"]["transcriptome"] = "pert_type"
    elif mutation == "control_pert_type":
        broken["entity"]["control_pert_type"] = "negcon"
    elif mutation == "empty_penalty_grid":
        broken["model"]["penalty_grid"] = []
    elif mutation == "seed_is_not_an_integer":
        broken["seed"] = "twenty twenty one"
    elif mutation == "outer_folds_of_one":
        broken["outer_folds"] = 1
    elif mutation == "aggregation_the_code_does_not_implement":
        broken["entity"]["profile_aggregation"] = "mean across replicate wells"
    else:
        raise AssertionError(f"unknown mutation {mutation!r}")
    return broken


def _run(document: dict[str, Any], root: Path, snapshot) -> None:
    contract_path = write_contract(root / "protocol.json", document)
    contract = load_contract(contract_path)
    run_lab(
        contract,
        root / ".cache/rosetta_cross_modality",
        root / "results",
        root / "summary.json",
        computed_on="2026-10-21",
        software={"python": "3.11.15"},
        fetch=fetcher_for(snapshot),
    )


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_known_bad_contract_is_rejected(tmp_path: Path, mutation: str) -> None:
    snapshot = build_snapshot()
    document = _mutate(snapshot.contract_document, mutation)
    with pytest.raises(ContractError):
        _run(document, tmp_path, snapshot)
    # A rejected contract leaves no artefact behind. The cache is an input,
    # not an artefact, so a published object that was fetched before the
    # refusal may be there; what must not be there is a result, a committed
    # summary or a half-written object.
    assert not (tmp_path / "results").exists()
    assert not (tmp_path / "summary.json").exists()
    assert not list(tmp_path.rglob("*.part"))


def test_the_unmutated_contract_is_accepted(tmp_path: Path) -> None:
    """The control: the pipeline must accept a contract it can honour."""
    snapshot = build_snapshot()
    _run(snapshot.contract_document, tmp_path, snapshot)
    assert (tmp_path / "results" / "computed-summary.json").is_file()
    assert (tmp_path / "summary.json").is_file()
    committed = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert committed["protocol_id"] == "synthetic-rosetta-cross-modality-v1"
    assert committed["counts"]["admitted_perturbations"] == 24


def test_a_rejected_contract_does_not_touch_the_committed_record(tmp_path: Path) -> None:
    """The committed summary of the real lab is never rewritten by a bad run."""
    snapshot = build_snapshot()
    committed = tmp_path / "summary.json"
    committed.write_text(
        '{"protocol_id": "synthetic-rosetta-cross-modality-v1"}\n', encoding="utf-8"
    )
    before = committed.read_bytes()
    with pytest.raises(ContractError):
        _run(_mutate(snapshot.contract_document, "outer_folds_of_one"), tmp_path, snapshot)
    assert committed.read_bytes() == before
