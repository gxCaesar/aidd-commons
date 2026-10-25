from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import floor
from typing import Literal

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from aidd_commons.chembl_egfr.data import ParentActivityRecord

SplitName = Literal["train", "validation", "test"]
SPLIT_ORDER: tuple[SplitName, ...] = ("train", "validation", "test")


class SplitContractError(ValueError):
    """Raised when scaffold membership violates the frozen split protocol."""


@dataclass(frozen=True)
class SplitTargets:
    train: int
    validation: int
    test: int


@dataclass(frozen=True)
class ScaffoldSplitMembership:
    targets: SplitTargets
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    grouping_keys: Mapping[str, str]

    def ids(self, split: SplitName) -> tuple[str, ...]:
        if split == "train":
            return self.train_ids
        if split == "validation":
            return self.validation_ids
        return self.test_ids


def split_targets(record_count: int) -> SplitTargets:
    if record_count < 0:
        raise SplitContractError("record count must be non-negative")
    train = floor(0.70 * record_count + 0.5)
    validation = floor(0.15 * record_count + 0.5)
    return SplitTargets(
        train=train,
        validation=validation,
        test=record_count - train - validation,
    )


def scaffold_group_key(canonical_smiles: str) -> str:
    molecule = Chem.MolFromSmiles(canonical_smiles)
    if molecule is None or molecule.GetNumAtoms() == 0:
        raise SplitContractError(f"invalid molecule for scaffold split: {canonical_smiles}")
    normalized = Chem.MolToSmiles(molecule, isomericSmiles=True)
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(  # type: ignore[no-untyped-call]
        mol=molecule,
        includeChirality=True,
    )
    return scaffold or f"acyclic:{normalized}"


def scaffold_split(
    records: Sequence[ParentActivityRecord],
) -> ScaffoldSplitMembership:
    grouping = {
        record.parent_molecule_chembl_id: scaffold_group_key(record.canonical_smiles)
        for record in records
    }
    if len(grouping) != len(records):
        raise SplitContractError("duplicate parent molecule ID before scaffold split")
    membership = greedy_group_split(grouping)
    expected_ids = {record.parent_molecule_chembl_id for record in records}
    observed_ids = set(membership.train_ids + membership.validation_ids + membership.test_ids)
    if observed_ids != expected_ids:
        raise SplitContractError("scaffold split does not cover the parent molecule set")
    return membership


def greedy_group_split(grouping_by_id: Mapping[str, str]) -> ScaffoldSplitMembership:
    grouped_ids: dict[str, list[str]] = defaultdict(list)
    for parent_id, group_key in grouping_by_id.items():
        if not parent_id or not group_key:
            raise SplitContractError("parent IDs and scaffold keys must be non-empty")
        grouped_ids[group_key].append(parent_id)
    ordered_groups = sorted(
        ((key, tuple(sorted(ids))) for key, ids in grouped_ids.items()),
        key=lambda item: (-len(item[1]), item[0]),
    )

    targets = split_targets(len(grouping_by_id))
    target_by_split = {
        "train": targets.train,
        "validation": targets.validation,
        "test": targets.test,
    }
    assigned: dict[SplitName, list[str]] = {split: [] for split in SPLIT_ORDER}
    split_index = 0
    for _, group_ids in ordered_groups:
        while (
            split_index < len(SPLIT_ORDER) - 1
            and len(assigned[SPLIT_ORDER[split_index]]) >= target_by_split[SPLIT_ORDER[split_index]]
        ):
            split_index += 1
        assigned[SPLIT_ORDER[split_index]].extend(group_ids)

    membership = ScaffoldSplitMembership(
        targets=targets,
        train_ids=tuple(assigned["train"]),
        validation_ids=tuple(assigned["validation"]),
        test_ids=tuple(assigned["test"]),
        grouping_keys=dict(sorted(grouping_by_id.items())),
    )
    assert_scaffold_isolation(membership)
    all_ids = membership.train_ids + membership.validation_ids + membership.test_ids
    if len(all_ids) != len(set(all_ids)):
        raise SplitContractError("parent molecule overlap across split membership")
    return membership


def assert_scaffold_isolation(membership: ScaffoldSplitMembership) -> None:
    assigned_split_by_group: dict[str, SplitName] = {}
    for split in SPLIT_ORDER:
        for parent_id in membership.ids(split):
            try:
                group_key = membership.grouping_keys[parent_id]
            except KeyError as error:
                raise SplitContractError(
                    f"missing scaffold key for parent molecule {parent_id}"
                ) from error
            previous = assigned_split_by_group.get(group_key)
            if previous is not None and previous != split:
                raise SplitContractError(f"scaffold group overlaps across splits: {group_key}")
            assigned_split_by_group[group_key] = split
