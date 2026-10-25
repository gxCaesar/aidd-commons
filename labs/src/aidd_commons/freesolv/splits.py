from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import floor
from random import Random
from typing import Literal

import numpy as np
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from aidd_commons.freesolv.data import MoleculeRecord

GLOBAL_SEED = 20_260_904
SplitName = Literal["train", "validation", "test"]
SPLIT_ORDER: tuple[SplitName, ...] = ("train", "validation", "test")


class SplitContractError(ValueError):
    """Raised when frozen split membership invariants do not hold."""


@dataclass(frozen=True)
class SplitTargets:
    train: int
    validation: int
    test: int


@dataclass(frozen=True)
class SplitMembership:
    split_kind: Literal["random", "scaffold"]
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
    train = floor(0.8 * record_count + 0.5)
    validation = floor(0.1 * record_count + 0.5)
    return SplitTargets(train=train, validation=validation, test=record_count - train - validation)


def random_split(records: Sequence[MoleculeRecord], seed: int = GLOBAL_SEED) -> SplitMembership:
    targets = split_targets(len(records))
    order = np.random.default_rng(seed).permutation(len(records))
    ids = tuple(records[int(index)].canonical_smiles for index in order)
    train_end = targets.train
    validation_end = train_end + targets.validation
    grouping_keys = {
        record.canonical_smiles: scaffold_group_key(record.canonical_smiles) for record in records
    }
    membership = SplitMembership(
        split_kind="random",
        targets=targets,
        train_ids=ids[:train_end],
        validation_ids=ids[train_end:validation_end],
        test_ids=ids[validation_end:],
        grouping_keys=grouping_keys,
    )
    assert_no_canonical_overlap(membership)
    _assert_complete_membership(records, membership)
    return membership


def scaffold_split(records: Sequence[MoleculeRecord], seed: int = GLOBAL_SEED) -> SplitMembership:
    targets = split_targets(len(records))
    grouped_ids: dict[str, list[str]] = defaultdict(list)
    grouping_keys: dict[str, str] = {}
    for record in records:
        key = scaffold_group_key(record.canonical_smiles)
        grouped_ids[key].append(record.canonical_smiles)
        grouping_keys[record.canonical_smiles] = key

    seeded_tie_breaker = Random(seed)
    ordered_groups: list[tuple[str, list[str]]] = []
    for group_size in sorted({len(ids) for ids in grouped_ids.values()}, reverse=True):
        equal_size_keys = sorted(key for key, ids in grouped_ids.items() if len(ids) == group_size)
        seeded_tie_breaker.shuffle(equal_size_keys)
        ordered_groups.extend((key, grouped_ids[key]) for key in equal_size_keys)

    assigned: dict[SplitName, list[str]] = {split: [] for split in SPLIT_ORDER}
    target_by_split = {
        "train": targets.train,
        "validation": targets.validation,
        "test": targets.test,
    }
    for _, group_ids in ordered_groups:
        for split in SPLIT_ORDER:
            if len(assigned[split]) < target_by_split[split]:
                assigned[split].extend(group_ids)
                break
        else:
            raise SplitContractError("scaffold allocation exhausted every frozen target")

    membership = SplitMembership(
        split_kind="scaffold",
        targets=targets,
        train_ids=tuple(assigned["train"]),
        validation_ids=tuple(assigned["validation"]),
        test_ids=tuple(assigned["test"]),
        grouping_keys=grouping_keys,
    )
    assert_no_canonical_overlap(membership)
    _assert_complete_membership(records, membership)
    assert_scaffold_isolation(membership)
    return membership


def scaffold_group_key(canonical_smiles: str) -> str:
    molecule = Chem.MolFromSmiles(canonical_smiles)
    if molecule is None:
        raise SplitContractError(
            f"invalid canonical molecule for scaffold split: {canonical_smiles}"
        )
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=molecule)  # type: ignore[no-untyped-call]
    return scaffold or f"acyclic:{canonical_smiles}"


def assert_no_canonical_overlap(membership: SplitMembership) -> None:
    all_ids = membership.train_ids + membership.validation_ids + membership.test_ids
    if len(all_ids) != len(set(all_ids)):
        raise SplitContractError("canonical molecule overlap across split membership")


def assert_scaffold_isolation(membership: SplitMembership) -> None:
    assigned_split_by_key: dict[str, SplitName] = {}
    for split in SPLIT_ORDER:
        for canonical_smiles in membership.ids(split):
            try:
                key = membership.grouping_keys[canonical_smiles]
            except KeyError as error:
                raise SplitContractError(
                    f"missing grouping key for canonical molecule {canonical_smiles}"
                ) from error
            previous_split = assigned_split_by_key.get(key)
            if previous_split is not None and previous_split != split:
                raise SplitContractError(f"grouping key overlaps across splits: {key}")
            assigned_split_by_key[key] = split


def _assert_complete_membership(
    records: Sequence[MoleculeRecord], membership: SplitMembership
) -> None:
    expected_ids = {record.canonical_smiles for record in records}
    observed_ids = set(membership.train_ids + membership.validation_ids + membership.test_ids)
    if expected_ids != observed_ids:
        raise SplitContractError("split membership does not cover the canonical molecule set")
