"""The data contract: what the laboratory reads, and what it refuses to read."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.objective_ladder.data import (
    DataContractError,
    fetch,
    read_affinity_records,
    read_alphafold,
    read_entry_accessions,
    read_structure,
    read_uniprot,
)
from aidd_commons.objective_ladder.protocol import ContractError, load_protocol

LAB = Path(__file__).resolve().parents[2] / "objective_ladder"
CACHE = Path(".cache/objective_ladder")
REAL_CACHE_PRESENT = (CACHE / "read_on.txt").exists()

pytestmark = pytest.mark.skipif(
    not REAL_CACHE_PRESENT,
    reason="the public records have not been fetched on this machine",
)


def test_the_committed_contract_declares_six_objectives_and_six_targets() -> None:
    protocol = load_protocol(LAB / "protocol.json")
    assert len(protocol.objectives) == 6
    assert len(protocol.targets) == 6
    assert protocol.protocol_id == "objective-ladder-six-objectives-v1"


def test_the_contract_names_the_source_of_every_objective() -> None:
    from aidd_commons.objective_ladder.protocol import OBJECTIVE_SOURCES

    protocol = load_protocol(LAB / "protocol.json")
    for objective in protocol.objectives:
        assert objective in OBJECTIVE_SOURCES
    for source in protocol.sources:
        assert source.licence
        assert source.route.startswith("https://")


def test_the_read_accession_carries_a_sequence_and_an_annotation() -> None:
    record = read_uniprot("P00374", CACHE)
    assert record.accession == "P00374"
    assert record.sequence_length > 0
    assert record.function_text
    assert len(record.sequence) == record.sequence_length
    assert record.sequence.startswith("M")


def test_the_read_accession_carries_every_catalytic_annotation() -> None:
    """An accession can carry several catalytic activities, and each has a catalogue number."""
    record = read_uniprot("P08183", CACHE)
    assert len(record.catalysis) > 1
    assert record.ec_numbers
    assert all(reaction for reaction in record.catalysis)


def test_the_read_structure_reports_its_method_and_its_components() -> None:
    record = read_structure("1IVO", CACHE)
    assert record.entry_id == "1IVO"
    assert record.method
    assert record.polymer_entity_ids


def test_the_model_archive_entry_carries_a_global_metric() -> None:
    record = read_alphafold("P00374", CACHE)
    assert record is not None
    assert record.entry_id.startswith("AF-P00374")
    assert record.global_metric is not None


def test_the_affinity_archive_is_read_by_position_and_padded() -> None:
    records = read_affinity_records(CACHE)
    assert records
    for record in records:
        assert record.structure_code
        assert record.structure_code[0].isdigit()


def test_the_affinity_rows_state_whether_they_carry_a_value() -> None:
    """A row of the mirror can name a structure and carry no value at all."""
    records = read_affinity_records(CACHE)
    without_value = [record for record in records if not record.carries_a_value]
    with_value = [record for record in records if record.carries_a_value]
    assert without_value
    assert with_value
    assert all(record.carries_a_change for record in records if record.affinity_mutant is not None)


def test_the_entry_states_the_accessions_its_entities_reference() -> None:
    accessions = read_entry_accessions("1YCS", CACHE)
    assert "P04637" in accessions
    assert read_entry_accessions("1BOZ", CACHE) == ("P00374",)


def test_a_missing_record_is_refused_rather_than_guessed(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        read_uniprot("NOT_AN_ACCESSION", tmp_path / "empty")


def test_a_contract_without_the_expected_identifier_is_refused(tmp_path: Path) -> None:
    document = json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))
    document["protocol_id"] = "something-else"
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ContractError, match="protocol identifier"):
        load_protocol(path)


def test_a_contract_with_a_different_objective_set_is_refused(tmp_path: Path) -> None:
    document = json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))
    document["objectives"] = document["objectives"][:3]
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ContractError, match="objectives"):
        load_protocol(path)


def test_a_contract_without_tolerances_is_refused(tmp_path: Path) -> None:
    document = json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))
    del document["tolerances"]
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ContractError, match="tolerances"):
        load_protocol(path)


def test_a_cached_record_is_not_fetched_again(tmp_path: Path) -> None:
    target = tmp_path / "cached"
    target.mkdir()
    (target / "probe.txt").write_bytes(b"cached payload")
    from aidd_commons.objective_ladder.data import _cache_name

    name = _cache_name("https://example.invalid/probe")
    (target / name).write_bytes(b"cached payload")
    assert fetch("https://example.invalid/probe", target) == b"cached payload"
