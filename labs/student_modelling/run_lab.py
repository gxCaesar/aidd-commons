"""Standalone, synthetic teaching exercise. No imports from frozen research labs."""

import argparse
import json
import math
import os
from pathlib import Path


def teaching_rows():
    """Authored numbers, not molecules, assay measurements, or a benchmark."""
    values = [
        (0, 1, 0, "train"),
        (1, 3, 0, "train"),
        (2, 5, 0, "train"),
        (3, 7, 1, "train"),
        (4, 9, 1, "train"),
        (5, 11, 1, "train"),
        (1.5, 4, 0, "validation"),
        (3.5, 8, 1, "validation"),
        (6, 10, 1, "test"),
        (7, 9, 0, "test"),
    ]
    return [
        {"entity_id": f"toy-{i + 1:02}", "feature": x, "response": y, "hit": hit, "split": split}
        for i, (x, y, hit, split) in enumerate(values)
    ]


def mean(values):
    return sum(values) / len(values)


def fit_ridge(x, y, alpha):
    """Minimize sum squared error + alpha * slope squared; intercept is free."""
    x_bar, y_bar = mean(x), mean(y)
    denominator = sum((value - x_bar) ** 2 for value in x) + alpha
    slope = (
        sum((a - x_bar) * (b - y_bar) for a, b in zip(x, y, strict=True)) / denominator
        if denominator
        else 0.0
    )
    return y_bar - slope * x_bar, slope


def sigmoid(value):
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1 + exponential)


def fit_logistic(x, y, alpha, steps=500, start=(0.0, 0.0)):
    """Fixed full-batch steps on mean CE + alpha * slope squared / 2.

    The step budget and the starting point are arguments so that the optimiser
    itself can be varied without touching the data, the penalty or the selection
    rule. Defaults reproduce the original fit exactly.
    """
    center = mean(x)
    scale = math.sqrt(mean([(value - center) ** 2 for value in x])) or 1.0
    z = [(value - center) / scale for value in x]
    intercept, slope = start
    for _ in range(steps):
        residuals = [
            sigmoid(intercept + slope * value) - target for value, target in zip(z, y, strict=True)
        ]
        intercept -= 0.1 * mean(residuals)
        slope -= 0.1 * (mean([a * b for a, b in zip(residuals, z, strict=True)]) + alpha * slope)
    return {"intercept": intercept, "slope": slope, "mean": center, "scale": scale}


def predict_logistic(model, x):
    return [
        sigmoid(model["intercept"] + model["slope"] * (value - model["mean"]) / model["scale"])
        for value in x
    ]


def log_loss(y, probabilities):
    clipped = [min(max(value, 1e-15), 1 - 1e-15) for value in probabilities]
    return -mean(
        [
            target * math.log(p) + (1 - target) * math.log1p(-p)
            for target, p in zip(y, clipped, strict=True)
        ]
    )


def classification_metrics(y, probabilities):
    pairs = list(zip(y, [p >= 0.5 for p in probabilities], strict=True))
    tp = sum(target == 1 and prediction for target, prediction in pairs)
    tn = sum(target == 0 and not prediction for target, prediction in pairs)
    fp = sum(target == 0 and prediction for target, prediction in pairs)
    fn = sum(target == 1 and not prediction for target, prediction in pairs)
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": (tp + tn) / len(y),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
    }


def fit_stump(x, y, min_leaf):
    """Pick the training split that minimises squared error, both sides at least min_leaf.

    This is the smallest member of the tree family: one threshold, two constants.
    It shares nothing with the linear family except the records it is given, which
    is what makes the comparison a comparison of assumptions rather than of tuning.
    """
    order = sorted(zip(x, y, strict=True))
    thresholds = sorted({(a[0] + b[0]) / 2 for a, b in zip(order, order[1:], strict=False)})
    best = None
    for threshold in thresholds:
        left = [value for feature, value in order if feature < threshold]
        right = [value for feature, value in order if feature >= threshold]
        if len(left) < min_leaf or len(right) < min_leaf:
            continue
        left_mean, right_mean = mean(left), mean(right)
        error = sum((value - left_mean) ** 2 for value in left) + sum(
            (value - right_mean) ** 2 for value in right
        )
        if best is None or error < best[0]:
            best = (error, threshold, left_mean, right_mean)
    if best is None:
        # No admissible split: the family degenerates to the constant it contains.
        return None, mean(y), mean(y)
    return best[1], best[2], best[3]


