"""Project completed aggregate metrics into a public, compound-free teaching summary.

This module never imports the campaign, fits a model, or opens source assay data.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any


class SummaryContractError(ValueError):
    """Incomplete or inconsistent aggregates must not enter the teaching release."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SummaryContractError(message)


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
    _require(abs(actual - expected) < 1e-12, "aggregate arithmetic is inconsistent")


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
    _require(
        all(p["groups"] <= p["parents"] for p in partitions.values()), "more groups than parents"
    )
    pool = partitions["pool"]["parents"]
    q = pool // 20
    _require(q > 0, "original pool is too small")
    steps = [0, q, 2 * q, 3 * q, 4 * q]
    budget = {
        key: _count(source["budget"][key])
        for key in ("batch_size", "acquired_count", "original_pool_parent_count", "top_decile_size")
    }
    _require(
        budget
        == {
            "batch_size": q,
            "acquired_count": 4 * q,
            "original_pool_parent_count": pool,
            "top_decile_size": math.ceil(pool / 10),
        },
        "budget does not match the frozen original pool",
    )
    _require(source["budget"]["checkpoints"] == steps, "checkpoint counts changed")
    fraction = _number(source["budget"]["actual_budget_fraction"], maximum=1)
    _close(fraction, 4 * q / pool)
    budget_output = {**budget, "checkpoints": steps, "actual_budget_fraction": fraction}
    policies = source["policies"]
    names = ["maxmin", "random-0", "random-1", "random-2", "random-3", "random-4"]
    _require(
        isinstance(policies, list) and [p["name"] for p in policies] == names,
        "all six policy instances must appear in frozen order",
    )
    output = []
    for policy in policies:
        recovery = _curve(policy["recovery"], maximum=1)
        diversity = _curve(policy["scaffold_fraction"], maximum=1)
        for curve in (recovery, diversity):
            _require(
                curve[0] == 0 and all(a <= b for a, b in zip(curve, curve[1:], strict=False)),
                "acquisition curves must start at zero and not decrease",
            )
        for index, k in enumerate(steps):
            _require(
                recovery[index] * budget["top_decile_size"] <= k + 1e-12,
                "recovered more targets than acquired parents",
            )
            _require(
                diversity[index] * partitions["pool"]["groups"] <= k + 1e-12,
                "covered more scaffold groups than acquired parents",
            )
        auc = _number(policy["normalized_auc"], maximum=1)
        _close(
            auc,
            sum((a + b) / 2 * q for a, b in zip(recovery, recovery[1:], strict=False)) / (4 * q),
        )
        output.append(
            {
                "name": policy["name"],
                "recovery": recovery,
                "normalized_auc": auc,
                "scaffold_fraction": diversity,
                "evaluation_mae": _curve(policy["evaluation_mae"]),
            }
        )
    return {"partitions": partitions, "budget": budget_output, "policies": output}


def build_public_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    """Explicit field projection: unknown input fields are never copied."""
    try:
        _require(metrics["status"] == "completed", "campaign is not completed")
        _require(metrics["protocol_id"] == "chembl37-egfr-pool-budget-v1", "wrong protocol")
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
        raise SummaryContractError(f"cannot export completed aggregates: {error}") from error
    return {
        "schema_version": "aidd-commons.pool-budget-real-summary.v1",
        "protocol_id": metrics["protocol_id"],
        "completed_on": completed_on,
        "data_kind": "retrospective-assay-replay",
        "software": software,
        "assays": assays,
        "interpretation": [
            "Two retrospective assay replays; no prospective experimental or discovery claim.",
            "Random seeds are fixed policy instances, not independent biological replicates.",
            "Ridge alpha=1 was informed by T05 development; "
            "this is not independent corroboration of T05.",
            "T15 accessed labels shared with T05 before T05 evaluation; "
            "the separate T05 and T11 evaluations have since completed without retuning.",
            "No confidence intervals, p values, or pooled inferential comparisons are reported.",
        ],
    }
