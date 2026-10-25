"""Measure train-set proximity and ridge error without selecting a domain threshold."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from math import floor
from pathlib import Path
from random import Random
from typing import Any

import numpy as np
from numpy.typing import NDArray
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]

from aidd_commons.freesolv.data import MoleculeRecord, parse_freesolv_v052
from aidd_commons.freesolv.models import (
    MORGAN_BITS as EXISTING_MORGAN_BITS,
)
from aidd_commons.freesolv.models import (
    MORGAN_CHIRALITY as EXISTING_MORGAN_CHIRALITY,
)
from aidd_commons.freesolv.models import (
    MORGAN_RADIUS as EXISTING_MORGAN_RADIUS,
)
from aidd_commons.freesolv.models import build_morgan_features
from aidd_commons.freesolv.splits import scaffold_group_key

from .protocol import (
    MORGAN_BITS,
    MORGAN_RADIUS,
    PROPERTIES,
    RIDGE_ALPHA,
    SEED,
    SOURCE_BYTES,
    TRAIN_FRACTION,
)


class AuditError(ValueError):
    """An input or measured invariant makes this audit invalid."""


@dataclass(frozen=True)
class AuditResult:
    cohort: dict[str, Any]
    split: dict[str, int]
    distance_statistics: dict[str, Any]
    error_halves: dict[str, dict[str, float | int]]
    train: tuple[MoleculeRecord, ...]
    test: tuple[MoleculeRecord, ...]
    pair_distances: NDArray[np.float64]
    nearest_indices: NDArray[np.intp]
    predictions: NDArray[np.float64]
    errors: NDArray[np.float64]


def load_release(path: Path) -> tuple[MoleculeRecord, ...]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise AuditError(f"source cannot be read: {path}") from error
    if len(raw) != SOURCE_BYTES:
        raise AuditError(f"source byte length is {len(raw)}, expected {SOURCE_BYTES}")
    try:
        records, _ = parse_freesolv_v052(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise AuditError(f"source does not parse as FreeSolv v0.52: {error}") from error
    if not records:
        raise AuditError("source has no molecules")
    return records


def split_scaffolds(
    records: Sequence[MoleculeRecord],
) -> tuple[tuple[MoleculeRecord, ...], tuple[MoleculeRecord, ...]]:
    if len(records) < 2:
        raise AuditError("at least two molecules are needed for the split")
    groups: dict[str, list[MoleculeRecord]] = defaultdict(list)
    for record in records:
        groups[scaffold_group_key(record.canonical_smiles)].append(record)
    random = Random(SEED)
    ordered: list[str] = []
    for size in sorted({len(group) for group in groups.values()}, reverse=True):
        keys = sorted(key for key, group in groups.items() if len(group) == size)
        random.shuffle(keys)
        ordered.extend(keys)
    target = floor(TRAIN_FRACTION * len(records) + 0.5)
    train: list[MoleculeRecord] = []
    test: list[MoleculeRecord] = []
    for key in ordered:
        (train if len(train) < target else test).extend(groups[key])
    if not train or not test:
        raise AuditError("split needs both train and test molecules")
    return tuple(train), tuple(test)


def property_matrix(records: Sequence[MoleculeRecord]) -> NDArray[np.float64]:
    rows: list[list[float]] = []
    for record in records:
        molecule = Chem.MolFromSmiles(record.canonical_smiles)
        if molecule is None:
            raise AuditError(f"invalid molecule: {record.source_id}")
        rows.append(
            [
                float(Descriptors.MolWt(molecule)),  # type: ignore[attr-defined]
                float(Descriptors.MolLogP(molecule)),  # type: ignore[attr-defined]
                float(rdMolDescriptors.CalcTPSA(molecule)),
                float(rdMolDescriptors.CalcNumHBD(molecule)),
                float(rdMolDescriptors.CalcNumHBA(molecule)),
            ]
        )
    matrix = np.asarray(rows, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != len(PROPERTIES) or not np.isfinite(matrix).all():
        raise AuditError("computed properties must be finite and have five columns")
    return matrix


def scaled_pair_distances(
    train_properties: NDArray[np.float64], test_properties: NDArray[np.float64]
) -> NDArray[np.float64]:
    if (
        train_properties.ndim != 2
        or test_properties.ndim != 2
        or len(train_properties) == 0
        or len(test_properties) == 0
        or train_properties.shape[1] != len(PROPERTIES)
        or test_properties.shape[1] != len(PROPERTIES)
        or not np.isfinite(train_properties).all()
        or not np.isfinite(test_properties).all()
    ):
        raise AuditError("nonempty finite train and test property matrices are required")
    scale = np.std(train_properties, axis=0, ddof=0)
    scale = np.where(scale == 0, 1.0, scale)
    distances = np.mean(
        np.abs(test_properties[:, None, :] - train_properties[None, :, :]) / scale,
        axis=2,
    )
    if not np.isfinite(distances).all():
        raise AuditError("scaled distances are not finite")
    return np.asarray(distances, dtype=np.float64)


def nearest_training(
    distances: NDArray[np.float64],
) -> tuple[NDArray[np.intp], NDArray[np.float64]]:
    if distances.ndim != 2 or 0 in distances.shape or not np.isfinite(distances).all():
        raise AuditError("each test molecule needs a finite training neighbour")
    indices = np.argmin(distances, axis=1)
    nearest = distances[np.arange(len(indices)), indices]
    return np.asarray(indices, dtype=np.intp), np.asarray(nearest, dtype=np.float64)


def error_halves(
    distances: NDArray[np.float64], errors: NDArray[np.float64], source_ids: Sequence[str]
) -> dict[str, dict[str, float | int]]:
    if (
        len(distances) < 2
        or len(distances) != len(errors)
        or len(distances) != len(source_ids)
        or not np.isfinite(distances).all()
        or not np.isfinite(errors).all()
        or np.any(errors < 0)
    ):
        raise AuditError("at least two finite distances and nonnegative errors are required")
    order = sorted(range(len(distances)), key=lambda i: (float(distances[i]), source_ids[i]))
    halfway = len(order) // 2
    return {
        "smaller_distance": {
            "count": halfway,
            "median_absolute_error_kcal_mol": float(np.median(errors[order[:halfway]])),
        },
        "larger_distance": {
            "count": len(order) - halfway,
            "median_absolute_error_kcal_mol": float(np.median(errors[order[halfway:]])),
        },
    }


def analyze(records: Sequence[MoleculeRecord]) -> AuditResult:
    if (EXISTING_MORGAN_RADIUS, EXISTING_MORGAN_BITS, EXISTING_MORGAN_CHIRALITY) != (
        MORGAN_RADIUS,
        MORGAN_BITS,
        True,
    ):
        raise AuditError("existing Morgan feature builder differs from the frozen baseline")
    train, test = split_scaffolds(records)
    train_keys = {scaffold_group_key(row.canonical_smiles) for row in train}
    test_keys = {scaffold_group_key(row.canonical_smiles) for row in test}
    targets = np.asarray([row.target_kcal_mol for row in records], dtype=np.float64)
    pair_distances = scaled_pair_distances(property_matrix(train), property_matrix(test))
    nearest_indices, nearest = nearest_training(pair_distances)
    model = Ridge(alpha=RIDGE_ALPHA)
    model.fit(build_morgan_features(train), [row.target_kcal_mol for row in train])
    predictions = np.asarray(model.predict(build_morgan_features(test)), dtype=np.float64)
    observed = np.asarray([row.target_kcal_mol for row in test], dtype=np.float64)
    errors = np.abs(predictions - observed)
    worst_index = int(np.argmax(nearest))
    farthest_index = int(np.argmax(pair_distances[worst_index]))
    cohort: dict[str, Any] = {
        "molecules": len(records),
        "distinct_scaffolds": len(train_keys | test_keys),
        "measured_median_kcal_mol": float(np.median(targets)),
        "measured_q1_kcal_mol": float(np.quantile(targets, 0.25)),
        "measured_q3_kcal_mol": float(np.quantile(targets, 0.75)),
        "measured_iqr_kcal_mol": float(np.quantile(targets, 0.75) - np.quantile(targets, 0.25)),
    }
    split = {
        "train_molecules": len(train),
        "test_molecules": len(test),
        "train_scaffolds": len(train_keys),
        "test_scaffolds": len(test_keys),
    }
    distance_statistics: dict[str, Any] = {
        "median": float(np.median(nearest)),
        "q1": float(np.quantile(nearest, 0.25)),
        "q3": float(np.quantile(nearest, 0.75)),
        "iqr": float(np.quantile(nearest, 0.75) - np.quantile(nearest, 0.25)),
        "farthest_nearest_distance": float(nearest[worst_index]),
        "farthest_nearest_test_id": test[worst_index].source_id,
        "nearest_train_id_for_that_test": train[int(nearest_indices[worst_index])].source_id,
        "farthest_train_distance_for_that_test": float(pair_distances[worst_index, farthest_index]),
        "farthest_train_id_for_that_test": train[farthest_index].source_id,
    }
    return AuditResult(
        cohort=cohort,
        split=split,
        distance_statistics=distance_statistics,
        error_halves=error_halves(nearest, errors, [row.source_id for row in test]),
        train=train,
        test=test,
        pair_distances=pair_distances,
        nearest_indices=nearest_indices,
        predictions=predictions,
        errors=errors,
    )


def check_invariants(result: AuditResult) -> list[str]:
    failures: list[str] = []
    train_ids = {row.canonical_smiles for row in result.train}
    test_ids = {row.canonical_smiles for row in result.test}
    train_keys = {scaffold_group_key(value) for value in train_ids}
    test_keys = {scaffold_group_key(value) for value in test_ids}
    if train_ids & test_ids or train_keys & test_keys:
        failures.append("canonical molecule or scaffold crosses the split")
    expected_train, expected_test = split_scaffolds(result.train + result.test)
    if {row.canonical_smiles for row in expected_train} != train_ids or {
        row.canonical_smiles for row in expected_test
    } != test_ids:
        failures.append("membership differs from the frozen scaffold assignment")
    if result.split != {
        "train_molecules": len(result.train),
        "test_molecules": len(result.test),
        "train_scaffolds": len(train_keys),
        "test_scaffolds": len(test_keys),
    } or result.cohort["molecules"] != len(result.train) + len(result.test):
        failures.append("cohort and split counts disagree")
    targets = np.asarray(
        [row.target_kcal_mol for row in result.train + result.test], dtype=np.float64
    )
    expected_cohort = {
        "distinct_scaffolds": len(train_keys | test_keys),
        "measured_median_kcal_mol": float(np.median(targets)),
        "measured_q1_kcal_mol": float(np.quantile(targets, 0.25)),
        "measured_q3_kcal_mol": float(np.quantile(targets, 0.75)),
        "measured_iqr_kcal_mol": float(np.quantile(targets, 0.75) - np.quantile(targets, 0.25)),
    }
    if any(result.cohort[key] != value for key, value in expected_cohort.items()):
        failures.append("cohort scaffold count or measured quartiles disagree")
    if result.pair_distances.shape != (len(result.test), len(result.train)):
        failures.append("pairwise distance shape disagrees with split")
        return failures
    try:
        indices, nearest = nearest_training(result.pair_distances)
    except AuditError as error:
        failures.append(str(error))
        return failures
    if not np.array_equal(indices, result.nearest_indices):
        failures.append("reported nearest neighbours are not minima")
    if len(result.predictions) != len(result.test) or len(result.errors) != len(result.test):
        failures.append("test prediction or error count disagrees")
        return failures
    expected_errors = np.abs(
        result.predictions - np.asarray([row.target_kcal_mol for row in result.test])
    )
    if not np.isfinite(expected_errors).all() or not np.allclose(expected_errors, result.errors):
        failures.append("absolute errors disagree with predictions and measurements")
    if result.error_halves != error_halves(
        nearest, result.errors, [row.source_id for row in result.test]
    ):
        failures.append("error halves disagree with distance ranking")
    if result.distance_statistics["median"] != float(np.median(nearest)):
        failures.append("distance median disagrees with test distances")
    if result.distance_statistics["q1"] != float(np.quantile(nearest, 0.25)):
        failures.append("distance first quartile disagrees with test distances")
    if result.distance_statistics["q3"] != float(np.quantile(nearest, 0.75)):
        failures.append("distance third quartile disagrees with test distances")
    if result.distance_statistics["iqr"] != float(
        np.quantile(nearest, 0.75) - np.quantile(nearest, 0.25)
    ):
        failures.append("distance interquartile range disagrees with test distances")
    worst_index = int(np.argmax(nearest))
    farthest_index = int(np.argmax(result.pair_distances[worst_index]))
    expected_extreme = {
        "farthest_nearest_distance": float(nearest[worst_index]),
        "farthest_nearest_test_id": result.test[worst_index].source_id,
        "nearest_train_id_for_that_test": result.train[int(indices[worst_index])].source_id,
        "farthest_train_distance_for_that_test": float(
            result.pair_distances[worst_index, farthest_index]
        ),
        "farthest_train_id_for_that_test": result.train[farthest_index].source_id,
    }
    if any(result.distance_statistics[key] != value for key, value in expected_extreme.items()):
        failures.append("extreme test–training pair disagrees with distances")
    return failures
