"""The analysis: the sequence audit, the structural audit, and the separation."""

from __future__ import annotations

from pathlib import Path

import pytest
from aidd_commons.objective_ladder.analysis import (
    TargetEvidence,
    audit_recovery,
    audit_structure,
    build_ladder,
)
from aidd_commons.objective_ladder.data import (
    AffinityRecord,
    read_affinity_records,
    read_alphafold,
    read_coordinates,
    read_entry_accessions,
    read_structure,
    read_uniprot,
)
from aidd_commons.objective_ladder.protocol import (
    ABSENCE_REASONS,
    OBJECTIVES,
    ContractError,
    load_protocol,
)

LAB = Path(__file__).resolve().parents[2] / "objective_ladder"
CACHE = Path(".cache/objective_ladder")
REAL_CACHE_PRESENT = (CACHE / "read_on.txt").exists()

pytestmark = pytest.mark.skipif(
    not REAL_CACHE_PRESENT,
    reason="the public records have not been fetched on this machine",
)


def _protocol():
    return load_protocol(LAB / "protocol.json")


def _evidence(target, affinity=(), verified=frozenset()):
    """Read every record for one target and assemble its evidence."""
    uniprot = read_uniprot(target.accession, CACHE)
    alphafold = read_alphafold(target.accession, CACHE)
    structure = read_structure(target.structure_id, CACHE)
    coordinates = read_coordinates(target.structure_id, CACHE)
    recovery = audit_recovery(target.structure_id, coordinates, target.accession, uniprot.sequence)
    geometry = audit_structure(
        target.structure_id, coordinates, _protocol().tolerances, recovery.entity_id
    )
    return TargetEvidence(
        target=target,
        uniprot=uniprot,
        alphafold=alphafold,
        structure=structure,
        geometry=geometry,
        recovery=recovery,
        affinity=tuple(affinity),
        structure_codes=(target.structure_id,),
        verified_codes=frozenset(verified),
    )


def test_the_audit_reads_the_declared_coordinates_and_reports_two_counts() -> None:
    protocol = _protocol()
    audit = audit_structure("1IVO", read_coordinates("1IVO", CACHE), protocol.tolerances)
    assert audit.audited
    assert audit.atom_rows >= protocol.tolerances.minimum_coordinate_rows
    assert audit.bond_length_outliers >= 0
    assert audit.clashes >= 0


def test_a_structure_with_too_few_rows_is_declined_rather_than_audited() -> None:
    protocol = _protocol()
    audit = audit_structure("1IVO", "not a coordinate file", protocol.tolerances)
    assert not audit.audited
    assert audit.atom_rows == 0
    assert audit.note


def test_the_audit_says_how_many_rows_belong_to_the_examined_entity() -> None:
    protocol = _protocol()
    audit = audit_structure("1IVO", read_coordinates("1IVO", CACHE), protocol.tolerances, "1")
    assert audit.audited
    assert audit.entity_rows["1"] > 0
    assert sum(audit.entity_rows.values()) == audit.atom_rows


def test_the_sequence_audit_counts_matched_positions_over_the_evaluated_region() -> None:
    """The fraction is counted, not asserted, and it is a fraction of a region."""
    uniprot = read_uniprot("P00374", CACHE)
    recovery = audit_recovery("1BOZ", read_coordinates("1BOZ", CACHE), "P00374", uniprot.sequence)
    assert recovery.audited
    assert recovery.evaluated_positions == 186
    assert recovery.matched_positions == 185
    assert recovery.fraction == pytest.approx(185 / 186)
    assert recovery.mismatches
    assert recovery.reference_accession == "P00374"


def test_the_sequence_audit_declines_an_entity_the_entry_does_not_hold() -> None:
    uniprot = read_uniprot("P00374", CACHE)
    recovery = audit_recovery("1BOZ", read_coordinates("1BOZ", CACHE), "P04637", uniprot.sequence)
    assert not recovery.audited
    assert recovery.evaluated_positions == 0
    assert recovery.note


def test_every_target_produces_one_outcome_per_objective() -> None:
    protocol = _protocol()
    for target in protocol.targets:
        ladder = build_ladder(_evidence(target), protocol)
        assert set(ladder.outcomes) == set(OBJECTIVES)
        assert ladder.evidenced + ladder.empty == len(OBJECTIVES)


