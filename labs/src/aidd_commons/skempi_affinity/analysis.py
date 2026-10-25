"""Count independent units, expose row leakage, and score two fixed comparators."""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from .data import Dataset, Record
from .protocol import SEED


class AnalysisContractError(ValueError):
    """A split or input count violates the declared evaluation unit."""


@dataclass(frozen=True)
class Split:
    train: tuple[Record, ...]
    test: tuple[Record, ...]


def complex_split(rows: tuple[Record, ...]) -> Split:
    complexes = sorted({row.complex_id for row in rows})
    if len(complexes) < 2:
        raise AnalysisContractError("complex holdout needs two or more complexes")
    random.Random(SEED).shuffle(complexes)
    test_n = math.ceil(len(complexes) * 0.2)
    test_ids = set(complexes[:test_n])
    return Split(
        tuple(row for row in rows if row.complex_id not in test_ids),
        tuple(row for row in rows if row.complex_id in test_ids),
    )


def row_split_leakage(rows: tuple[Record, ...]) -> dict[str, int]:
    indices = list(range(len(rows)))
    random.Random(SEED).shuffle(indices)
    test_n = math.ceil(len(rows) * 0.2)
    test_indices = set(indices[:test_n])
    train_complexes = {
        row.complex_id for index, row in enumerate(rows) if index not in test_indices
    }
    leaked_test_rows = sum(
        row.complex_id in train_complexes
        for index, row in enumerate(rows)
        if index in test_indices
    )
    return {"test_rows": test_n, "leaked_test_rows": leaked_test_rows}


def _metrics(actual: list[float], predicted: list[float], groups: list[str]) -> dict[str, float]:
    errors = [abs(a - p) for a, p in zip(actual, predicted, strict=True)]
    by_complex: dict[str, list[float]] = defaultdict(list)
    for group, error in zip(groups, errors, strict=True):
        by_complex[group].append(error)
    return {
        "row_mae_log10_m": statistics.mean(errors),
        "complex_mean_mae_log10_m": statistics.mean(
            statistics.mean(values) for values in by_complex.values()
        ),
    }


def evaluate(split: Split) -> dict[str, Any]:
    if not split.train or not split.test:
        raise AnalysisContractError("empty train or test partition")
    train_ids = {row.complex_id for row in split.train}
    test_ids = {row.complex_id for row in split.test}
    if train_ids & test_ids:
        raise AnalysisContractError("complex appears in both partitions")
    if not all(row.complete for row in (*split.train, *split.test)):
        raise AnalysisContractError("evaluation contains incomplete affinity pair")
    by_group: dict[str, list[float]] = defaultdict(list)
    train_targets: list[float] = []
    for row in split.train:
        assert row.wild_type_m is not None
        target = math.log10(row.wild_type_m)
        by_group[row.protein_group].append(target)
        train_targets.append(target)
    global_median = statistics.median(train_targets)
    group_medians = {key: statistics.median(values) for key, values in by_group.items()}
    actual: list[float] = []
    group_predictions: list[float] = []
    mutant_predictions: list[float] = []
    ids: list[str] = []
    for row in split.test:
        assert row.wild_type_m is not None and row.mutant_m is not None
        actual.append(math.log10(row.wild_type_m))
        group_predictions.append(group_medians.get(row.protein_group, global_median))
        mutant_predictions.append(math.log10(row.mutant_m))
        ids.append(row.complex_id)
    return {
        "train_rows": len(split.train),
        "train_complexes": len(train_ids),
        "test_rows": len(split.test),
        "test_complexes": len(test_ids),
        "group_only": _metrics(actual, group_predictions, ids),
        "observed_mutant": _metrics(actual, mutant_predictions, ids),
    }


def analyze(dataset: Dataset) -> dict[str, Any]:
    rows = dataset.records
    by_class: dict[str, list[Record]] = defaultdict(list)
    for row in rows:
        by_class[row.interaction_class].append(row)
    classes: dict[str, dict[str, Any]] = {}
    for interaction_class, group in sorted(by_class.items()):
        complexes = Counter(row.complex_id for row in group)
        top = complexes.most_common(5)
        top_count = sum(count for _, count in top)
        classes[interaction_class] = {
            "rows": len(group),
            "complexes": len(complexes),
            "complete_pairs": sum(row.complete for row in group),
            "protein_groups": len({row.protein_group for row in group}),
            "top_five_rows": top_count,
            "top_five_share": top_count / len(group),
            "top_five_complexes": [name for name, _ in top],
        }
    eligible = tuple(row for row in rows if row.interaction_class == "AB/AG" and row.complete)
    if len(eligible) < 2:
        raise AnalysisContractError("insufficient complete AB/AG rows")
    split = complex_split(eligible)
    return {
        "rows": len(rows),
        "complexes": len({row.complex_id for row in rows}),
        "complete_pairs": sum(row.complete for row in rows),
        "fragmented_rows": dataset.fragmented_rows,
        "field_counts": {str(k): v for k, v in dataset.field_counts.items()},
        "classes": classes,
        "eligible_rows": len(eligible),
        "row_split_diagnostic": row_split_leakage(eligible),
        "complex_holdout": evaluate(split),
    }


def check_invariants(dataset: Dataset, result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    rows = dataset.records
    classes = result["classes"]
    if sum(dataset.field_counts.values()) != len(rows):
        failures.append("field counts do not cover rows")
    if sum(item["rows"] for item in classes.values()) != len(rows):
        failures.append("interaction classes do not cover rows")
    if sum(item["complete_pairs"] for item in classes.values()) != result["complete_pairs"]:
        failures.append("class completeness does not cover complete pairs")
    for name, item in classes.items():
        if item["complete_pairs"] > item["rows"] or item["top_five_rows"] > item["rows"]:
            failures.append(f"class count invalid: {name}")
    eligible = tuple(row for row in rows if row.interaction_class == "AB/AG" and row.complete)
    split = complex_split(eligible)
    if {row.complex_id for row in split.train} & {row.complex_id for row in split.test}:
        failures.append("complex holdout leaks")
    if len(split.train) + len(split.test) != len(eligible):
        failures.append("complex holdout omits rows")
    diagnostic = result["row_split_diagnostic"]
    if diagnostic["leaked_test_rows"] > diagnostic["test_rows"]:
        failures.append("row leakage count invalid")
    return failures