def predict_stump(model, x):
    threshold, left, right = model
    if threshold is None:
        return [left] * len(x)
    return [left if value < threshold else right for value in x]


def regression_metrics(y, predictions):
    errors = [prediction - target for target, prediction in zip(y, predictions, strict=True)]
    return {
        "mae": mean([abs(value) for value in errors]),
        "rmse": math.sqrt(mean([value**2 for value in errors])),
    }


def run(rows):
    """Split first. Fit train only; select on validation; score test only afterward."""
    if not rows or len({row["entity_id"] for row in rows}) != len(rows):
        raise ValueError("Entity IDs must be unique across all partitions")
    partitions = {name: [] for name in ("train", "validation", "test")}
    for row in rows:
        if row["split"] not in partitions:
            raise ValueError("Unknown partition")
        if not all(math.isfinite(row[key]) for key in ("feature", "response", "hit")):
            raise ValueError("Features and labels must be finite")
        if row["hit"] not in (0, 1):
            raise ValueError("The constructed hit target must be binary")
        partitions[row["split"]].append(row)
    if any(not values for values in partitions.values()):
        raise ValueError("Each partition must contain records")
    train, validation, test = (partitions[name] for name in ("train", "validation", "test"))
    x = [row["feature"] for row in train]
    y = [row["response"] for row in train]
    hits = [row["hit"] for row in train]
    validation_x = [row["feature"] for row in validation]
    candidates, validation_scores = {}, []
    for alpha in (0.0, 1.0, 10.0):
        regression = fit_ridge(x, y, alpha)
        classification = fit_logistic(x, hits, alpha)
        candidates[str(alpha)] = {"regression": regression, "classification": classification}
        predictions = [regression[0] + regression[1] * value for value in validation_x]
        validation_scores.append(
            {
                "alpha": alpha,
                "regression_mae": regression_metrics(
                    [row["response"] for row in validation],
                    predictions,
                )["mae"],
                "classification_log_loss": log_loss(
                    [row["hit"] for row in validation],
                    predict_logistic(classification, validation_x),
                ),
            }
        )
    stump_candidates, stump_validation_scores = {}, []
    for min_leaf in (1, 2, 3):
        stump = fit_stump(x, y, min_leaf)
        stump_candidates[str(min_leaf)] = stump
        stump_validation_scores.append(
            {
                "min_leaf": min_leaf,
                "regression_mae": regression_metrics(
                    [row["response"] for row in validation],
                    predict_stump(stump, validation_x),
                )["mae"],
                "split_threshold": stump[0],
            }
        )
    # Tuple ordering fixes ties in favor of the lower alpha; no test target is used here.
    regression_alpha = min(
        validation_scores, key=lambda row: (row["regression_mae"], row["alpha"])
    )["alpha"]
    classification_alpha = min(
        validation_scores, key=lambda row: (row["classification_log_loss"], row["alpha"])
    )["alpha"]
    regression = candidates[str(regression_alpha)]["regression"]
    classification = candidates[str(classification_alpha)]["classification"]
    # The same rule, applied to the other family: lowest validation MAE, ties to the
    # less constrained candidate. Only the assumption set differs.
    stump_min_leaf = min(
        stump_validation_scores, key=lambda row: (row["regression_mae"], row["min_leaf"])
    )["min_leaf"]
    stump = stump_candidates[str(stump_min_leaf)]
    # With the configuration chosen, vary only the optimiser. Three declared
    # starting points and three step budgets, no randomness and no new data, so
    # every difference below is the search and not the records.
    optimisation_variability = []
    for steps in (50, 200, 500):
        for start in ((0.0, 0.0), (-2.0, 1.0), (2.0, -1.0)):
            attempt = fit_logistic(x, hits, classification_alpha, steps=steps, start=start)
            validation_probabilities = predict_logistic(attempt, validation_x)
            optimisation_variability.append(
                {
                    "steps": steps,
                    "start": list(start),
                    "gradient_evaluations": steps * len(train),
                    "train_log_loss": log_loss(hits, predict_logistic(attempt, x)),
                    "validation_probabilities": validation_probabilities,
                    "validation_decisions": [
                        int(probability >= 0.5) for probability in validation_probabilities
                    ],
                }
            )
    budget_summary = []
    for steps in (50, 200, 500):
        attempts = [row for row in optimisation_variability if row["steps"] == steps]
        decisions = {tuple(row["validation_decisions"]) for row in attempts}
        spreads = [
            max(column) - min(column)
            for column in zip(*(row["validation_probabilities"] for row in attempts), strict=True)
        ]
        budget_summary.append(
            {
                "steps": steps,
                "gradient_evaluations": attempts[0]["gradient_evaluations"],
                "starting_points": len(attempts),
                "decisions_agree": len(decisions) == 1,
                "largest_probability_spread": max(spreads),
            }
        )
    test_x = [row["feature"] for row in test]
    predictions = [regression[0] + regression[1] * value for value in test_x]
    stump_predictions = predict_stump(stump, test_x)
    probabilities = predict_logistic(classification, test_x)
    targets = [row["response"] for row in test]
    test_hits = [row["hit"] for row in test]
    return {
        "data_kind": "synthetic-teaching-example",
        "claim": "Training mechanics only; not QSAR performance or biological evidence",
        "counts": {name: len(values) for name, values in partitions.items()},
        "selection": {
            "regression_alpha": regression_alpha,
            "stump_min_leaf": stump_min_leaf,
            "classification_alpha": classification_alpha,
            "classification_threshold": 0.5,
            "refit_with_validation": False,
        },
        "validation_scores": validation_scores,
        "stump_validation_scores": stump_validation_scores,
        "optimisation_variability": optimisation_variability,
        "budget_summary": budget_summary,
        "candidate_models": candidates,
        "models": {
            "regression": regression,
            "classification": classification,
            "stump": stump,
            "train_mean": mean(y),
            "train_prevalence": mean(hits),
        },
        "test_metrics": {
            "ridge": regression_metrics(targets, predictions),
            "stump": regression_metrics(targets, stump_predictions),
            "train_mean": regression_metrics(targets, [mean(y)] * len(test)),
            "logistic": {
                **classification_metrics(test_hits, probabilities),
                "log_loss": log_loss(test_hits, probabilities),
            },
            "train_prevalence": {
                **classification_metrics(test_hits, [mean(hits)] * len(test)),
                "log_loss": log_loss(test_hits, [mean(hits)] * len(test)),
            },
        },
        "test_predictions": [
            {
                **row,
                "prediction": prediction,
                "residual": prediction - row["response"],
                "hit_probability": probability,
            }
            for row, prediction, probability in zip(test, predictions, probabilities, strict=True)
        ],
    }


