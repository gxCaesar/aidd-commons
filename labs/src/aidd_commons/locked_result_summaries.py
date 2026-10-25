"""Aggregate-only teaching projections; never import a pipeline or fit a model."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any, Literal


class SummaryContractError(ValueError):
    """Incomplete or inconsistent scores must not enter a teaching release."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SummaryContractError(message)


def _number(value: Any, *, minimum: float = 0, maximum: float = math.inf) -> float:
    _require(type(value) in (int, float), "metric must be numeric")
    number = float(value)
    _require(math.isfinite(number) and minimum <= number <= maximum, "metric outside finite range")
    return number


def _scores(value: Mapping[str, Any]) -> dict[str, float]:
    result = {key: _number(value[key]) for key in ("mae", "rmse")}
    _require(result["rmse"] >= result["mae"], "RMSE cannot be below MAE")
    return result


def _base(
    source: Mapping[str, Any], *, protocol_id: str, reviewed_on: str, chembl: bool
) -> dict[str, Any]:
    _require(date.fromisoformat(reviewed_on).isoformat() == reviewed_on, "invalid review date")
    packages = (
        ("python", "numpy", "scikit_learn", "rdkit")
        if chembl
        else ("python", "numpy", "scikit_learn")
    )
    software = {name: source["software"][name] for name in packages}
    _require(
        all(
            isinstance(v, str) and re.fullmatch(r"\d+(?:\.\d+){1,3}", v) for v in software.values()
        ),
        "invalid software version",
    )
    return {
        "schema_version": f"aidd-commons.{protocol_id}.locked-summary.v1",
        "artifact_type": "reviewed-locked-summary",
        "status": "completed",
        "protocol_id": protocol_id,
        "reviewed_on": reviewed_on,
        "software": software,
    }


def chembl_locked_summary(metrics: Mapping[str, Any], *, reviewed_on: str) -> dict[str, Any]:
    """Retain all three baselines on both evaluation sets, including failed transfer."""
    try:
        _require(metrics["locked_evaluation_complete"] is True, "evaluation is not completed")
        _require(
            metrics["schema_version"] == "aidd-commons.chembl-egfr-locked-results.v1"
            and metrics["protocol_version"] == "chembl37-egfr-representation-v1",
            "wrong ChEMBL result protocol",
        )
        alphas = {
            name: _number(metrics["selected_alphas"][name])
            for name in ("descriptor_ridge", "morgan_ridge")
        }
        _require(alphas == {"descriptor_ridge": 1000, "morgan_ridge": 1}, "selected alphas changed")
        expected = {"primary_test": 132, "assay_replication": 170}
        _require(set(metrics["results"]) == set(expected), "both evaluation sets are required")
        results = {}
        models = ("train_mean", "descriptor_ridge", "morgan_ridge")
        for name, count in expected.items():
            source = metrics["results"][name]
            _require(
                type(source["count"]) is int and source["count"] == count, "parent count changed"
            )
            _require(set(source["metrics"]) == set(models), "all three baselines are required")
            scores = {}
            for model in models:
                raw = source["metrics"][model]
                numeric = _scores(raw)
                status = raw["spearman_status"]
                rho = raw["spearman"]
                if status == "defined":
                    rho = _number(rho, minimum=-1, maximum=1)
                else:
                    _require(
                        status in ("undefined_constant_prediction", "undefined_constant_target")
                        and rho is None,
                        "undefined correlation needs its explicit reason and null value",
                    )
                if model == "train_mean":
                    _require(status == "undefined_constant_prediction", "train mean is constant")
                scores[model] = {**numeric, "spearman": rho, "spearman_status": status}
            results[name] = {"count": count, "metrics": scores}
        summary = _base(
            metrics,
            protocol_id="chembl37-egfr-representation-v1",
            reviewed_on=reviewed_on,
            chembl=True,
        )
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise SummaryContractError(f"cannot project ChEMBL results: {error}") from error
    return {
        **summary,
        "selected_alphas": alphas,
        "results": results,
        "interpretation": [
            "T15 accessed labels shared with T05 before this evaluation; "
            "this is not an entirely untouched independent confirmatory evaluation.",
            "The frozen split, alpha grid and selected alphas were not retuned "
            "after that exposure.",
            "Primary evaluation and assay replication are separate comparisons; "
            "success on one does not erase failure on the other.",
            "Descriptor alpha is at the upper edge of the frozen grid.",
            "No confidence intervals, p values or pooled-assay superiority claims are reported.",
        ],
    }


