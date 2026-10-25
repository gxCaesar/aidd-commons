"""Reading the six objectives apart, and auditing one structure for plausibility.

Three pieces of work live here. The first is a sequence audit computed by
comparing the deposited polymer sequence with the named reference over the
region the archive's own alignment record covers. The second is a structural
audit computed from the deposited coordinates: how many non-bonded atom pairs
sit closer than the declared clash distance, how many bonded pairs sit further
from the sum of their covalent radii than the declared tolerance, and how many
of the audited rows belong to the examined entity. The third takes the records
that the public archives returned and states, for each objective, whether a
record carries evidence at that level, and when it does not, why not.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from aidd_commons.objective_ladder.data import (
    AffinityRecord,
    AlphaFoldRecord,
    StructureRecord,
    UniProtRecord,
)
from aidd_commons.objective_ladder.protocol import (
    ABSENCE_REASONS,
    ContractError,
    Protocol,
    Target,
    Tolerances,
)

#: The parser and the geometry constants live in the structural laboratory that
#: already ships them, so this laboratory reuses them rather than writing a
#: second reader for the same file format.
_CIF_MODULE_PATH = Path(__file__).resolve().parents[4] / "labs" / "egfr_structures" / "cif.py"

#: How much of an annotation the record quotes before it stops.
_FUNCTION_QUOTE_LIMIT = 220


def _load_cif_module() -> Any:
    """Import the repository's own mmCIF reader by path."""
    if not _CIF_MODULE_PATH.exists():
        raise ContractError(
            f"the structural reader is not present at {_CIF_MODULE_PATH}, "
            "so the coordinates cannot be read"
        )
    specification = importlib.util.spec_from_file_location(
        "aidd_commons_structures_cif", _CIF_MODULE_PATH
    )
    if specification is None or specification.loader is None:
        raise ContractError("the structural reader could not be loaded")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class RecoveryAudit:
    """How much of the deposited sequence matches the named reference.

    The evaluated region is the region the archive's own alignment record
    covers, and the reference is the accession the alignment names. Positions
    outside that region are not scored and do not enter the fraction.
    """

    entry_id: str
    reference_accession: str
    entity_id: str
    strands: tuple[str, ...]
    evaluated_positions: int
    matched_positions: int
    entity_positions: int
    reference_begin: int
    reference_end: int
    regions: tuple[str, ...]
    mismatches: tuple[str, ...]
    audited: bool
    note: str = ""

    @property
    def fraction(self) -> float | None:
        """The fraction of evaluated positions that match the reference."""
        if not self.evaluated_positions:
            return None
        return self.matched_positions / self.evaluated_positions


def _entity_sequences(categories: dict[str, Any]) -> dict[str, str]:
    """The canonical one-letter sequence of every polymer entity."""
    sequences: dict[str, str] = {}
    for row in categories.get("_entity_poly") or []:
        raw = str(row.get("pdbx_seq_one_letter_code_can") or "")
        sequences[str(row.get("entity_id"))] = "".join(raw.split())
    return sequences


def _entity_strands(categories: dict[str, Any]) -> dict[str, list[str]]:
    """The chains every polymer entity occupies."""
    strands: dict[str, list[str]] = {}
    for row in categories.get("_entity_poly") or []:
        raw = str(row.get("pdbx_strand_id") or "")
        strands[str(row.get("entity_id"))] = [part for part in raw.split(",") if part]
    return strands


