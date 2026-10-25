from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from sklearn.ensemble import RandomForestRegressor  # type: ignore[import-untyped]
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]

from aidd_commons.freesolv.data import MoleculeRecord
from aidd_commons.freesolv.splits import GLOBAL_SEED

MORGAN_RADIUS = 2
MORGAN_BITS = 2048
MORGAN_CHIRALITY = True


class FeatureContractError(ValueError):
    """Raised when feature construction departs from the frozen inputs."""


class ModelContractError(ValueError):
    """Raised when training provenance or frozen model settings are invalid."""


@dataclass(frozen=True)
class FitTrace:
    model_fit_ids: Mapping[str, tuple[str, ...]]
    feature_fit_ids: tuple[str, ...]


@dataclass(frozen=True)
class FrozenModels:
    train_mean: float
    ridge: Ridge
    random_forest: RandomForestRegressor
    fit_trace: FitTrace


def build_morgan_features(
    records: Sequence[MoleculeRecord],
    feature_sources: tuple[str, ...] = ("canonical_smiles",),
) -> np.ndarray:
    if feature_sources != ("canonical_smiles",):
        raise FeatureContractError(
            "target or non-canonical fields are not allowed as model features"
        )
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=MORGAN_RADIUS,
        fpSize=MORGAN_BITS,
        includeChirality=MORGAN_CHIRALITY,
    )
    matrix = np.zeros((len(records), MORGAN_BITS), dtype=np.uint8)
    for index, record in enumerate(records):
        molecule = Chem.MolFromSmiles(record.canonical_smiles)
        if molecule is None:
            raise FeatureContractError(
                f"invalid canonical molecule for feature construction: {record.canonical_smiles}"
            )
        fingerprint = generator.GetFingerprint(molecule)
        DataStructs.ConvertToNumpyArray(fingerprint, matrix[index])
    return matrix


def fit_frozen_models(train_records: Sequence[MoleculeRecord]) -> FrozenModels:
    if not train_records:
        raise ModelContractError("training partition must not be empty")
    train_ids = tuple(record.canonical_smiles for record in train_records)
    if len(train_ids) != len(set(train_ids)):
        raise ModelContractError("training partition contains duplicate canonical molecules")
    targets = np.asarray([record.target_kcal_mol for record in train_records], dtype=float)
    if not np.isfinite(targets).all():
        raise ModelContractError("training partition contains a non-finite target")
    features = build_morgan_features(train_records)

    ridge = Ridge(alpha=1.0)
    ridge.fit(features, targets)
    random_forest = RandomForestRegressor(
        n_estimators=500,
        max_features="sqrt",
        min_samples_leaf=1,
        random_state=GLOBAL_SEED,
        n_jobs=1,
    )
    random_forest.fit(features, targets)
    fit_trace = FitTrace(
        model_fit_ids={
            "train_mean": train_ids,
            "morgan_ridge": train_ids,
            "morgan_random_forest": train_ids,
        },
        feature_fit_ids=train_ids,
    )
    assert_training_only_fit(fit_trace, train_ids)
    return FrozenModels(
        train_mean=float(np.mean(targets)),
        ridge=ridge,
        random_forest=random_forest,
        fit_trace=fit_trace,
    )


def predict_models(
    models: FrozenModels, records: Sequence[MoleculeRecord]
) -> dict[str, np.ndarray]:
    if not records:
        return {
            "train_mean": np.empty(0, dtype=float),
            "morgan_ridge": np.empty(0, dtype=float),
            "morgan_random_forest": np.empty(0, dtype=float),
        }
    features = build_morgan_features(records)
    return {
        "train_mean": np.full(len(records), models.train_mean, dtype=float),
        "morgan_ridge": np.asarray(models.ridge.predict(features), dtype=float),
        "morgan_random_forest": np.asarray(models.random_forest.predict(features), dtype=float),
    }


def assert_training_only_fit(trace: FitTrace, train_ids: tuple[str, ...]) -> None:
    if trace.feature_fit_ids != train_ids:
        raise ModelContractError("feature preprocessing was fitted outside train")
    for model_name, fitted_ids in trace.model_fit_ids.items():
        if fitted_ids != train_ids:
            raise ModelContractError(f"{model_name} was fitted outside train")
