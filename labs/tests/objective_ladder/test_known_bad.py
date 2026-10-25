"""A mutated contract must be refused before anything is read or written."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.objective_ladder.protocol import ContractError, load_protocol

LAB = Path(__file__).resolve().parents[2] / "objective_ladder"
CONTRACT_PATH = LAB / "protocol.json"


@pytest.mark.parametrize(
    "mutation",
    [
        "schema_version",
        "protocol_id",
        "objectives",
        "tolerances",
        "targets",
        "sources",
    ],
)
def test_a_known_bad_contract_is_rejected(tmp_path: Path, mutation: str) -> None:
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if mutation == "schema_version":
        document["schema_version"] = "something-else"
    elif mutation == "protocol_id":
        document["protocol_id"] = "something-else"
    elif mutation == "objectives":
        document["objectives"] = document["objectives"][:-1]
    elif mutation == "tolerances":
        document["tolerances"] = {}
    elif mutation == "targets":
        document["targets"] = []
    elif mutation == "sources":
        document["sources"] = []
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ContractError):
        load_protocol(path)


def test_a_contract_that_names_a_tolerance_it_does_not_declare_is_rejected(
    tmp_path: Path,
) -> None:
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["tolerances"].pop("clash_distance_angstrom")
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ContractError, match="clash distance"):
        load_protocol(path)


def test_a_contract_with_a_tolerance_that_is_not_a_number_is_rejected(tmp_path: Path) -> None:
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["tolerances"]["clash_distance_angstrom"] = "two angstroms"
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises((ContractError, ValueError)):
        load_protocol(path)


def test_a_refused_contract_leaves_no_output_behind(tmp_path: Path) -> None:
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["protocol_id"] = "something-else"
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ContractError):
        load_protocol(path)
    assert not output.exists()
