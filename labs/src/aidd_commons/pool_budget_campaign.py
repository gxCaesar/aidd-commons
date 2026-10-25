"""Frozen retrospective campaign; acquisition receives structures, never labels.

The oracle is a procedural access boundary, not a security sandbox. Ingestion
enforces source filters; prediction code sees only initial and acquired targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]

from aidd_commons.chembl_egfr.data import AssayDataset
from aidd_commons.chembl_egfr.features import build_morgan_matrix
from aidd_commons.chembl_egfr.splits import scaffold_group_key
from aidd_commons.pool_budget import (
    budget_checkpoints,
    group_partition,
    maxmin_order,
    recovery_curve,
)


class CampaignContractError(ValueError):
    """A frozen campaign cannot proceed without changing its contract."""


@dataclass(frozen=True)
class Library:
    parent_ids: tuple[str, ...]
    features: NDArray[Any]
    groups: tuple[str, ...]


@dataclass(frozen=True)
class PolicyPlan:
    name: str
    picks: tuple[int, ...]


@dataclass(frozen=True)
class CampaignPlan:
    initial: tuple[int, ...]
    pool: tuple[int, ...]
    evaluation: tuple[int, ...]
    checkpoints: tuple[int, ...]
    policies: tuple[PolicyPlan, ...]


@dataclass(frozen=True)
class FrozenPredictions:
    plan: CampaignPlan
    values: tuple[tuple[tuple[float, ...], ...], ...]
    fit_rows: tuple[tuple[tuple[int, ...], ...], ...]


def _training_rows(plan: CampaignPlan, policy: int, checkpoint: int) -> tuple[int, ...]:
    if not 0 <= policy < len(plan.policies) or checkpoint not in plan.checkpoints:
        raise CampaignContractError("undeclared policy or checkpoint")
    return tuple(sorted(plan.initial + plan.policies[policy].picks[:checkpoint]))


class LabelOracle:
    def __init__(self, targets: NDArray[Any], plan: CampaignPlan) -> None:
        self._targets = targets.copy()
        self._targets.flags.writeable = False
        self._plan = plan
        self._frozen: FrozenPredictions | None = None

    def training_labels(self, policy: int, checkpoint: int) -> NDArray[Any]:
        if self._frozen is not None:
            raise CampaignContractError("predictions already frozen; no further fitting")
        return self._targets[list(_training_rows(self._plan, policy, checkpoint))].copy()

    def evaluation_targets(self) -> NDArray[Any]:
        if self._frozen is None:
            raise CampaignContractError("all predictions must be frozen before scoring")
        return self._targets[list(self._plan.evaluation)].copy()

    def pool_targets(self) -> NDArray[Any]:
        if self._frozen is None:
            raise CampaignContractError("all predictions must be frozen before scoring")
        return self._targets[list(self._plan.pool)].copy()


@dataclass(frozen=True)
class PreparedCampaign:
    library: Library
    plan: CampaignPlan
    oracle: LabelOracle


def build_plan(library: Library) -> CampaignPlan:
    """The selector has no interface for target values."""
    initial, pool, evaluation = group_partition(library.groups)
    checkpoints = budget_checkpoints(len(pool))
    policies = [
        PolicyPlan("maxmin", maxmin_order(library.features, initial, pool, checkpoints[-1]))
    ]
    policies.extend(
        PolicyPlan(
            f"random-{seed}",
            tuple(
                int(row) for row in np.random.default_rng(seed).permutation(pool)[: checkpoints[-1]]
            ),
        )
        for seed in range(5)
    )
    return CampaignPlan(initial, pool, evaluation, checkpoints, tuple(policies))


def prepare_campaign(dataset: AssayDataset) -> PreparedCampaign:
    records = tuple(sorted(dataset.records, key=lambda record: record.parent_molecule_chembl_id))
    parent_ids = tuple(record.parent_molecule_chembl_id for record in records)
    if (
        not records
        or any(not value for value in parent_ids)
        or len(set(parent_ids)) != len(parent_ids)
        or any(record.assay_chembl_id != dataset.assay_chembl_id for record in records)
    ):
        raise CampaignContractError("missing, duplicate, or cross-assay entity")
    targets = np.asarray([record.target_pchembl for record in records], dtype=np.float64)
    if not np.isfinite(targets).all():
        raise CampaignContractError("targets must be finite; no additional exclusions")
    try:
        features = build_morgan_matrix(records).values
        groups = tuple(scaffold_group_key(record.canonical_smiles) for record in records)
        features.flags.writeable = False
        library = Library(parent_ids, features, groups)
        plan = build_plan(library)
    except ValueError as error:
        raise CampaignContractError(str(error)) from error
    return PreparedCampaign(library, plan, LabelOracle(targets, plan))


def fit_checkpoint(
    features: NDArray[Any],
    train_rows: tuple[int, ...],
    labels: NDArray[Any],
    evaluation_rows: tuple[int, ...],
) -> tuple[float, ...]:
    if features.ndim != 2 or features.shape[1] == 0 or not np.isin(features, (0, 1)).all():
        raise CampaignContractError("features must be a finite binary matrix")
    for rows in (train_rows, evaluation_rows):
        if (
            not rows
            or len(set(rows)) != len(rows)
            or tuple(sorted(rows)) != rows
            or any(
                isinstance(row, bool)
                or not isinstance(row, (int, np.integer))
                or row < 0
                or row >= len(features)
                for row in rows
            )
        ):
            raise CampaignContractError("rows must be nonempty, unique, sorted, valid indices")
    if (
        set(train_rows).intersection(evaluation_rows)
        or labels.shape != (len(train_rows),)
        or not np.isfinite(labels).all()
    ):
        raise CampaignContractError("overlapping rows or invalid training labels")
    model = Ridge(alpha=1.0, fit_intercept=True, solver="lsqr", tol=1e-8, max_iter=10000)
    model.fit(features[list(train_rows)].astype(np.float64), labels)
    predictions = model.predict(features[list(evaluation_rows)].astype(np.float64))
    if predictions.shape != (len(evaluation_rows),) or not np.isfinite(predictions).all():
        raise CampaignContractError("invalid prediction vector")
    return tuple(float(value) for value in predictions)


def _validate_predictions(prepared: PreparedCampaign, frozen: FrozenPredictions) -> None:
    plan = prepared.plan
    if (
        frozen.plan is not plan
        or len(frozen.values) != len(plan.policies)
        or len(frozen.fit_rows) != len(plan.policies)
    ):
        raise CampaignContractError("predictions do not belong to this complete campaign")
    for policy, (values, fit_rows) in enumerate(zip(frozen.values, frozen.fit_rows, strict=True)):
        if len(values) != len(plan.checkpoints) or len(fit_rows) != len(plan.checkpoints):
            raise CampaignContractError("missing checkpoint predictions")
        for k, vector, rows in zip(plan.checkpoints, values, fit_rows, strict=True):
            if (
                len(vector) != len(plan.evaluation)
                or not np.isfinite(vector).all()
                or rows != _training_rows(plan, policy, k)
            ):
                raise CampaignContractError("invalid predictions or training membership")


def freeze_predictions(prepared: PreparedCampaign) -> FrozenPredictions:
    plan = prepared.plan
    rows = tuple(
        tuple(_training_rows(plan, policy, k) for k in plan.checkpoints)
        for policy in range(len(plan.policies))
    )
    values = tuple(
        tuple(
            fit_checkpoint(
                prepared.library.features,
                fit_rows,
                prepared.oracle.training_labels(policy, k),
                plan.evaluation,
            )
            for k, fit_rows in zip(plan.checkpoints, checkpoints, strict=True)
        )
        for policy, checkpoints in enumerate(rows)
    )
    frozen = FrozenPredictions(plan, values, rows)
    _validate_predictions(prepared, frozen)
    prepared.oracle._frozen = frozen
    return frozen


def score_campaign(prepared: PreparedCampaign, frozen: FrozenPredictions) -> dict[str, Any]:
    _validate_predictions(prepared, frozen)
    if prepared.oracle._frozen is not frozen:
        raise CampaignContractError("only the original frozen prediction object can be scored")
    plan, library = prepared.plan, prepared.library
    evaluation_targets = prepared.oracle.evaluation_targets()
    pool_targets = prepared.oracle.pool_targets()
    pool_local = {row: index for index, row in enumerate(plan.pool)}
    pool_group_count = len({library.groups[row] for row in plan.pool})
    policies = []
    for policy, predictions in zip(plan.policies, frozen.values, strict=True):
        recovery, auc = recovery_curve(
            pool_targets, tuple(pool_local[row] for row in policy.picks), plan.checkpoints
        )
        policies.append(
            {
                "name": policy.name,
                "recovery": list(recovery),
                "normalized_auc": auc,
                "scaffold_fraction": [
                    len({library.groups[row] for row in policy.picks[:k]}) / pool_group_count
                    for k in plan.checkpoints
                ],
                "evaluation_mae": [
                    float(np.mean(np.abs(np.asarray(vector) - evaluation_targets)))
                    for vector in predictions
                ],
            }
        )
    return {
        "partitions": {
            name: {"parents": len(rows), "groups": len({library.groups[row] for row in rows})}
            for name, rows in zip(
                ("initial", "pool", "evaluation"),
                (plan.initial, plan.pool, plan.evaluation),
                strict=True,
            )
        },
        "budget": {
            "checkpoints": list(plan.checkpoints),
            "batch_size": plan.checkpoints[1],
            "acquired_count": plan.checkpoints[-1],
            "original_pool_parent_count": len(plan.pool),
            "actual_budget_fraction": plan.checkpoints[-1] / len(plan.pool),
            "top_decile_size": ceil(len(plan.pool) / 10),
        },
        "policies": policies,
    }