def audit_recovery(
    entry_id: str,
    coordinates: str,
    reference_accession: str,
    reference_sequence: str,
) -> RecoveryAudit:
    """Compare the deposited sequence with the named reference.

    The comparison is made position by position over the region the archive's
    alignment record covers, so the fraction is a measurement of the deposited
    record and not a restatement of what the depositor asserted.
    """
    module = _load_cif_module()
    try:
        categories = module.parse(coordinates)
    except Exception as error:  # the reader raises several shapes of error
        return RecoveryAudit(
            entry_id=entry_id,
            reference_accession=reference_accession,
            entity_id="",
            strands=(),
            evaluated_positions=0,
            matched_positions=0,
            entity_positions=0,
            reference_begin=0,
            reference_end=0,
            regions=(),
            mismatches=(),
            audited=False,
            note=f"the coordinates could not be read: {error}",
        )

    references = {
        str(row.get("entity_id")): str(row.get("pdbx_db_accession") or "")
        for row in (categories.get("_struct_ref") or [])
    }
    target_entities = [
        entity for entity, accession in references.items() if accession == reference_accession
    ]
    if not target_entities:
        return RecoveryAudit(
            entry_id=entry_id,
            reference_accession=reference_accession,
            entity_id="",
            strands=(),
            evaluated_positions=0,
            matched_positions=0,
            entity_positions=0,
            reference_begin=0,
            reference_end=0,
            regions=(),
            mismatches=(),
            audited=False,
            note=(
                f"the entry holds no polymer entity that references {reference_accession}, "
                "so no deposited position can be compared with the reference"
            ),
        )

    sequences = _entity_sequences(categories)
    strands_by_entity = _entity_strands(categories)
    entity_id = target_entities[0]
    entity_strands = strands_by_entity.get(entity_id, [])

    evaluated = 0
    matched = 0
    entity_positions = 0
    reference_begin = 0
    reference_end = 0
    regions: list[str] = []
    mismatches: list[str] = []

    for row in categories.get("_struct_ref_seq") or []:
        strand = str(row.get("pdbx_strand_id") or "")
        if strand not in entity_strands:
            continue
        if str(row.get("pdbx_db_accession") or "") != reference_accession:
            continue
        try:
            begin = int(row["seq_align_beg"])
            end = int(row["seq_align_end"])
            database_begin = int(row["db_align_beg"])
            database_end = int(row["db_align_end"])
        except (KeyError, TypeError, ValueError):
            continue
        deposited = sequences.get(entity_id, "")[begin - 1 : end]
        expected = reference_sequence[database_begin - 1 : database_end]
        regions.append(
            f"chain {strand}, entity {begin}-{end}, reference {reference_accession} "
            f"{database_begin}-{database_end}"
        )
        if len(deposited) != len(expected):
            mismatches.append(
                f"chain {strand}: the deposited region holds {len(deposited)} positions and the "
                f"reference region holds {len(expected)}"
            )
            continue
        entity_positions = max(entity_positions, end - begin + 1)
        reference_begin = database_begin
        reference_end = database_end
        for offset, (left, right) in enumerate(zip(deposited, expected, strict=True)):
            evaluated += 1
            if left == right:
                matched += 1
            else:
                mismatches.append(
                    f"chain {strand} position {begin + offset}: deposited {left}, reference {right}"
                )

    if not regions:
        return RecoveryAudit(
            entry_id=entry_id,
            reference_accession=reference_accession,
            entity_id=entity_id,
            strands=tuple(entity_strands),
            evaluated_positions=0,
            matched_positions=0,
            entity_positions=0,
            reference_begin=0,
            reference_end=0,
            regions=(),
            mismatches=(),
            audited=False,
            note=(
                f"the entry holds no alignment record between its {reference_accession} entity "
                "and the reference, so no position is evaluated"
            ),
        )

    return RecoveryAudit(
        entry_id=entry_id,
        reference_accession=reference_accession,
        entity_id=entity_id,
        strands=tuple(entity_strands),
        evaluated_positions=evaluated,
        matched_positions=matched,
        entity_positions=entity_positions,
        reference_begin=reference_begin,
        reference_end=reference_end,
        regions=tuple(regions),
        mismatches=tuple(mismatches),
        audited=True,
        note="",
    )


@dataclass(frozen=True)
class GeometryAudit:
    """What the deposited coordinates say about their own plausibility."""

    entry_id: str
    atom_rows: int
    entity_rows: dict[str, int]
    entity_names: dict[str, str]
    bond_length_outliers: int
    clashes: int
    shortest_non_bonded_distance: float | None
    shortest_clash_entity: str
    shortest_clash_partner_entity: str
    audited: bool
    note: str = ""


