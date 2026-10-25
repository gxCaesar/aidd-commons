"""Project the completed uncertainty-campaign metrics into a public teaching summary.

Same discipline as `pool_budget_summary.py`, adapted to one policy instead of six:
explicit field projection, and arithmetic that must close before anything is written.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any


class UncertaintySummaryContractError(ValueError):
    """Incomplete or inconsistent aggregates must not enter the teaching release."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise UncertaintySummaryContractError(message)


def _count(value: Any) -> int:
    _require(type(value) is int and value > 0, "counts must be positive integers")
    return int(value)


def _number(value: Any, *, maximum: float = math.inf) -> float:
    _require(type(value) in (int, float), "metrics must be numbers")
    result = float(value)
    _require(math.isfinite(result) and 0 <= result <= maximum, "metric outside its finite range")
    return result


def _curve(value: Any, *, maximum: float = math.inf) -> list[float]:
    _require(isinstance(value, list) and len(value) == 5, "each curve needs five checkpoints")
    return [_number(item, maximum=maximum) for item in value]


def _close(actual: float, expected: float) -> None:
    _require(abs(actual - expected) < 1e-9, "aggregate arithmetic is inconsistent")


def _assay_summary(source: Any, expected_parents: int, expected_groups: int) -> dict[str, Any]:
    partitions = {
        name: {key: _count(source["partitions"][name][key]) for key in ("parents", "groups")}
        for name in ("initial", "pool", "evaluation")
    }
    _require(
        sum(p["parents"] for p in partitions.values()) == expected_parents, "parent count changed"
    )
    _require(
        sum(p["groups"] for p in partitions.values()) == expected_groups, "group count changed"
    )
    pool = partitions["pool"]["parents"]
    q = pool // 20
    _require(q > 0, "original pool is too small")
    steps = [0, q, 2 * q, 3 * q, 4 * q]
    budget = {
        key: _count(source["budget"][key])
        for key in ("batch_size", "acquired_count", "original_pool_parent_count")
    }
    _require(
        budget == {"batch_size": q, "acquired_count": 4 * q, "original_pool_parent_count": pool},
        "budget does not match the frozen original pool",
    )
    _require(source["budget"]["checkpoints"] == steps, "checkpoint counts changed")
    fraction = _number(source["budget"]["actual_budget_fraction"], maximum=1)
    _close(fraction, 4 * q / pool)
    policy = source["policy"]
    _require(policy["name"] == "ensemble-variance-uncertainty", "unexpected policy name")
    recovery = _curve(policy["recovery"], maximum=1)
    diversity = _curve(policy["scaffold_fraction"], maximum=1)
    for curve in (recovery, diversity):
        _require(
            curve[0] == 0 and all(a <= b for a, b in zip(curve, curve[1:], strict=False)),
            "acquisition curves must start at zero and not decrease",
        )
    auc = _number(policy["normalized_auc"], maximum=1)
    _close(
        auc, sum((a + b) / 2 * q for a, b in zip(recovery, recovery[1:], strict=False)) / (4 * q)
    )
    return {
        "partitions": partitions,
        "budget": {**budget, "checkpoints": steps, "actual_budget_fraction": fraction},
        "policy": {
            "name": policy["name"],
            "recovery": recovery,
            "normalized_auc": auc,
            "scaffold_fraction": diversity,
            "evaluation_mae": _curve(policy["evaluation_mae"]),
        },
    }


def build_public_uncertainty_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    """Explicit field projection: unknown input fields are never copied."""
    try:
        _require(metrics["status"] == "completed", "campaign is not completed")
        _require(
            metrics["protocol_id"] == "chembl37-egfr-pool-budget-uncertainty-v1", "wrong protocol"
        )
        _require(
            set(metrics["assays"]) == {"CHEMBL5736995", "CHEMBL3705421"}, "both assays required"
        )
        completed_on = datetime.fromisoformat(metrics["completed_at"]).date().isoformat()
        software = {
            package: metrics["software"][package]
            for package in ("python", "numpy", "rdkit", "scikit-learn")
        }
        _require(
            all(
                isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+){1,3}", value) is not None
                for value in software.values()
            ),
            "invalid software version",
        )
        assays = {
            assay: _assay_summary(metrics["assays"][assay], parents, groups)
            for assay, parents, groups in (("CHEMBL5736995", 902, 238), ("CHEMBL3705421", 170, 23))
        }
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise UncertaintySummaryContractError(
            f"cannot export completed aggregates: {error}"
        ) from error
    return {
        "schema_version": "aidd-commons.pool-budget-uncertainty-summary.v1",
        "protocol_id": metrics["protocol_id"],
        "completed_on": completed_on,
        "data_kind": "retrospective-assay-replay",
        "software": software,
        "assays": assays,
        "interpretation": [
            "Two retrospective assay replays; no prospective experimental or discovery claim.",
            "Ensemble variance is a ranking signal for acquisition, "
            "not a checked calibrated interval.",
            "Ridge alpha=1 was inherited from the same frozen contract as the completed campaign; "
            "this is not an independently tuned model.",
            "T15 accessed labels shared with T05 before T05 evaluation, as the completed campaign "
            "already discloses; this run inherits that same exposure.",
            "No confidence intervals, p values, or pooled inferential comparisons are reported.",
        ],
    }