def test_an_empty_cell_always_carries_a_declared_reason() -> None:
    protocol = _protocol()
    for target in protocol.targets:
        ladder = build_ladder(_evidence(target), protocol)
        for outcome in ladder.outcomes.values():
            if outcome.found:
                assert outcome.record
            else:
                assert outcome.absence_reason in ABSENCE_REASONS
                assert outcome.detail


def test_a_bound_component_is_not_counted_as_measured_binding_evidence() -> None:
    """A crystallisation additive is present in most entries, so it is not evidence."""
    protocol = _protocol()
    target = [item for item in protocol.targets if item.symbol == "ESR1"][0]
    ladder = build_ladder(_evidence(target), protocol)
    binding = ladder.outcomes["binding"]
    assert not binding.found
    assert "measured" in binding.detail


def test_a_row_without_an_affinity_value_leaves_the_binding_cell_empty() -> None:
    """The row exists and names a structure, but it carries no value to read."""
    protocol = _protocol()
    target = [item for item in protocol.targets if item.symbol == "ERBB2"][0]
    row = AffinityRecord(
        structure_code="3MZW",
        protein_group="3MZW_A",
        mutation="NA23T",
        affinity_wild_type=None,
        affinity_mutant=None,
        wild_type_text="",
        mutant_text="",
        method="",
        field_count=6,
    )
    ladder = build_ladder(_evidence(target, affinity=[row], verified={"3MZW"}), protocol)
    binding = ladder.outcomes["binding"]
    assert not binding.found
    assert binding.absence_reason == "no-affinity-value"
    assert "affinity value" in binding.detail


def test_a_row_with_a_value_fills_the_binding_cell_and_names_the_value() -> None:
    protocol = _protocol()
    target = [item for item in protocol.targets if item.symbol == "TP53"][0]
    row = AffinityRecord(
        structure_code="1YCS",
        protein_group="1YCS_A_B",
        mutation="RA273H",
        affinity_wild_type=2.2e-06,
        affinity_mutant=1.8e-06,
        wild_type_text="2.2E-06",
        mutant_text="1.8E-06",
        method="ITC",
        field_count=29,
    )
    ladder = build_ladder(_evidence(target, affinity=[row], verified={"1YCS"}), protocol)
    binding = ladder.outcomes["binding"]
    assert binding.found
    assert "1YCS" in binding.record
    assert "2.2e-06" in binding.record
    assert "1.8e-06" in binding.record


def test_a_row_naming_a_structure_the_entry_does_not_reference_is_refused() -> None:
    """The cell is only filled by a structure the archive itself links to the target."""
    protocol = _protocol()
    target = [item for item in protocol.targets if item.symbol == "TP53"][0]
    row = AffinityRecord(
        structure_code="1YCS",
        protein_group="1YCS_A_B",
        mutation="RA273H",
        affinity_wild_type=2.2e-06,
        affinity_mutant=1.8e-06,
        wild_type_text="2.2E-06",
        mutant_text="1.8E-06",
        method="ITC",
        field_count=29,
    )
    ladder = build_ladder(_evidence(target, affinity=[row], verified=set()), protocol)
    binding = ladder.outcomes["binding"]
    assert not binding.found
    assert binding.absence_reason == "no-affinity-record"


def test_the_folding_cell_marks_the_model_as_a_prediction() -> None:
    """A prediction is not an observation of folding, and the record says so."""
    protocol = _protocol()
    target = [item for item in protocol.targets if item.symbol == "TP53"][0]
    ladder = build_ladder(_evidence(target), protocol)
    folding = ladder.outcomes["folding"]
    assert folding.found
    assert "prediction" in folding.record
    assert "not an observation" in folding.record


def test_a_ladder_for_a_contract_with_a_different_objective_set_is_refused() -> None:
    """The ladder fills exactly the objectives the contract declares, and no other."""
    from dataclasses import replace

    protocol = _protocol()
    altered = replace(protocol, objectives=("sequence-recovery", "folding"))
    target = protocol.targets[0]
    with pytest.raises(ContractError, match="the contract declares"):
        build_ladder(_evidence(target), altered)


def test_the_affinity_rows_that_name_a_target_are_the_ones_the_entry_confirms() -> None:
    """The reader keeps the rows, and the archive confirms the structure."""
    affinity = read_affinity_records(CACHE)
    assert affinity
    for row in affinity:
        assert row.structure_code
        assert row.structure_code[0].isdigit()
    accessions = read_entry_accessions("1YCS", CACHE)
    assert "P04637" in accessions
    assert "P04626" not in accessions