def audit_structure(
    entry_id: str,
    coordinates: str,
    tolerances: Tolerances,
    target_entity_id: str = "",
) -> GeometryAudit:
    """Audit one deposited structure's coordinates."""
    module = _load_cif_module()
    try:
        categories = module.parse(coordinates)
    except Exception as error:  # the reader raises several shapes of error
        return GeometryAudit(
            entry_id=entry_id,
            atom_rows=0,
            entity_rows={},
            entity_names={},
            bond_length_outliers=0,
            clashes=0,
            shortest_non_bonded_distance=None,
            shortest_clash_entity="",
            shortest_clash_partner_entity="",
            audited=False,
            note=f"the coordinates could not be read: {error}",
        )

    rows = categories.get("_atom_site") or []
    elements: list[str] = []
    points: list[tuple[float, float, float]] = []
    entity_of_row: list[str] = []
    for row in rows:
        if row.get("pdbx_PDB_model_num") not in (None, "1"):
            continue
        if row.get("label_alt_id") not in (None, "A"):
            continue
        try:
            elements.append(str(row["type_symbol"]).upper())
            points.append(
                (
                    float(row["Cartn_x"]),
                    float(row["Cartn_y"]),
                    float(row["Cartn_z"]),
                )
            )
            entity_of_row.append(str(row.get("label_entity_id") or ""))
        except (KeyError, TypeError, ValueError):
            continue

    if len(points) < tolerances.minimum_coordinate_rows:
        return GeometryAudit(
            entry_id=entry_id,
            atom_rows=len(points),
            entity_rows={},
            entity_names={},
            bond_length_outliers=0,
            clashes=0,
            shortest_non_bonded_distance=None,
            shortest_clash_entity="",
            shortest_clash_partner_entity="",
            audited=False,
            note=(
                f"only {len(points)} coordinate rows were read, below the declared "
                f"minimum of {tolerances.minimum_coordinate_rows}, so nothing was audited"
            ),
        )

    entity_rows: dict[str, int] = {}
    for entity in entity_of_row:
        entity_rows[entity] = entity_rows.get(entity, 0) + 1

    entity_names: dict[str, str] = {}
    for row in categories.get("_entity") or []:
        entity_names[str(row.get("id"))] = str(row.get("pdbx_description") or "")

    radii = module.COVALENT_RADII
    bond_tolerance = module.BOND_TOLERANCE
    array = np.asarray(points, dtype=float)
    tree = cKDTree(array)

    cutoff = max(
        tolerances.clash_distance_angstrom,
        max(radii.values()) * 2 + bond_tolerance,
    )
    neighbours = tree.query_ball_point(array, cutoff)

    outliers = 0
    clashes = 0
    shortest: float | None = None
    shortest_entity = ""
    shortest_partner = ""
    for index, group in enumerate(neighbours):
        left_element = elements[index]
        left_radius = radii.get(left_element)
        for other in group:
            if other <= index:
                continue
            distance = float(np.linalg.norm(array[index] - array[other]))
            right_radius = radii.get(elements[other])
            if left_radius is None or right_radius is None:
                continue
            reference = left_radius + right_radius
            if distance <= reference + bond_tolerance:
                # a bonded pair: it is implausible when it sits away from the
                # reference length by more than the declared tolerance
                if abs(distance - reference) > tolerances.bond_length_tolerance_angstrom:
                    outliers += 1
                continue
            if distance < tolerances.clash_distance_angstrom:
                clashes += 1
                if shortest is None or distance < shortest:
                    shortest = distance
                    shortest_entity = entity_of_row[index]
                    shortest_partner = entity_of_row[other]

    return GeometryAudit(
        entry_id=entry_id,
        atom_rows=len(points),
        entity_rows=entity_rows,
        entity_names=entity_names,
        bond_length_outliers=outliers,
        clashes=clashes,
        shortest_non_bonded_distance=shortest,
        shortest_clash_entity=shortest_entity,
        shortest_clash_partner_entity=shortest_partner,
        audited=True,
        note="",
    )


