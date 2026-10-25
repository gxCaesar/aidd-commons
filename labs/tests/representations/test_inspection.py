from __future__ import annotations

import json

import pytest
from aidd_commons.representations.inspection import (
    MoleculeInput,
    RepresentationConfig,
    RepresentationInputError,
    build_report,
    inspect_molecules,
    render_report,
)


def test_equivalent_smiles_converge_to_one_toolkit_canonical_form() -> None:
    inspections = inspect_molecules(
        (
            MoleculeInput("pyridine-kekule", "C1=CC=CN=C1", "equivalent traversal"),
            MoleculeInput("pyridine-aromatic", "n1ccccc1", "equivalent traversal"),
        )
    )

    assert inspections[0].input_smiles != inspections[1].input_smiles
    assert inspections[0].canonical_isomeric_smiles == inspections[1].canonical_isomeric_smiles
    assert inspections[0].inchi_key == inspections[1].inchi_key


def test_nonisomeric_smiles_collapses_defined_enantiomers() -> None:
    inspections = inspect_molecules(
        (
            MoleculeInput("alanine-one", "N[C@@H](C)C(=O)O", "defined stereochemistry"),
            MoleculeInput("alanine-two", "N[C@H](C)C(=O)O", "opposite stereochemistry"),
        )
    )

    assert inspections[0].canonical_isomeric_smiles != inspections[1].canonical_isomeric_smiles
    assert (
        inspections[0].canonical_nonisomeric_smiles
        == inspections[1].canonical_nonisomeric_smiles
    )
    assert inspections[0].inchi_key != inspections[1].inchi_key
    assert all(item.specified_stereocenters == 1 for item in inspections)


def test_disconnected_salt_is_not_silently_converted_to_a_parent() -> None:
    [inspection] = inspect_molecules(
        (MoleculeInput("sodium-acetate", "CC(=O)[O-].[Na+]", "disconnected salt"),)
    )

    assert inspection.component_count == 2
    assert inspection.canonical_isomeric_smiles.count(".") == 1
    assert inspection.formal_charge == 0


def test_report_records_versioned_feature_contract_without_labels_or_models() -> None:
    config = RepresentationConfig(morgan_radius=2, morgan_bits=2048, include_chirality=True)
    report = build_report(
        (MoleculeInput("ethanol", "CCO", "small neutral molecule"),),
        config=config,
    )
    encoded = json.loads(render_report(report))

    assert encoded["contract"]["morgan_radius"] == 2
    assert encoded["contract"]["morgan_bits"] == 2048
    assert encoded["contract"]["include_chirality"] is True
    assert encoded["contract"]["rdkit_version"]
    assert encoded["scope"] == "label-free representation inspection"
    assert encoded["molecules"][0]["morgan_on_bits"] > 0
    assert encoded["molecules"][0]["morgan_on_bits"] <= 2048
    assert "target" not in render_report(report).lower()
    assert "model" not in render_report(report).lower()


@pytest.mark.parametrize("smiles", ["", "not-a-smiles", "[Na+]."])
def test_invalid_or_zero_atom_input_fails_closed(smiles: str) -> None:
    with pytest.raises(RepresentationInputError):
        inspect_molecules((MoleculeInput("bad", smiles, "invalid"),))


def test_duplicate_source_ids_fail_closed() -> None:
    with pytest.raises(RepresentationInputError, match="duplicate source ID"):
        inspect_molecules(
            (
                MoleculeInput("same", "CCO", "first"),
                MoleculeInput("same", "CCN", "second"),
            )
        )
