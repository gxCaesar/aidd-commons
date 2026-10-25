from __future__ import annotations

import pytest
from aidd_commons.freesolv.data import MoleculeRecord
from aidd_commons.freesolv.splits import (
    GLOBAL_SEED,
    SplitContractError,
    SplitMembership,
    SplitTargets,
    assert_no_canonical_overlap,
    assert_scaffold_isolation,
    random_split,
    scaffold_group_key,
    scaffold_split,
    split_targets,
)


def records(smiles: tuple[str, ...]) -> tuple[MoleculeRecord, ...]:
    return tuple(
        MoleculeRecord(
            source_id=f"mobley_fixture_{index}",
            input_smiles=smile,
            canonical_smiles=smile,
            target_kcal_mol=float(index),
        )
        for index, smile in enumerate(smiles)
    )


def test_split_targets_use_frozen_half_up_rounding() -> None:
    assert split_targets(11) == SplitTargets(train=9, validation=1, test=1)
    assert split_targets(2) == SplitTargets(train=2, validation=0, test=0)


def test_random_split_is_seeded_deterministic_and_complete() -> None:
    source_records = records(tuple(f"C{'C' * index}O" for index in range(1, 21)))

    first = random_split(source_records, seed=GLOBAL_SEED)
    second = random_split(source_records, seed=GLOBAL_SEED)

    assert first == second
    assert len(first.train_ids) == 16
    assert len(first.validation_ids) == 2
    assert len(first.test_ids) == 2
    assert_no_canonical_overlap(first)
    assert set(first.train_ids + first.validation_ids + first.test_ids) == {
        record.canonical_smiles for record in source_records
    }


def test_scaffold_split_is_deterministic_and_keeps_grouping_keys_whole() -> None:
    source_records = records(
        (
            "c1ccccc1",
            "Cc1ccccc1",
            "Oc1ccccc1",
            "C1CCCCC1",
            "CCO",
            "CCN",
            "CCC",
            "CCCC",
            "CCCl",
            "CCBr",
            "CCF",
        )
    )

    first = scaffold_split(source_records, seed=GLOBAL_SEED)
    second = scaffold_split(source_records, seed=GLOBAL_SEED)

    assert first == second
    assert_no_canonical_overlap(first)
    assert_scaffold_isolation(first)
    assert scaffold_group_key("CCO") == "acyclic:CCO"


def test_scaffold_isolation_rejects_deliberate_leakage() -> None:
    membership = SplitMembership(
        split_kind="scaffold",
        targets=SplitTargets(train=1, validation=1, test=0),
        train_ids=("c1ccccc1",),
        validation_ids=("Cc1ccccc1",),
        test_ids=(),
        grouping_keys={
            "c1ccccc1": "c1ccccc1",
            "Cc1ccccc1": "c1ccccc1",
        },
    )

    with pytest.raises(SplitContractError, match="grouping key"):
        assert_scaffold_isolation(membership)