@dataclass(frozen=True)
class ObjectiveOutcome:
    """What one objective resolved to, for one target."""

    objective: str
    found: bool
    record: str
    detail: str
    absence_reason: str = ""


@dataclass
class TargetLadder:
    """The six outcomes for one target."""

    accession: str
    symbol: str
    name: str
    structure_id: str
    outcomes: dict[str, ObjectiveOutcome] = field(default_factory=dict)

    @property
    def evidenced(self) -> int:
        return sum(1 for outcome in self.outcomes.values() if outcome.found)

    @property
    def empty(self) -> int:
        return sum(1 for outcome in self.outcomes.values() if not outcome.found)


@dataclass(frozen=True)
class TargetEvidence:
    """Everything the laboratory read for one target."""

    target: Target
    uniprot: UniProtRecord
    alphafold: AlphaFoldRecord | None
    structure: StructureRecord
    geometry: GeometryAudit
    recovery: RecoveryAudit
    affinity: tuple[AffinityRecord, ...]
    structure_codes: tuple[str, ...]
    verified_codes: frozenset[str]


def _outcome(
    objective: str, found: bool, record: str, detail: str, reason: str = ""
) -> ObjectiveOutcome:
    return ObjectiveOutcome(
        objective=objective,
        found=found,
        record=record,
        detail=detail,
        absence_reason=""
        if found
        else (reason or ABSENCE_REASONS.get(objective, "no record was found")),
    )


