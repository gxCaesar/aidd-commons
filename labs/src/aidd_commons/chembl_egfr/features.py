from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors, rdFingerprintGenerator

from aidd_commons.chembl_egfr.data import ParentActivityRecord
from aidd_commons.chembl_egfr.protocol import (
    MORGAN_BITS,
    MORGAN_COUNT_SIMULATION,
    MORGAN_INCLUDE_CHIRALITY,
    MORGAN_INCLUDE_RING_MEMBERSHIP,
    MORGAN_RADIUS,
    MORGAN_USE_BOND_TYPES,
    descriptor_names,
)


class FeatureContractError(ValueError):
    """Raised when molecular features depart from the frozen representation."""


@dataclass(frozen=True)
class FeatureMatrix:
    names: tuple[str, ...]
    values: np.ndarray


def build_descriptor_matrix(
    records: Sequence[ParentActivityRecord],
) -> FeatureMatrix:
    names = descriptor_names()
    rows: list[list[float]] = []
    for record in records:
        molecule = _parse_record(record)
        calculated = Descriptors.CalcMolDescriptors(  # type: ignore[no-untyped-call]
            molecule,
            missingVal=float("nan"),
            silent=True,
        )
        try:
            rows.append([float(calculated[name]) for name in names])
        except (KeyError, TypeError, ValueError) as error:
            raise FeatureContractError(
                f"could not calculate the frozen descriptor registry for "
                f"{record.parent_molecule_chembl_id}"
            ) from error
    values = np.asarray(rows, dtype=float) if rows else np.empty((0, len(names)), dtype=float)
    return FeatureMatrix(names=names, values=values)


def build_morgan_matrix(records: Sequence[ParentActivityRecord]) -> FeatureMatrix:
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=MORGAN_RADIUS,
        countSimulation=MORGAN_COUNT_SIMULATION,
        includeChirality=MORGAN_INCLUDE_CHIRALITY,
        useBondTypes=MORGAN_USE_BOND_TYPES,
        includeRingMembership=MORGAN_INCLUDE_RING_MEMBERSHIP,
        fpSize=MORGAN_BITS,
    )
    matrix = np.zeros((len(records), MORGAN_BITS), dtype=np.uint8)
    for index, record in enumerate(records):
        molecule = _parse_record(record)
        fingerprint = generator.GetFingerprint(molecule)
        DataStructs.ConvertToNumpyArray(fingerprint, matrix[index])
    return FeatureMatrix(
        names=tuple(f"morgan_bit_{index}" for index in range(MORGAN_BITS)),
        values=matrix,
    )


def _parse_record(record: ParentActivityRecord) -> Chem.Mol:
    molecule = Chem.MolFromSmiles(record.canonical_smiles)
    if molecule is None or molecule.GetNumAtoms() == 0:
        raise FeatureContractError(
            f"invalid canonical molecule for {record.parent_molecule_chembl_id}"
        )
    return molecule
