"""Cross-modality agreement, and what plate and batch structure do to it.

The question this module answers is operational rather than rhetorical: for
a perturbation measured in both readouts, does the transcriptomic profile
predict the imaging profile, and does that prediction survive an evaluation
that keeps the experimental design from leaking?

Everything here is a pure function over the entities assembled by
`data.load_cached_dataset`. Nothing fetches, nothing caches and nothing
refits an already-frozen result. The evaluation set is fixed by
`protocol.py`: the seed, the fold counts and the ridge penalty grid are
constants, and the penalty is selected inside each training fold, so no
held-out row ever influences its own penalty.

The evaluations, in the order the lab reports them:

``apparent``
    A random five-fold split over perturbations. This is the number an
    analysis that ignores the design reports, and the number every other
    evaluation is read against.
``size_matched_random``
    A random split with the same training and test sizes as a blocked
    evaluation, drawn from the same population. It separates "there was
    less training data" from "the structure the test set needed was not
    available".
``batch_blocked``
    Every perturbation of one batch is held out, and the training side is
    the other batch. Perturbations measured in both batches are excluded
    from the evaluation rather than assigned to either.
``plate_blocked``
    Every perturbation measured on one imaging assay plate is held out, and
    the training side is every perturbation never measured on that plate.
``null_within_batch_permuted``
    The apparent split, with each perturbation's imaging profile replaced by
    another perturbation's imaging profile from the same batch. Plate and
    batch structure are preserved and the pairing between the two readouts
    is destroyed, so this is the agreement the design alone can produce.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


class AnalysisContractError(ValueError):
    """Raised when an analysis input does not meet its declared shape."""


@dataclass(frozen=True)
class RidgeMap:
    """A fitted ridge map from one readout's profile space to the other's."""

    mean: NDArray[np.float64]
    scale: NDArray[np.float64]
    weights: NDArray[np.float64]
    intercept: NDArray[np.float64]
    alpha: float


@dataclass(frozen=True)
class Fold:
    """One evaluation fold: which entities are training rows and which are
    held out."""

    train: NDArray[np.int64]
    test: NDArray[np.int64]


@dataclass(frozen=True)
class SplitResult:
    """What one evaluation produced."""

    name: str
    folds: int
    tested_perturbations: int
    perturbation_r: float
    feature_r: float
    train_sizes: tuple[int, ...]
    test_sizes: tuple[int, ...]
    alphas: tuple[float, ...]
    per_perturbation_r: NDArray[np.float64]


def fit_ridge(
    x: NDArray[np.float64], y: NDArray[np.float64], alpha: float
) -> RidgeMap:
    """Fit a multi-output ridge map with the training rows standardised.

    The standardisation uses the training rows only, so a held-out row's
    own scale never enters the map.
    """
    if x.ndim != 2 or y.ndim != 2:
        raise AnalysisContractError("ridge inputs must be two-dimensional")
    if x.shape[0] != y.shape[0]:
        raise AnalysisContractError("ridge inputs must have the same number of rows")
    if x.shape[0] < 2:
        raise AnalysisContractError("a ridge map needs at least two training rows")
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale = np.where(scale > 0, scale, 1.0)
    design = (x - mean) / scale
    target_mean = y.mean(axis=0)
    gram = design.T @ design + alpha * np.eye(design.shape[1])
    weights = np.linalg.solve(gram, design.T @ (y - target_mean))
    return RidgeMap(
        mean=mean,
        scale=scale,
        weights=weights,
        intercept=target_mean,
        alpha=alpha,
    )


def predict(model: RidgeMap, x: NDArray[np.float64]) -> NDArray[np.float64]:
    """Apply a fitted ridge map to new rows."""
    return ((x - model.mean) / model.scale) @ model.weights + model.intercept


def _correlate_rows(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
    """Row-wise Pearson correlation between two equally shaped matrices."""
    a_centred = a - a.mean(axis=1, keepdims=True)
    b_centred = b - b.mean(axis=1, keepdims=True)
    numerator = np.sum(a_centred * b_centred, axis=1)
    denominator = np.linalg.norm(a_centred, axis=1) * np.linalg.norm(b_centred, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        correlation = np.where(denominator > 0, numerator / denominator, np.nan)
    return correlation


def _correlate_columns(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
    """Column-wise Pearson correlation between two equally shaped matrices."""
    a_centred = a - a.mean(axis=0, keepdims=True)
    b_centred = b - b.mean(axis=0, keepdims=True)
    numerator = np.sum(a_centred * b_centred, axis=0)
    denominator = np.linalg.norm(a_centred, axis=0) * np.linalg.norm(b_centred, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        correlation = np.where(denominator > 0, numerator / denominator, np.nan)
    return correlation


def random_folds(count: int, folds: int, seed: int) -> tuple[Fold, ...]:
    """A random partition of `count` entities into `folds` folds."""
    if count < folds:
        raise AnalysisContractError("more folds than entities")
    order = np.random.RandomState(seed).permutation(count)
    chunks = np.array_split(order, folds)
    everything = np.arange(count)
    return tuple(
        Fold(train=np.setdiff1d(everything, test), test=test) for test in chunks
    )


def size_matched_random_folds(
    pool: NDArray[np.int64], sizes: tuple[tuple[int, int], ...], seed: int
) -> tuple[Fold, ...]:
    """Random folds with the same training and test sizes as a blocked
    evaluation, drawn from the same population.

    This is the control that separates a design effect from a sample-size
    effect: a blocked fold that performs like a random fold of the same size
    was hurt by having less training data, not by the structure it hid.
    """
    folds: list[Fold] = []
    for offset, (train_size, test_size) in enumerate(sizes):
        order = np.random.RandomState(seed + offset).permutation(len(pool))
        test = pool[order[:test_size]]
        train = pool[order[test_size : test_size + train_size]]
        folds.append(Fold(train=np.sort(train), test=np.sort(test)))
    return tuple(folds)


def size_matched_partition_folds(
    pool: NDArray[np.int64], sizes: tuple[tuple[int, int], ...], seed: int
) -> tuple[Fold, ...]:
    """Random folds that mirror a leave-one-group-out evaluation exactly.

    The pool is split into disjoint test groups of the same sizes as the
    blocked evaluation's test groups, and each fold trains on the other
    group. The population, the fold count, the training sizes, the test
    sizes and the coverage are the same as the blocked evaluation; only the
    grouping is random instead of structural.
    """
    order = np.random.RandomState(seed).permutation(len(pool))
    groups: list[NDArray[np.int64]] = []
    cursor = 0
    for _, test_size in sizes:
        groups.append(pool[order[cursor : cursor + test_size]])
        cursor += test_size
    folds: list[Fold] = []
    for index, (train_size, _) in enumerate(sizes):
        test = groups[index]
        others = np.concatenate([group for other, group in enumerate(groups) if other != index])
        folds.append(Fold(train=np.sort(others[:train_size]), test=np.sort(test)))
    return tuple(folds)


def batch_blocked_folds(
    batches: tuple[str | None, ...], batch_names: tuple[str, ...]
) -> tuple[Fold, ...]:
    """Leave one batch out entirely.

    A perturbation measured in more than one batch is excluded from the
    evaluation rather than assigned to one of them: putting it on the
    training side would put the held-out batch's plates in the training set,
    and putting it on the test side would put another batch's plates in the
    test set.
    """
    folds: list[Fold] = []
    for name in batch_names:
        others = [other for other in batch_names if other != name]
        test = np.array(
            [index for index, batch in enumerate(batches) if batch == name], dtype=np.int64
        )
        train = np.array(
            [index for index, batch in enumerate(batches) if batch in others], dtype=np.int64
        )
        folds.append(Fold(train=train, test=test))
    return tuple(folds)


def plate_blocked_folds(
    membership: tuple[frozenset[str], ...], plates: tuple[str, ...]
) -> tuple[Fold, ...]:
    """Hold out every entity measured on one imaging assay plate.

    The training side is every entity never measured on that plate, so the
    held-out plate's own offset is absent from the training data.
    """
    folds: list[Fold] = []
    for plate in plates:
        test = np.array(
            [index for index, plates_of in enumerate(membership) if plate in plates_of],
            dtype=np.int64,
        )
        train = np.array(
            [index for index, plates_of in enumerate(membership) if plate not in plates_of],
            dtype=np.int64,
        )
        folds.append(Fold(train=train, test=test))
    return tuple(folds)


def select_alpha(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    alphas: tuple[float, ...],
    inner_folds: int,
    seed: int,
) -> float:
    """Choose the ridge penalty by an inner cross-validation on the training
    rows only.

    The criterion is the mean per-feature correlation between the predicted
    and the observed imaging profile across the held-out inner rows, the
    same quantity the outer evaluation reports.
    """
    count = x.shape[0]
    if not alphas:
        raise AnalysisContractError("the penalty grid is empty")
    if count < inner_folds + 1:
        raise AnalysisContractError("too few training rows to select a penalty")
    inner = random_folds(count, inner_folds, seed)
    best_alpha = alphas[0]
    best_score = -np.inf
    for alpha in alphas:
        scores = []
        for fold in inner:
            model = fit_ridge(x[fold.train], y[fold.train], alpha)
            predicted = predict(model, x[fold.test])
            observed = y[fold.test]
            correlations = _correlate_columns(predicted, observed)
            scores.append(float(np.nanmean(correlations)))
        score = float(np.mean(scores))
        if score > best_score:
            best_score = score
            best_alpha = alpha
    return best_alpha


def evaluate(
    name: str,
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    folds: tuple[Fold, ...],
    alphas: tuple[float, ...],
    inner_folds: int,
    seed: int,
) -> SplitResult:
    """Run one evaluation and report both agreement statistics.

    `perturbation_r` is the mean over held-out entities of the correlation
    between the predicted and the observed imaging profile. `feature_r` is
    the mean over imaging features of the correlation between predicted and
    observed values across the held-out entities of a fold, averaged over
    folds.
    """
    if not folds:
        raise AnalysisContractError("an evaluation needs at least one fold")
    for fold in folds:
        if np.intersect1d(fold.train, fold.test).size:
            raise AnalysisContractError(
                f"{name}: a fold puts the same entity on both the training and the test side"
            )
    per_perturbation = np.full(x.shape[0], np.nan)
    feature_scores: list[float] = []
    selected_alphas: list[float] = []
    for fold in folds:
        if fold.test.size == 0:
            continue
        alpha = select_alpha(x[fold.train], y[fold.train], alphas, inner_folds, seed)
        selected_alphas.append(alpha)
        model = fit_ridge(x[fold.train], y[fold.train], alpha)
        predicted = predict(model, x[fold.test])
        observed = y[fold.test]
        per_perturbation[fold.test] = _correlate_rows(predicted, observed)
        feature_scores.append(float(np.nanmean(_correlate_columns(predicted, observed))))
    if not feature_scores:
        raise AnalysisContractError("an evaluation needs at least one non-empty fold")
    if not np.isfinite(feature_scores).all() or not np.isfinite(
        float(np.nanmean(per_perturbation))
    ):
        raise AnalysisContractError(
            f"{name}: the evaluation produced a non-finite agreement, so it cannot be reported"
        )
    return SplitResult(
        name=name,
        folds=len(folds),
        tested_perturbations=int(np.count_nonzero(~np.isnan(per_perturbation))),
        perturbation_r=float(np.nanmean(per_perturbation)),
        feature_r=float(np.mean(feature_scores)),
        train_sizes=tuple(int(fold.train.size) for fold in folds),
        test_sizes=tuple(int(fold.test.size) for fold in folds),
        alphas=tuple(selected_alphas),
        per_perturbation_r=per_perturbation,
    )


def permute_within_group(
    y: NDArray[np.float64], groups: tuple[str | None, ...], seed: int
) -> NDArray[np.float64]:
    """Replace each row's imaging profile with another row's from the same
    group, keeping the group sizes.

    The pairing between the two readouts is destroyed while the plate and
    batch structure is left in place, so the result is the agreement the
    design alone can produce.
    """
    permuted = np.array(y, dtype=np.float64, copy=True)
    state = np.random.RandomState(seed)
    unique = sorted({group for group in groups if group is not None})
    for group in unique:
        members = np.array([index for index, value in enumerate(groups) if value == group])
        order = state.permutation(len(members))
        permuted[members] = y[members[order]]
    return permuted


def neighbourhood_concordance(
    x: NDArray[np.float64], y: NDArray[np.float64]
) -> float:
    """A model-free cross-modality agreement statistic.

    For every entity, the two readouts rank all the other entities by
    similarity. The Spearman correlation between the two rankings measures
    whether the two readouts put the same neighbours around the same
    entity. No model is fitted and no split is drawn, so this is an
    independent check on the fitted evaluations rather than a substitute
    for them.
    """
    if x.shape[0] != y.shape[0]:
        raise AnalysisContractError("concordance needs the same entities in both readouts")
    x_ranks = _rank_rows(_similarity(x))
    y_ranks = _rank_rows(_similarity(y))
    values: list[float] = []
    for index in range(x.shape[0]):
        keep = np.ones(x.shape[0], dtype=bool)
        keep[index] = False
        values.append(
            float(_pearson(x_ranks[index][keep], y_ranks[index][keep]))
        )
    return float(np.nanmedian(values))


def _rank_rows(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Rank every row of a matrix, averaging the ranks of tied values.

    This is the ranking a rank correlation needs, and it is written here
    rather than imported so that this lab depends on NumPy alone.
    """
    rows, columns = matrix.shape
    order = np.argsort(matrix, axis=1, kind="mergesort")
    sorted_values = np.take_along_axis(matrix, order, axis=1)
    new_group = np.ones((rows, columns), dtype=bool)
    new_group[:, 1:] = sorted_values[:, 1:] != sorted_values[:, :-1]
    group = np.cumsum(new_group, axis=1) - 1
    rows_index = np.arange(rows)[:, None]
    counts = np.zeros((rows, columns), dtype=np.float64)
    np.add.at(counts, (rows_index, group), 1.0)
    positions = np.broadcast_to(
        np.arange(1, columns + 1, dtype=np.float64), (rows, columns)
    )
    sums = np.zeros((rows, columns), dtype=np.float64)
    np.add.at(sums, (rows_index, group), positions)
    averages = np.where(counts > 0, sums / np.where(counts > 0, counts, 1.0), 0.0)
    ranks_sorted = np.take_along_axis(averages, group, axis=1)
    ranks = np.empty_like(ranks_sorted)
    np.put_along_axis(ranks, order, ranks_sorted, axis=1)
    return ranks


