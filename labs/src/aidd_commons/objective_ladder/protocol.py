"""The frozen contract for the objective-ladder laboratory.

The curriculum's topic in this track asks a reader to separate six objectives
that are routinely conflated. This module is the machine-readable statement of
that separation: which objectives exist, which entities are examined, which
public record is supposed to carry the evidence for each objective, and what the
declared tolerances are.

Nothing here is a result. The file says what would be looked up and where; the
reading is computed by :mod:`aidd_commons.objective_ladder.analysis` from what
the public sources actually return.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

OBJECTIVES: tuple[str, ...] = (
    "sequence-recovery",
    "folding",
    "structural-plausibility",
    "binding",
    "catalysis",
    "function",
)

#: The record that is expected to carry the evidence for each objective.
OBJECTIVE_SOURCES: dict[str, str] = {
    "sequence-recovery": "rcsb-entry",
    "folding": "alphafold-db",
    "structural-plausibility": "deposited-coordinates",
    "binding": "skempi-and-bound-ligand",
    "catalysis": "uniprot-enzyme-annotation",
    "function": "uniprot-function-annotation",
}

#: Why a cell may legitimately be empty. A target that is not an enzyme has no
#: catalysis record, and saying so is the point of the laboratory.
ABSENCE_REASONS: dict[str, str] = {
    "no-affinity-record": "no measured affinity change names any structure of this target",
    "no-affinity-value": (
        "the affinity archive holds rows that name a structure of this target, "
        "and none of them carries an affinity value in this snapshot"
    ),
    "no-bound-ligand": "the declared structure carries no bound small molecule",
    "no-catalysis-annotation": "the accession carries no catalytic-activity annotation",
    "no-function-annotation": "the accession carries no functional annotation",
    "no-model": "the model archive holds no prediction for this accession",
    "no-structure": "the archive holds no deposited structure for this accession",
}


class ContractError(ValueError):
    """The protocol is missing something the laboratory needs."""


@dataclass(frozen=True)
class Source:
    """A public record the laboratory reads, and the terms it is read under."""

    key: str
    name: str
    licence: str
    route: str


@dataclass(frozen=True)
class Target:
    """One examined entity, and the structure the laboratory reads for it."""

    accession: str
    symbol: str
    name: str
    structure_id: str


@dataclass(frozen=True)
class Tolerances:
    """The declared thresholds of the structural audit."""

    clash_distance_angstrom: float
    bond_length_tolerance_angstrom: float
    minimum_coordinate_rows: int


@dataclass(frozen=True)
class Protocol:
    """The frozen contract itself."""

    protocol_id: str
    issued_on: str
    declared_question: str
    sources: tuple[Source, ...]
    targets: tuple[Target, ...]
    tolerances: Tolerances
    objectives: tuple[str, ...] = field(default=OBJECTIVES)

    def source(self, key: str) -> Source:
        for source in self.sources:
            if source.key == key:
                return source
        raise ContractError(f"the protocol declares no source with key {key!r}")

    def target(self, accession: str) -> Target:
        for target in self.targets:
            if target.accession == accession:
                return target
        raise ContractError(f"the protocol declares no target with accession {accession!r}")


def default_protocol_path() -> Path:
    """Where the committed contract lives, relative to the installed package."""
    return Path(__file__).resolve().parents[3] / "objective_ladder" / "protocol.json"


def _require(value: Any, label: str) -> Any:
    if value is None:
        raise ContractError(f"the contract has no {label!r} block")
    return value


def load_protocol(path: Path | None = None) -> Protocol:
    """Read and check the frozen contract."""
    contract_path = path if path is not None else default_protocol_path()
    try:
        text = contract_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ContractError(f"could not read the contract at {contract_path}: {error}") from error

    document = json.loads(text)
    if document.get("schema_version") != "aidd-commons.objective-ladder-protocol.v1":
        raise ContractError("the contract does not carry the expected schema version")
    if document.get("protocol_id") != "objective-ladder-six-objectives-v1":
        raise ContractError("the contract does not carry the expected protocol identifier")

    objectives = tuple(document.get("objectives") or ())
    if objectives != OBJECTIVES:
        raise ContractError(
            "the contract declares a different set of objectives than the laboratory reads"
        )

    sources = tuple(
        Source(
            key=str(item["key"]),
            name=str(item["name"]),
            licence=str(item["licence"]),
            route=str(item["route"]),
        )
        for item in _require(document.get("sources"), "sources")
    )
    if not sources:
        raise ContractError("the contract names no source to read")
    targets = tuple(
        Target(
            accession=str(item["accession"]),
            symbol=str(item["symbol"]),
            name=str(item["name"]),
            structure_id=str(item["structure_id"]),
        )
        for item in _require(document.get("targets"), "targets")
    )
    if not targets:
        raise ContractError("the contract examines no target")

    declared = _require(document.get("tolerances"), "tolerances")
    tolerances = Tolerances(
        clash_distance_angstrom=float(
            _require(declared.get("clash_distance_angstrom"), "clash distance")
        ),
        bond_length_tolerance_angstrom=float(
            _require(declared.get("bond_length_tolerance_angstrom"), "bond length tolerance")
        ),
        minimum_coordinate_rows=int(
            _require(declared.get("minimum_coordinate_rows"), "minimum coordinate rows")
        ),
    )

    return Protocol(
        protocol_id=str(document["protocol_id"]),
        issued_on=str(document["issued_on"]),
        declared_question=str(_require(document.get("declared_question"), "declared question")),
        sources=sources,
        targets=targets,
        tolerances=tolerances,
        objectives=objectives,
    )
