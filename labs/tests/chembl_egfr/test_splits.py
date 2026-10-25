from __future__ import annotations

from dataclasses import replace

from aidd_commons.chembl_egfr.data import ParentActivityRecord
from aidd_commons.chembl_egfr.splits import (
    SplitTargets,
    assert_scaffold_isolation,
    greedy_group_split,
    scaffold_group_key,
    scaffold_split,
    split_targets,
)


def parent(parent_id: str, smiles: str, target: float = 7.0) -> ParentActivityRecord:
    return ParentActivityRecord(
        assay_chembl_id="CHEMBL5736995",
        parent_molecule_chembl_id=parent_id,
        canonical_smiles=smiles,
        target_pchembl=target,
        activity_ids=(int(parent_id.rsplit("_", 1)[-1]),),
        replicate_count=1,
        pchembl_range=0.0,
    )


def test_split_targets_use_frozen_round_half_up_ratios() -> None:
    assert split_targets(10) == SplitTargets(train=7, validation=2, test=1)
    assert split_targets(902) == SplitTargets(train=631, validation=135, test=136)


def test_greedy_group_split_sorts_by_size_then_key_and_never_breaks_groups() -> None:
    grouping = {
        "a1": "a",
        "a2": "a",
        "a3": "a",
        "a4": "a",
        "b1": "b",
        "b2": "b",
        "b3": "b",
        "c1": "c",
        "c2": "c",
        "d1": "d",
    }

    membership = greedy_group_split(grouping)

    assert membership.targets == SplitTargets(train=7, validation=2, test=1)
    assert membership.train_ids == ("a1", "a2", "a3", "a4", "b1", "b2", "b3")
    assert membership.validation_ids == ("c1", "c2")
    assert membership.test_ids == ("d1",)
    assert_scaffold_isolation(membership)


def test_scaffold_key_preserves_stereochemistry_and_split_ignores_labels() -> None:
    first_smiles = "C1=C([C@H](Nc2ccccc2)c2ccccc2)NNN1"
    second_smiles = "C1=C([C@@H](Nc2ccccc2)c2ccccc2)NNN1"
    assert scaffold_group_key(first_smiles) != scaffold_group_key(second_smiles)

    records = (
        parent("CHEMBL_FIXTURE_1", first_smiles),
        parent("CHEMBL_FIXTURE_2", second_smiles),
        parent("CHEMBL_FIXTURE_3", "c1ccccc1"),
        parent("CHEMBL_FIXTURE_4", "C1CCCCC1"),
        parent("CHEMBL_FIXTURE_5", "c1ccncc1"),
        parent("CHEMBL_FIXTURE_6", "c1ccoc1"),
        parent("CHEMBL_FIXTURE_7", "c1ccsc1"),
        parent("CHEMBL_FIXTURE_8", "C1CCCC1"),
        parent("CHEMBL_FIXTURE_9", "C1CCC1"),
        parent("CHEMBL_FIXTURE_10", "C1CC1"),
    )
    shifted = tuple(
        replace(record, target_pchembl=record.target_pchembl + 100.0) for record in records
    )

    original_membership = scaffold_split(records)
    shifted_membership = scaffold_split(shifted)

    assert original_membership == shifted_membership
    assert_scaffold_isolation(original_membership)
