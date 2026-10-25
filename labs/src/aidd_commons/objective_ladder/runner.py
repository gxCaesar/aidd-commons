"""Reading the ladder from the records the download step cached.

The summary and the inspector both need the same reading, so it is computed
once here. Nothing in this module writes a file.
"""

from __future__ import annotations

from pathlib import Path

from aidd_commons.objective_ladder.analysis import (
    TargetEvidence,
    TargetLadder,
    audit_recovery,
    audit_structure,
    build_ladder,
)
from aidd_commons.objective_ladder.data import (
    find_structures,
    read_affinity_records,
    read_alphafold,
    read_coordinates,
    read_entry_accessions,
    read_structure,
    read_uniprot,
)
from aidd_commons.objective_ladder.protocol import Protocol


def read_ladders(protocol: Protocol, cache_dir: Path) -> list[TargetLadder]:
    """Read every examined entity and state what its six objectives can point at.

    A structure that the search service returns is treated as a structure of
    the target only when the entry itself lists the target's accession, so a
    candidate that the search matched for another reason cannot supply the
    binding record.
    """
    affinity = read_affinity_records(cache_dir)
    ladders: list[TargetLadder] = []
    for target in protocol.targets:
        uniprot = read_uniprot(target.accession, cache_dir)
        alphafold = read_alphafold(target.accession, cache_dir)
        structure = read_structure(target.structure_id, cache_dir)
        coordinates = read_coordinates(target.structure_id, cache_dir)
        recovery = audit_recovery(
            target.structure_id, coordinates, target.accession, uniprot.sequence
        )
        geometry = audit_structure(
            target.structure_id,
            coordinates,
            protocol.tolerances,
            recovery.entity_id,
        )
        codes = tuple(find_structures(target.accession, cache_dir))
        candidates = [row for row in affinity if row.structure_code in codes]
        verified = frozenset(
            code
            for code in sorted({row.structure_code for row in candidates})
            if target.accession in read_entry_accessions(code, cache_dir)
        )
        rows = tuple(row for row in candidates if row.structure_code in verified)
        evidence = TargetEvidence(
            target=target,
            uniprot=uniprot,
            alphafold=alphafold,
            structure=structure,
            geometry=geometry,
            recovery=recovery,
            affinity=rows,
            structure_codes=codes,
            verified_codes=verified,
        )
        ladders.append(build_ladder(evidence, protocol))
    return ladders
