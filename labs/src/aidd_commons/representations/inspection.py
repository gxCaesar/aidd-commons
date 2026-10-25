from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors, rdFingerprintGenerator, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold


class RepresentationInputError(ValueError):
    """Raised when a label-free representation input violates the lab contract."""


@dataclass(frozen=True)
class MoleculeInput:
    source_id: str
    smiles: str
    teaching_point: str


@dataclass(frozen=True)
class RepresentationConfig:
    morgan_radius: int = 2
    morgan_bits: int = 2048
    include_chirality: bool = True

    def __post_init__(self) -> None:
        if self.morgan_radius < 0:
            raise RepresentationInputError("Morgan radius must be non-negative")
        if self.morgan_bits <= 0:
            raise RepresentationInputError("Morgan bit-vector size must be positive")


@dataclass(frozen=True)
class DescriptorSnapshot:
    molecular_weight: float
    wildman_crippen_logp: float
    topological_polar_surface_area: float
    hydrogen_bond_donors: int
    hydrogen_bond_acceptors: int
    rotatable_bonds: int


@dataclass(frozen=True)
class MoleculeInspection:
    source_id: str
    input_smiles: str
    teaching_point: str
    canonical_isomeric_smiles: str
    canonical_nonisomeric_smiles: str
    inchi_key: str
    molecular_formula: str
    atom_count: int
    heavy_atom_count: int
    bond_count: int
    component_count: int
    formal_charge: int
    specified_stereocenters: int
    unassigned_stereocenters: int
    murcko_scaffold_smiles: str | None
    descriptors: DescriptorSnapshot
    morgan_on_bits: int
    morgan_nonzero_count_features: int


@dataclass(frozen=True)
class RepresentationContract:
    rdkit_version: str
    canonical_smiles_toolkit: str
    descriptor_names: tuple[str, ...]
    morgan_radius: int
    morgan_bits: int
    include_chirality: bool
    fingerprint_forms: tuple[str, ...]


@dataclass(frozen=True)
class RepresentationReport:
    scope: str
    contract: RepresentationContract
    molecules: tuple[MoleculeInspection, ...]


def inspect_molecules(
    inputs: Sequence[MoleculeInput],
    *,
    config: RepresentationConfig | None = None,
) -> tuple[MoleculeInspection, ...]:
    """Inspect molecular encodings without loading labels or fitting a model."""

    resolved_config = config or RepresentationConfig()
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=resolved_config.morgan_radius,
        fpSize=resolved_config.morgan_bits,
        includeChirality=resolved_config.include_chirality,
    )
    seen_ids: set[str] = set()
    inspections: list[MoleculeInspection] = []

    for record in inputs:
        if not record.source_id.strip():
            raise RepresentationInputError("source ID must not be empty")
        if record.source_id in seen_ids:
            raise RepresentationInputError(f"duplicate source ID: {record.source_id}")
        seen_ids.add(record.source_id)

        molecule = Chem.MolFromSmiles(record.smiles) if record.smiles.strip() else None
        if molecule is None or molecule.GetNumAtoms() == 0:
            raise RepresentationInputError(
                f"invalid or zero-atom SMILES for source ID {record.source_id}"
            )

        stereocenters = Chem.FindMolChiralCenters(  # type: ignore[no-untyped-call]
            molecule,
            force=True,
            includeUnassigned=True,
            includeCIP=True,
            useLegacyImplementation=False,
        )
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(  # type: ignore[no-untyped-call]
            mol=molecule
        )
        bit_fingerprint = generator.GetFingerprint(molecule)
        count_fingerprint = generator.GetCountFingerprint(molecule)
        inspections.append(
            MoleculeInspection(
                source_id=record.source_id,
                input_smiles=record.smiles,
                teaching_point=record.teaching_point,
                canonical_isomeric_smiles=Chem.MolToSmiles(
                    molecule, isomericSmiles=True
                ),
                canonical_nonisomeric_smiles=Chem.MolToSmiles(
                    molecule, isomericSmiles=False
                ),
                inchi_key=Chem.MolToInchiKey(molecule),  # type: ignore[no-untyped-call]
                molecular_formula=rdMolDescriptors.CalcMolFormula(molecule),
                atom_count=molecule.GetNumAtoms(),
                heavy_atom_count=molecule.GetNumHeavyAtoms(),
                bond_count=molecule.GetNumBonds(),
                component_count=len(Chem.GetMolFrags(molecule)),
                formal_charge=sum(
                    atom.GetFormalCharge()
                    for atom in molecule.GetAtoms()  # type: ignore[no-untyped-call]
                ),
                specified_stereocenters=sum(
                    assignment != "?" for _, assignment in stereocenters
                ),
                unassigned_stereocenters=sum(
                    assignment == "?" for _, assignment in stereocenters
                ),
                murcko_scaffold_smiles=scaffold or None,
                descriptors=DescriptorSnapshot(
                    molecular_weight=float(
                        Descriptors.MolWt(molecule)  # type: ignore[attr-defined]
                    ),
                    wildman_crippen_logp=float(
                        Descriptors.MolLogP(molecule)  # type: ignore[attr-defined]
                    ),
                    topological_polar_surface_area=float(
                        rdMolDescriptors.CalcTPSA(molecule)
                    ),
                    hydrogen_bond_donors=int(rdMolDescriptors.CalcNumHBD(molecule)),
                    hydrogen_bond_acceptors=int(rdMolDescriptors.CalcNumHBA(molecule)),
                    rotatable_bonds=int(
                        rdMolDescriptors.CalcNumRotatableBonds(molecule)
                    ),
                ),
                morgan_on_bits=len(bit_fingerprint.GetOnBits()),
                morgan_nonzero_count_features=len(
                    count_fingerprint.GetNonzeroElements()
                ),
            )
        )

    return tuple(inspections)


def build_report(
    inputs: Sequence[MoleculeInput],
    *,
    config: RepresentationConfig | None = None,
) -> RepresentationReport:
    resolved_config = config or RepresentationConfig()
    return RepresentationReport(
        scope="label-free representation inspection",
        contract=RepresentationContract(
            rdkit_version=rdBase.rdkitVersion,
            canonical_smiles_toolkit="RDKit",
            descriptor_names=(
                "molecular_weight",
                "wildman_crippen_logp",
                "topological_polar_surface_area",
                "hydrogen_bond_donors",
                "hydrogen_bond_acceptors",
                "rotatable_bonds",
            ),
            morgan_radius=resolved_config.morgan_radius,
            morgan_bits=resolved_config.morgan_bits,
            include_chirality=resolved_config.include_chirality,
            fingerprint_forms=("hashed_bit_vector", "hashed_count_vector"),
        ),
        molecules=inspect_molecules(inputs, config=resolved_config),
    )


def render_report(report: RepresentationReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"
