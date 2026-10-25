"""Small, label-blind diversity campaign on authored synthetic molecular graphs.

This teaching example never reads ChEMBL files or fits a predictive model.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from math import ceil
from typing import Any

import numpy as np
from numpy.typing import NDArray
from rdkit import Chem, rdBase
from rdkit.Chem import rdFingerprintGenerator

from aidd_commons.chembl_egfr.splits import scaffold_group_key


def budget_checkpoints(pool_size: int) -> tuple[int, ...]:
    """Four equal batches, each floor(5% of the ORIGINAL pool)."""
    if isinstance(pool_size, bool) or not isinstance(pool_size, int) or pool_size < 20:
        raise ValueError("pool_size must be an integer of at least 20")
    batch = pool_size // 20
    return tuple(round_index * batch for round_index in range(5))


def group_partition(groups: Sequence[str]) -> tuple[tuple[int, ...], ...]:
    """Target 10/70/20%; assign whole groups to largest remaining capacity.

    Sort groups by descending size then key. Ties in capacity use initial,
    pool, evaluation order. Whole groups can cause target-size deviations.
    """
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(groups):
        if not key:
            raise ValueError("group keys must be nonempty")
        grouped[key].append(index)
    if len(grouped) < 3:
        raise ValueError("at least three independent groups are required")
    targets = (len(groups) * 0.1, len(groups) * 0.7, len(groups) * 0.2)
    assigned: list[list[int]] = [[], [], []]
    for _, members in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        partition = max(range(3), key=lambda p: targets[p] - len(assigned[p]))
        assigned[partition].extend(members)
    if any(not members for members in assigned):
        raise ValueError("whole-group allocation left an empty partition")
    return tuple(tuple(sorted(members)) for members in assigned)


def _indices(values: Sequence[int], size: int) -> tuple[int, ...]:
    result = tuple(values)
    if any(isinstance(i, bool) or not isinstance(i, (int, np.integer)) for i in result):
        raise ValueError("indices must be integers")
    if len(set(result)) != len(result) or any(i < 0 or i >= size for i in result):
        raise ValueError("indices must be unique and in range")
    return result


def maxmin_order(
    features: NDArray[Any], initial: Sequence[int], pool: Sequence[int], count: int
) -> tuple[int, ...]:
    """Greedy maximum minimum Tanimoto distance; ties choose smallest row index."""
    if features.ndim != 2 or not np.isin(features, (0, 1)).all():
        raise ValueError("features must be a finite binary matrix")
    initial_rows = _indices(initial, len(features))
    remaining = set(_indices(pool, len(features)))
    if not initial_rows or remaining.intersection(initial_rows):
        raise ValueError("initial must be nonempty and disjoint from pool")
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= len(remaining):
        raise ValueError("count must be an integer within pool capacity")
    bits = features.astype(bool)
    selected: list[int] = []
    reference = list(initial_rows)
    for _ in range(count):

        def distance(index: int) -> float:
            union = np.logical_or(bits[index], bits[reference]).sum(axis=1)
            intersection = np.logical_and(bits[index], bits[reference]).sum(axis=1)
            # Two empty fingerprints have similarity 1, distance 0.
            similarity = np.divide(intersection, union, out=np.ones(len(union)), where=union > 0)
            return float((1 - similarity).min())

        choice = max(sorted(remaining), key=distance)
        selected.append(choice)
        reference.append(choice)
        remaining.remove(choice)
    return tuple(selected)


def recovery_curve(
    labels: NDArray[Any], order: Sequence[int], checkpoints: Sequence[int]
) -> tuple[tuple[float, ...], float]:
    """Score pool-local picks against exactly ceil(10% of original pool) targets."""
    if labels.ndim != 1 or not len(labels) or not np.isfinite(labels).all():
        raise ValueError("labels must be a nonempty finite vector")
    picks = _indices(order, len(labels))
    steps = tuple(checkpoints)
    if (
        len(steps) < 2
        or any(isinstance(k, bool) or not isinstance(k, int) for k in steps)
        or steps[0] != 0
        or any(a >= b for a, b in zip(steps, steps[1:], strict=False))
        or steps[-1] > len(picks)
    ):
        raise ValueError("checkpoints must increase strictly from zero within order length")
    top_count = ceil(len(labels) / 10)
    top = set(sorted(range(len(labels)), key=lambda i: (-float(labels[i]), i))[:top_count])
    recall = tuple(len(top.intersection(picks[:k])) / top_count for k in steps)
    auc = float(np.trapezoid(recall, x=steps) / steps[-1])
    return recall, auc


def synthetic_library() -> tuple[NDArray[Any], tuple[str, ...], NDArray[Any]]:
    """60 authored graphs and artificial scores with no medicinal interpretation."""
    smiles = [
        "C" * length + suffix
        for length in range(1, 11)
        for suffix in ("O", "N", "F", "C(=O)O", "c1ccccc1", "C1CCCCC1")
    ]
    molecules = [Chem.MolFromSmiles(value) for value in smiles]
    canonical = [Chem.MolToSmiles(mol, isomericSmiles=True) for mol in molecules]
    if len(set(canonical)) != len(smiles):
        raise ValueError("synthetic library must contain unique molecular graphs")
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=2, fpSize=2048, includeChirality=True
    )
    features = np.array([generator.GetFingerprintAsNumPy(mol) for mol in molecules])
    groups = tuple(scaffold_group_key(value) for value in canonical)
    labels = np.array([((index * 17) % 61) / 10 for index in range(len(smiles))])
    return features, groups, labels


def campaign_summary() -> dict[str, Any]:
    features, groups, labels = synthetic_library()
    initial, pool, evaluation = group_partition(groups)
    checkpoints = budget_checkpoints(len(pool))
    count = checkpoints[-1]
    pool_local = {row: index for index, row in enumerate(pool)}

    def score(picks: Sequence[int]) -> dict[str, Any]:
        recall, auc = recovery_curve(
            labels[list(pool)], tuple(pool_local[row] for row in picks), checkpoints
        )
        return {"recovery": list(recall), "normalized_auc": auc}

    diversity = score(maxmin_order(features, initial, pool, count))
    random_runs = [
        {"seed": seed, **score(np.random.default_rng(seed).permutation(pool)[:count].tolist())}
        for seed in range(5)
    ]
    return {
        "data_kind": "synthetic-teaching-example",
        "real_campaign": "not_run",
        "scope": "Authored graphs and artificial scores; no evidence of assay performance.",
        "software": {"numpy": np.__version__, "rdkit": rdBase.rdkitVersion},
        "partitions": {
            name: {"molecules": len(rows), "groups": len({groups[i] for i in rows})}
            for name, rows in zip(
                ("initial", "pool", "evaluation"), (initial, pool, evaluation), strict=True
            )
        },
        "budget": {
            "checkpoints": list(checkpoints),
            "batch_size": checkpoints[1],
            "acquired_fraction": count / len(pool),
            "top_decile_size": ceil(len(pool) / 10),
        },
        "maxmin": diversity,
        "random_runs": random_runs,
        "evaluation": "not_scored; no predictive model is fitted",
    }