def _open_output_parent(root, parts):
    """Open or create output directories from a POSIX no-follow filesystem anchor."""
    if (
        os.name != "posix"
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or os.open not in os.supports_dir_fd
        or os.mkdir not in os.supports_dir_fd
    ):
        raise OSError(
            "Secure student output writing requires macOS/Linux POSIX no-follow APIs; "
            "use the browser reference output on this platform"
        )
    root = Path(root)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current_fd = os.open(root.anchor, directory_flags)
    try:
        for part in (*root.parts[1:], *parts):
            try:
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            except FileNotFoundError:
                os.mkdir(part, dir_fd=current_fd)
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            old_fd, current_fd = current_fd, None
            try:
                os.close(old_fd)
            except BaseException:
                os.close(next_fd)
                raise
            current_fd = next_fd
        parent_fd, current_fd = current_fd, None
        return parent_fd
    finally:
        if current_fd is not None:
            os.close(current_fd)


def write_report(report, destination, root):
    """Only create a new file inside the student output tree; never follow links."""
    root, destination = Path(root).absolute(), Path(destination).absolute()
    if ".." in destination.parts or not destination.is_relative_to(root):
        raise ValueError("Output must remain inside the student sandbox")
    for path in (destination, *destination.parents):
        if path.is_symlink():
            raise ValueError("Symlink output paths are not permitted")
    relative_destination = destination.relative_to(root)
    parent_fd = _open_output_parent(root, relative_destination.parent.parts)
    file_fd = None
    try:
        file_fd = os.open(
            relative_destination.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o666,
            dir_fd=parent_fd,
        )
        with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
            file_fd = None
            json.dump(report, handle, indent=2, allow_nan=False)
            handle.write("\n")
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent_fd)


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="tmp/student-modelling/report.json",
        help="Fresh JSON path under tmp/student-modelling, relative to repository root",
    )
    args = parser.parse_args()
    destination = root / args.output
    try:
        write_report(run(teaching_rows()), destination, root / "tmp" / "student-modelling")
    except (ValueError, OSError) as error:
        parser.exit(2, f"Student lab failed: {error}\n")
    print(f"Synthetic student report written: {destination}")
    print("No real assay data, frozen results, network requests or GPU were used.")


if __name__ == "__main__":
    main()
