"""A calibrated-predictive-uncertainty acquisition policy, as a new arm.

The frozen `chembl37-egfr-pool-budget-v1` campaign already ran two policies to
completion: MaxMin, which is deliberately label-blind, and five fixed random
seeds. Neither connects an acquisition choice to a model's own uncertainty. This
module adds exactly that, as a separate one-time protocol that reuses the same
partition, budget, representation and scoring utilities without importing,
calling, or modifying `pool_budget_campaign.py`'s `build_plan`, and without
touching any file the completed campaign wrote.

Unlike MaxMin, this selector is not label-blind: at each round it fits on the
labels of the initial parents and everything acquired in earlier rounds of this
same run, which the frozen contract's own language allows ("Predictors receive
only initial and acquired targets"). It never sees a pool label before that
label has been acquired by this policy, and it never sees an evaluation label
before every round's picks are finalized.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]

from aidd_commons.chembl_egfr.data import AssayDataset
from aidd_commons.chembl_egfr.features import build_morgan_matrix
from aidd_commons.chembl_egfr.splits import scaffold_group_key
from aidd_commons.pool_budget import budget_checkpoints, group_partition, recovery_curve

RIDGE_PARAMS: dict[str, Any] = {
    "alpha": 1.0,
    "fit_intercept": True,
    "solver": "lsqr",
    "tol": 1e-8,
    "max_iter": 10000,
}


class UncertaintyContractError(ValueError):
    """Raised when an acquisition step would violate the label-access boundary."""


class AcquiredLabelLedger:
    """Tracks which pool rows this run has legitimately acquired, and nothing else.

    A row's label can be read once it has been recorded as acquired by this same
    ledger. There is no path to read a pool row's label before that, and no path
    to read any evaluation-partition label at all; this class never receives the
    evaluation target vector.
    """

    def __init__(self, targets: NDArray[Any], initial: tuple[int, ...]) -> None:
        self._targets = targets.copy()
        self._targets.flags.writeable = False
        self._acquired: list[int] = []
        self._initial = tuple(initial)
        self._closed = False

    def current_training_rows(self) -> tuple[int, ...]:
        return tuple(sorted(self._initial + tuple(self._acquired)))

    def current_training_labels(self) -> NDArray[Any]:
        rows = self.current_training_rows()
        return self._targets[list(rows)].copy()

    def acquire(self, rows: tuple[int, ...]) -> None:
        if self._closed:
            raise UncertaintyContractError("no acquisition after this ledger is closed")
        if set(rows) & set(self._acquired) or set(rows) & set(self._initial):
            raise UncertaintyContractError("a row was acquired twice or was already initial")
        self._acquired.extend(rows)

    def close(self) -> tuple[int, ...]:
        """Finalize the full acquisition order; no further acquisition is possible."""
        self._closed = True
        return tuple(self._acquired)


@dataclass(frozen=True)
class RoundDiagnostic:
    round_index: int
    training_rows: int
    fold_models: int
    variance_minimum: float
    variance_maximum: float
    picked: int


def _stable_folds(rows: tuple[int, ...], fold_count: int) -> tuple[NDArray[Any], ...]:
    """Deterministic contiguous folds over the stably sorted current training rows.

    No random state of any kind; the same training set always yields the same
    folds, in the same order, on any machine.
    """
    ordered = np.asarray(sorted(rows))
    return tuple(np.array_split(ordered, min(fold_count, len(ordered))))


def ensemble_variance_order(
    features: NDArray[Any],
    ledger: AcquiredLabelLedger,
    pool: tuple[int, ...],
    checkpoints: tuple[int, ...],
    *,
    fold_count: int = 5,
) -> tuple[tuple[int, ...], tuple[RoundDiagnostic, ...]]:
    """Acquire `checkpoints[-1]` pool rows in `len(checkpoints) - 1` equal rounds.

    Each round fits `fold_count` Ridge models (fixed hyperparameters, one held-out
    contiguous fold each) on the current training rows, scores every remaining
    pool candidate by the variance of the fold ensemble's predictions, and
    acquires the batch with the largest variance, ties broken by the smallest
    global row index. This is a ranking proxy for acquisition, not a rigorously
    calibrated predictive interval; no interval-coverage check is performed here.
    """
    if features.ndim != 2 or features.shape[1] == 0 or not np.isin(features, (0, 1)).all():
        raise UncertaintyContractError("features must be a finite binary matrix")
    if len(checkpoints) < 2 or checkpoints[0] != 0:
        raise UncertaintyContractError("checkpoints must start at zero with at least one round")
    remaining = list(pool)
    diagnostics: list[RoundDiagnostic] = []
    for round_index in range(1, len(checkpoints)):
        expected_remaining = len(pool) - checkpoints[round_index - 1]
        if len(remaining) != expected_remaining:
            raise UncertaintyContractError("pool bookkeeping drifted from the declared checkpoints")
        train_rows = ledger.current_training_rows()
        train_labels = ledger.current_training_labels()
        folds = _stable_folds(train_rows, fold_count)
        row_to_label = dict(zip(train_rows, train_labels.tolist(), strict=True))
        models = []
        for fold in folds:
            fold_set = set(fold.tolist())
            fit_rows = [row for row in train_rows if row not in fold_set]
            if len(fit_rows) < 2:
                continue
            model = Ridge(**RIDGE_PARAMS)
            model.fit(
                features[fit_rows].astype(np.float64),
                np.asarray([row_to_label[row] for row in fit_rows]),
            )
            models.append(model)
        if len(models) < 2:
            raise UncertaintyContractError("too few fold models to estimate a variance")
        predictions = np.stack(
            [model.predict(features[remaining].astype(np.float64)) for model in models], axis=0
        )
        variance = predictions.var(axis=0, ddof=1)
        this_round_batch = checkpoints[round_index] - checkpoints[round_index - 1]
        order = sorted(range(len(remaining)), key=lambda i: (-variance[i], remaining[i]))
        picks = tuple(remaining[i] for i in order[:this_round_batch])
        ledger.acquire(picks)
        remaining = [row for row in remaining if row not in set(picks)]
        diagnostics.append(
            RoundDiagnostic(
                round_index=round_index,
                training_rows=len(train_rows),
                fold_models=len(models),
                variance_minimum=float(variance.min()),
                variance_maximum=float(variance.max()),
                picked=len(picks),
            )
        )
    picks = ledger.close()
    if len(picks) != checkpoints[-1] or len(set(picks)) != len(picks):
        raise UncertaintyContractError("acquisition order is incomplete or has a duplicate")
    return picks, tuple(diagnostics)


@dataclass(frozen=True)
class UncertaintyLibrary:
    parent_ids: tuple[str, ...]
    features: NDArray[Any]
    groups: tuple[str, ...]
    targets: NDArray[Any]
    initial: tuple[int, ...]
    pool: tuple[int, ...]
    evaluation: tuple[int, ...]
    checkpoints: tuple[int, ...]


def prepare_uncertainty_campaign(dataset: AssayDataset) -> UncertaintyLibrary:
    """Re-derive the same library and partition `prepare_campaign` uses, without
    computing or depending on its MaxMin or random policies. Deterministic from
    the dataset alone, so this always agrees with `prepare_campaign` on the same
    dataset; `check` in the CLI cross-checks that agreement explicitly rather than
    only asserting it here."""
    records = tuple(sorted(dataset.records, key=lambda record: record.parent_molecule_chembl_id))
    parent_ids = tuple(record.parent_molecule_chembl_id for record in records)
    if (
        not records
        or any(not value for value in parent_ids)
        or len(set(parent_ids)) != len(parent_ids)
        or any(record.assay_chembl_id != dataset.assay_chembl_id for record in records)
    ):
        raise UncertaintyContractError("missing, duplicate, or cross-assay entity")
    targets = np.asarray([record.target_pchembl for record in records], dtype=np.float64)
    if not np.isfinite(targets).all():
        raise UncertaintyContractError("targets must be finite; no additional exclusions")
    features = build_morgan_matrix(records).values
    groups = tuple(scaffold_group_key(record.canonical_smiles) for record in records)
    features.flags.writeable = False
    initial, pool, evaluation = group_partition(groups)
    checkpoints = budget_checkpoints(len(pool))
    return UncertaintyLibrary(
        parent_ids, features, groups, targets, initial, pool, evaluation, checkpoints
    )


def score_uncertainty_policy(library: UncertaintyLibrary, picks: tuple[int, ...]) -> dict[str, Any]:
    """Recovery and scaffold diversity, plus a per-checkpoint evaluation MAE fitted
    on initial-plus-acquired-so-far, in the same shape `score_campaign` reports for
    the six existing policies, so a reader can compare them directly."""
    pool_local = {row: index for index, row in enumerate(library.pool)}
    pool_targets = library.targets[list(library.pool)]
    recovery, auc = recovery_curve(
        pool_targets, tuple(pool_local[row] for row in picks), library.checkpoints
    )
    pool_group_count = len({library.groups[row] for row in library.pool})
    evaluation_targets = library.targets[list(library.evaluation)]
    evaluation_mae = []
    for k in library.checkpoints:
        train_rows = sorted(library.initial + tuple(picks[:k]))
        model = Ridge(**RIDGE_PARAMS)
        model.fit(library.features[train_rows].astype(np.float64), library.targets[train_rows])
        predictions = model.predict(library.features[list(library.evaluation)].astype(np.float64))
        evaluation_mae.append(float(np.mean(np.abs(predictions - evaluation_targets))))
    return {
        "name": "ensemble-variance-uncertainty",
        "recovery": list(recovery),
        "normalized_auc": auc,
        "scaffold_fraction": [
            len({library.groups[row] for row in picks[:k]}) / pool_group_count
            for k in library.checkpoints
        ],
        "evaluation_mae": evaluation_mae,
    }