def rmd17_locked_summary(
    metrics: Mapping[str, Any], protocol: Mapping[str, Any], *, reviewed_on: str
) -> dict[str, Any]:
    """Summarize the two systems separately and aggregate their MAEs, not their frames."""
    try:
        protocol_id = "rmd17-system-state-v1"
        _require(
            metrics["schema_version"] == "aidd-commons.rmd17-system-state-locked-metrics.v1"
            and metrics["protocol_id"] == protocol["protocol_id"] == protocol_id,
            "wrong rMD17 result protocol",
        )
        _require(_number(metrics["selected_alpha"]) == 100, "selected alpha changed")
        partitions = dict(protocol["sampling"]["partitions"])
        _require(
            partitions == {"train": 600, "validation": 200, "evaluation": 200}
            and protocol["sampling"]["selected_frames"] == 1000,
            "frozen partition counts changed",
        )
        systems = [entry["system_id"] for entry in protocol["systems"] if entry["role"] == "locked"]
        _require(systems == ["benzene", "uracil"], "both frozen locked systems are required")
        _require(set(metrics["results"]) == set(systems), "result systems differ from protocol")
        results = {}
        models = ("train_mean", "ridge")
        for system in systems:
            raw = metrics["results"][system]
            _require(set(raw) == set(models), "both baselines are required")
            scores = {
                model: {**_scores(raw[model]), "target_range": _number(raw[model]["target_range"])}
                for model in models
            }
            _require(
                scores["train_mean"]["target_range"] == scores["ridge"]["target_range"],
                "target ranges differ between baselines",
            )
            results[system] = scores
        aggregates = {}
        for model in models:
            values = [results[system][model]["mae"] for system in systems]
            aggregates[model] = {
                "median_mae": median(values),
                "mae_range": max(values) - min(values),
            }
        summary = _base(metrics, protocol_id=protocol_id, reviewed_on=reviewed_on, chembl=False)
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise SummaryContractError(f"cannot project rMD17 results: {error}") from error
    return {
        **summary,
        "selected_alpha": 100.0,
        "system_count": len(systems),
        "partitions_per_system": partitions,
        "results": results,
        "aggregates": aggregates,
        "interpretation": [
            "Each model is fitted on its own system's training frames; "
            "this is not zero-shot transfer.",
            "The reporting units are two molecular systems; "
            "frames within each system are correlated.",
            "No frame-pooled metrics, confidence intervals, p values, force or SOTA claims "
            "are reported.",
            "The original evaluation did not retain per-frame Ridge predictions. "
            "Post-run checks recomputed train-mean scores and target ranges, not Ridge scores.",
        ],
    }


def export_locked_summary(lab: Path, *, kind: Literal["chembl", "rmd17"], reviewed_on: str) -> Path:
    """Read completed local scores only; refuse to replace a different reviewed summary."""
    source = lab / "results/locked-metrics.json"
    target = lab / "locked-summary.json"
    inputs = [source] + ([lab / "protocol.json"] if kind == "rmd17" else [])
    _require(not any(path.is_symlink() for path in [*inputs, target]), "no symlink input or output")
    metrics = json.loads(source.read_text(encoding="utf-8"))
    if kind == "chembl":
        summary = chembl_locked_summary(metrics, reviewed_on=reviewed_on)
    else:
        protocol = json.loads((lab / "protocol.json").read_text(encoding="utf-8"))
        summary = rmd17_locked_summary(metrics, protocol, reviewed_on=reviewed_on)
    if target.exists():
        _require(
            json.loads(target.read_text(encoding="utf-8")) == summary,
            "existing public summary differs; review it before replacement",
        )
    else:
        with target.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return target