def _quote(text: str, limit: int = _FUNCTION_QUOTE_LIMIT) -> str:
    """The leading sentences of an annotation, cut at a word boundary."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    sentences: list[str] = []
    remaining = limit
    position = 0
    while position < len(collapsed) and remaining > 0:
        boundary = collapsed.find(". ", position)
        if boundary == -1 or boundary + 1 > limit:
            break
        sentences.append(collapsed[position : boundary + 1])
        position = boundary + 2
        remaining = limit - position
    if sentences:
        return " ".join(sentences)
    cut = collapsed[:limit]
    space = cut.rfind(" ")
    return f"{cut[: space if space > 0 else limit]}..."


def _chain_phrase(strands: tuple[str, ...]) -> str:
    if not strands:
        return "no chain"
    if len(strands) == 1:
        return f"chain {strands[0]}"
    return f"chains {', '.join(strands)}"


def _affinity_phrase(record: AffinityRecord) -> str:
    """What the row says about the two sides of the comparison."""
    if record.affinity_wild_type is not None and record.affinity_mutant is not None:
        return f"wild type {record.affinity_wild_type:g} M, mutant {record.affinity_mutant:g} M"
    if record.affinity_wild_type is not None:
        mutant = record.mutant_text or "not stated"
        return f"wild type {record.affinity_wild_type:g} M, mutant {mutant}"
    if record.affinity_mutant is not None:
        wild_type = record.wild_type_text or "not stated"
        return f"wild type {wild_type}, mutant {record.affinity_mutant:g} M"
    return "the row carries no affinity value"


def build_ladder(evidence: TargetEvidence, protocol: Protocol) -> TargetLadder:
    """State, for one target, what each of the six objectives can point at."""
    target = evidence.target
    uniprot = evidence.uniprot
    structure = evidence.structure
    ladder = TargetLadder(
        accession=target.accession,
        symbol=target.symbol,
        name=target.name,
        structure_id=target.structure_id,
    )

    # 1. sequence recovery: the deposited sequence against the named reference,
    #    over the region the archive's alignment record covers
    recovery = evidence.recovery
    if recovery.audited and recovery.evaluated_positions:
        fraction = recovery.fraction or 0.0
        ladder.outcomes["sequence-recovery"] = _outcome(
            "sequence-recovery",
            found=True,
            record=(
                f"{recovery.entry_id} against {recovery.reference_accession}, "
                f"{recovery.matched_positions} of {recovery.evaluated_positions} evaluated "
                f"positions match ({fraction:.4f})"
            ),
            detail=(
                "the fraction is counted position by position over the region the archive's "
                "alignment record covers, and the positions outside that region are not "
                "scored; "
                + "; ".join(recovery.regions)
                + (
                    "; the positions that differ are " + "; ".join(recovery.mismatches)
                    if recovery.mismatches
                    else ""
                )
            ),
        )
    else:
        ladder.outcomes["sequence-recovery"] = _outcome(
            "sequence-recovery",
            found=False,
            record="",
            detail=recovery.note or "the deposited sequence could not be compared",
            reason="no-structure",
        )

    # 2. folding: the deposited structure is the conformation record, and the
    #    model archive holds a prediction, which is not an observation
    model_phrase = "the model archive holds no prediction for this accession"
    if evidence.alphafold is not None:
        metric = (
            f"{evidence.alphafold.global_metric:.2f}"
            if evidence.alphafold.global_metric is not None
            else "not stated"
        )
        model_phrase = (
            f"the model archive holds {evidence.alphafold.entry_id}, dated "
            f"{evidence.alphafold.model_created}, with a global metric of {metric}, "
            "which is a prediction and not an observation"
        )
    if structure.method:
        coverage = ""
        if recovery.audited and recovery.entity_positions:
            coverage = (
                f", covering {recovery.entity_positions} residues of {target.accession} "
                f"({recovery.reference_begin}-{recovery.reference_end}) in "
                f"{_chain_phrase(recovery.strands)}"
            )
        ladder.outcomes["folding"] = _outcome(
            "folding",
            found=True,
            record=(f"{structure.entry_id}, {structure.method}{coverage}; {model_phrase}"),
            detail=(
                "the deposited structure is an experimental observation of a conformation in "
                "the state the experiment produced, and it is limited to that state; a "
                "prediction is not an observation of folding, and neither record supplies a "
                "binding or functional measurement"
            ),
        )
    else:
        ladder.outcomes["folding"] = _outcome(
            "folding",
            found=False,
            record="",
            detail=(
                "the archive states no experimental method for the declared structure, and "
                + model_phrase
            ),
            reason="no-structure",
        )

    # 3. structural plausibility: computed from the deposited coordinates
    geometry = evidence.geometry
    if geometry.audited:
        target_rows = geometry.entity_rows.get(recovery.entity_id, 0)
        composition = (
            f", of which {target_rows} belong to the examined entity" if target_rows else ""
        )
        closest = ""
        if geometry.shortest_non_bonded_distance is not None:
            name = geometry.entity_names.get(geometry.shortest_clash_entity, "")
            partner = geometry.entity_names.get(geometry.shortest_clash_partner_entity, "")
            if geometry.shortest_clash_partner_entity == geometry.shortest_clash_entity:
                where = f"both atoms in {name or 'the same entity'}"
            else:
                where = f"one atom in {name or 'the entry'} and one in {partner or 'the entry'}"
            closest = (
                f", the closest non-bonded pair at "
                f"{geometry.shortest_non_bonded_distance:.2f} angstrom, {where}"
            )
        ladder.outcomes["structural-plausibility"] = _outcome(
            "structural-plausibility",
            found=True,
            record=(
                f"{geometry.entry_id}, {geometry.atom_rows} coordinate rows audited"
                f"{composition}, {geometry.bond_length_outliers} bond-length outliers and "
                f"{geometry.clashes} clashes{closest}"
            ),
            detail=(
                "the plausibility figures are computed here from the deposited coordinates, "
                "not quoted from a score the archive reports, and they describe the internal "
                "consistency of the coordinate file rather than the fold it depicts"
            ),
        )
    else:
        ladder.outcomes["structural-plausibility"] = _outcome(
            "structural-plausibility",
            found=False,
            record="",
            detail=geometry.note or "the coordinates could not be audited",
            reason="no-structure",
        )

    # 4. binding: a measured value is the evidence. A bound component is not,
    #    because crystallisation additives and ions appear in most deposited
    #    entries, so a component says something about the experiment and not
    #    about the interaction.
    rows = [
        record for record in evidence.affinity if record.structure_code in evidence.verified_codes
    ]
    with_value = [record for record in rows if record.carries_a_value]
    if with_value:
        chosen = next((record for record in with_value if record.carries_a_change), with_value[0])
        if chosen.carries_a_change:
            kind = (
                "the row carries both sides of a measured change, with its unit and the "
                "method that produced it"
            )
        else:
            kind = (
                "the row carries one side of the comparison, so it is a measured value and "
                "not a measured change"
            )
        ladder.outcomes["binding"] = _outcome(
            "binding",
            found=True,
            record=(
                f"{chosen.structure_code}, mutation {chosen.mutation}, "
                f"{_affinity_phrase(chosen)}"
                + (f", method {chosen.method}" if chosen.method else "")
            ),
            detail=(
                f"the row names a deposited structure of {target.accession} that the archive "
                f"itself lists as referencing it; {kind}"
            ),
        )
    elif rows:
        ladder.outcomes["binding"] = _outcome(
            "binding",
            found=False,
            record="",
            detail=(
                f"{len(rows)} rows of the affinity archive name a structure of this target, "
                "and none of them carries an affinity value in this snapshot"
            ),
            reason="no-affinity-value",
        )
    elif structure.ligand_ids:
        components = ", ".join(structure.ligand_ids)
        ladder.outcomes["binding"] = _outcome(
            "binding",
            found=False,
            record="",
            detail=(
                f"the declared structure carries {components}, but a bound component is not a "
                "measured binding value, because crystallisation additives and ions appear "
                "in most deposited entries, and no measured change names any structure of "
                "this target"
            ),
            reason="no-affinity-record",
        )
    else:
        ladder.outcomes["binding"] = _outcome(
            "binding",
            found=False,
            record="",
            detail=(
                "no measured affinity change names any structure of this target and the "
                "declared structure carries no bound component"
            ),
            reason="no-affinity-record",
        )

    # 5. catalysis: the enzyme annotation
    if uniprot.catalysis or uniprot.ec_numbers:
        catalogue = ", ".join(uniprot.ec_numbers) or "no enzyme catalogue number"
        reaction = uniprot.catalysis[0] if uniprot.catalysis else "no reaction is named"
        count = len(uniprot.catalysis)
        ladder.outcomes["catalysis"] = _outcome(
            "catalysis",
            found=True,
            record=(
                f"{target.accession}, {count} catalytic-activity annotation"
                f"{'s' if count != 1 else ''}, catalogue {catalogue}, reaction {reaction}"
            ),
            detail=(
                "the accession carries a catalytic-activity annotation with a named reaction, "
                "which is a statement about the transformation and not a measured rate"
            ),
        )
    else:
        ladder.outcomes["catalysis"] = _outcome(
            "catalysis",
            found=False,
            record="",
            detail=(
                "the accession carries no catalytic-activity annotation and no enzyme "
                "catalogue number"
            ),
            reason="no-catalysis-annotation",
        )

    # 6. function: the functional annotation
    if uniprot.function_text:
        ladder.outcomes["function"] = _outcome(
            "function",
            found=True,
            record=f"{target.accession}, {_quote(uniprot.function_text)}",
            detail=(
                "the accession carries a functional annotation, which is a statement about "
                "what the entity does and not a measurement of any of the other objectives"
            ),
        )
    else:
        ladder.outcomes["function"] = _outcome(
            "function",
            found=False,
            record="",
            detail="the accession carries no functional annotation",
            reason="no-function-annotation",
        )

    # The ladder fills the objectives the contract declares, so a contract that
    # declares a different set cannot be read by this laboratory.
    if set(ladder.outcomes) != set(protocol.objectives):
        raise ContractError(
            f"the ladder for {target.accession} covers {sorted(ladder.outcomes)}, "
            f"which is not the set the contract declares"
        )
    return ladder