def _pearson(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    """Pearson correlation of two equally long vectors."""
    a_centred = a - a.mean()
    b_centred = b - b.mean()
    denominator = float(np.linalg.norm(a_centred) * np.linalg.norm(b_centred))
    if denominator <= 0:
        return float("nan")
    return float(np.sum(a_centred * b_centred) / denominator)


def _similarity(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Row-wise correlation between every pair of rows of a matrix."""
    centred = matrix - matrix.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(centred, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    unit = centred / norms
    similarity: NDArray[np.float64] = unit @ unit.T
    return similarity


def variance_shares(
    values: NDArray[np.float64], groups: tuple[str, ...]
) -> dict[str, float]:
    """Share of the total feature variance attributable to the group means.

    `between` is the share explained by differences between group means,
    `within` is the share left inside the groups. The two sum to one.
    """
    if values.shape[0] != len(groups):
        raise AnalysisContractError("every row needs a group")
    grand = values.mean(axis=0)
    total = float(np.mean(np.sum((values - grand) ** 2, axis=0)))
    between = 0.0
    within = 0.0
    for group in sorted(set(groups)):
        members = values[[index for index, value in enumerate(groups) if value == group]]
        group_mean = members.mean(axis=0)
        between += members.shape[0] * float(np.sum((group_mean - grand) ** 2))
        within += float(np.sum((members - group_mean) ** 2))
    between /= values.shape[1]
    within /= values.shape[1]
    if total <= 0:
        raise AnalysisContractError("the values carry no variance to decompose")
    return {
        "between": between / total,
        "within": within / total,
        "total_mean_square": total,
    }
