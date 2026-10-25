from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.rmd17_system_state.pipeline import (
    PipelineContractError,
    PublicSummaryError,
    development_summary,
    validate_public_summary,
)

FROZEN_ALPHA_GRID = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
REPOSITORY_ROOT = Path(__file__).parents[3]


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def _split_membership() -> dict[str, object]:
    old_indices = [
        3 * index + (5 if index >= 600 else 0) + (7 if index >= 800 else 0)
        for index in range(1_000)
    ]
    source_positions = list(range(999, -1, -1))
    return {
        "train": {
            "old_indices": old_indices[:600],
            "source_positions": source_positions[:600],
        },
        "validation": {
            "old_indices": old_indices[600:800],
            "source_positions": source_positions[600:800],
        },
        "evaluation": {
            "old_indices": old_indices[800:],
            "source_positions": source_positions[800:],
        },
    }


def _internal_pretest_payload() -> dict[str, Any]:
    metrics = {"mae": 0.5, "rmse": 0.75, "target_range": 2.0}
    return {
        "schema_version": "aidd-commons.rmd17-system-state-pretest.v1",
        "protocol_id": "rmd17-system-state-v1",
        "pretest_passed": True,
        "source": {
            "version": 4,
            "doi": "10.6084/m9.figshare.12672038.v4",
            "licence": "CC0",
            "data_path": "labs/rmd17_system_state/data/rmd17_ethanol.npz",
        },
        "protocol": {
            "split": {
                "selected_frames": 1_000,
                "partitions": {"train": 600, "validation": 200, "evaluation": 200},
                "original_index_ordering": "stable ascending old_indices",
            },
            "features": {
                "construction": "per-system lexicographic unordered element-pair channels",
                "bins_per_channel": 101,
                "distance_bin_width_angstrom": 0.1,
                "by_system": {
                    "ethanol": {
                        "element_pair_channels": ["Z1-Z1", "Z1-Z6"],
                        "channel_count": 2,
                        "feature_dimension": 202,
                    },
                    "malonaldehyde": {
                        "element_pair_channels": ["Z1-Z1", "Z1-Z6", "Z6-Z6"],
                        "channel_count": 3,
                        "feature_dimension": 303,
                    },
                },
            },
        },
        "selection": {
            "frozen_alphas": FROZEN_ALPHA_GRID,
            "grid": [
                {
                    "alpha": alpha,
                    "per_system_validation_mae": {"ethanol": 0.6, "malonaldehyde": 0.4},
                    "median_validation_mae": 0.5,
                }
                for alpha in FROZEN_ALPHA_GRID
            ],
            "selected_alpha": 1000.0,
        },
        "development": {
            system_id: {
                "split_membership": _split_membership(),
                "evaluation": {
                    "metrics": {"train_mean": metrics, "ridge": metrics},
                    "records": [
                        {
                            "old_index": 800,
                            "source_position": 800,
                            "target": 1.0,
                            "predictions": {"ridge": 0.8},
                            "errors": {"ridge": 0.2},
                        }
                    ],
                },
                "fit_row_ids": [f"{system_id}:{position}" for position in range(600)],
            }
            for system_id in ("ethanol", "malonaldehyde")
        },
        "software": {"python": "3.11.0", "numpy": "2.4.6", "scikit_learn": "1.9.0"},
        "locked_evaluations": {"benzene": "not_run", "uracil": "not_run"},
    }


def test_summary_projects_only_aggregate_development_evidence(tmp_path: Path) -> None:
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(_internal_pretest_payload()), encoding="utf-8")

    summary = development_summary(pretest_path)

    assert summary["artifact_type"] == "reviewed-development-summary"
    assert summary["source"] == {
        "version": 4,
        "doi": "10.6084/m9.figshare.12672038.v4",
        "licence": "CC0",
    }
    assert summary["selection"]["selected_alpha"] == 1000.0
    assert summary["locked_evaluations"] == {"benzene": "not_run", "uracil": "not_run"}
    assert summary["features"]["by_system"]["ethanol"]["feature_dimension"] == 202
    assert summary["features"]["by_system"]["malonaldehyde"]["feature_dimension"] == 303
    assert _all_keys(summary).isdisjoint(
        {
            "coordinates",
            "nuclear_charges",
            "energies",
            "forces",
            "old_indices",
            "source_positions",
            "fit_row_ids",
            "predictions",
            "errors",
            "data_path",
        }
    )
    validate_public_summary(summary)


def test_checked_in_development_summary_is_reviewed_and_aggregate_only() -> None:
    summary = json.loads(
        (REPOSITORY_ROOT / "labs/rmd17_system_state/development-summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["protocol_id"] == "rmd17-system-state-v1"
    assert summary["reviewed_on"] == "2026-09-05"
    assert summary["source"] == {
        "version": 4,
        "doi": "10.6084/m9.figshare.12672038.v4",
        "licence": "CC0",
    }
    assert summary["selection"]["selected_alpha"] == 100.0
    assert summary["features"]["by_system"]["ethanol"]["feature_dimension"] == 505
    assert summary["features"]["by_system"]["malonaldehyde"]["feature_dimension"] == 606
    assert summary["development_evaluation"]["ethanol"]["ridge"]["mae"] == pytest.approx(
        2.4810026728771484
    )
    assert summary["development_evaluation"]["malonaldehyde"]["ridge"][
        "mae"
    ] == pytest.approx(2.74979407419567)
    assert summary["aggregates"]["ridge"]["median_mae"] == pytest.approx(
        2.6153983735364092
    )
    assert summary["locked_evaluations"] == {"benzene": "not_run", "uracil": "not_run"}
    assert all(
        diagnostics["strictly_increasing"] is True
        for diagnostics in summary["split"]["ordering_diagnostics_by_system"].values()
    )
    validate_public_summary(summary)


def test_summary_projects_aggregate_ordering_and_gap_diagnostics(tmp_path: Path) -> None:
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(_internal_pretest_payload()), encoding="utf-8")

    summary = development_summary(pretest_path)

    expected = {
        "strictly_increasing": True,
        "adjacent_original_index_gap": {"minimum": 3, "median": 3, "maximum": 10},
        "partition_boundary_gap": {
            "train_to_validation": 8,
            "validation_to_evaluation": 10,
        },
    }
    assert summary["split"]["ordering_diagnostics_by_system"] == {
        "ethanol": expected,
        "malonaldehyde": expected,
    }
    validate_public_summary(summary)


def test_summary_rejects_unordered_split_membership(tmp_path: Path) -> None:
    payload = _internal_pretest_payload()
    membership = payload["development"]["ethanol"]["split_membership"]
    membership["validation"]["old_indices"][0] = membership["train"]["old_indices"][-1]
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="strictly increasing"):
        development_summary(pretest_path)


def test_summary_rejects_wrong_split_membership_length(tmp_path: Path) -> None:
    payload = _internal_pretest_payload()
    membership = payload["development"]["ethanol"]["split_membership"]
    membership["validation"]["old_indices"].pop()
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="length"):
        development_summary(pretest_path)


def test_summary_rejects_split_membership_without_exact_partition_keys(tmp_path: Path) -> None:
    payload = _internal_pretest_payload()
    membership = payload["development"]["ethanol"]["split_membership"]
    membership["other"] = membership.pop("evaluation")
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="partition schema"):
        development_summary(pretest_path)


def test_summary_rejects_negative_split_membership_index(tmp_path: Path) -> None:
    payload = _internal_pretest_payload()
    membership = payload["development"]["ethanol"]["split_membership"]
    membership["train"]["old_indices"][0] = -1
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="non-negative integer"):
        development_summary(pretest_path)


def test_summary_allowlists_validation_grid_aggregate_fields(tmp_path: Path) -> None:
    payload = _internal_pretest_payload()
    grid = payload["selection"]["grid"]
    assert isinstance(grid, list)
    first = grid[0]
    assert isinstance(first, dict)
    first["row_ids"] = ["ethanol:42"]
    first["frameId"] = 42
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    summary = development_summary(pretest_path)

    assert set(summary["selection"]["validation_grid"][0]) == {
        "alpha",
        "per_system_validation_mae",
        "median_validation_mae",
    }
    validate_public_summary(summary)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mae", [0.5]),
        ("rmse", {"nested": 0.75}),
        ("target_range", float("nan")),
        ("mae", float("inf")),
        ("frameId", 42),
    ],
    ids=("array", "nested", "nan", "infinity", "disguised-frame"),
)
def test_summary_rejects_non_scalar_or_non_finite_or_extra_metric_evidence(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    payload = _internal_pretest_payload()
    metrics = payload["development"]["ethanol"]["evaluation"]["metrics"]["ridge"]
    assert isinstance(metrics, dict)
    metrics[field] = value
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="metrics"):
        development_summary(pretest_path)


def test_summary_rejects_metric_schema_missing_required_scalar(tmp_path: Path) -> None:
    payload = _internal_pretest_payload()
    metrics = payload["development"]["ethanol"]["evaluation"]["metrics"]["ridge"]
    assert isinstance(metrics, dict)
    del metrics["rmse"]
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="metrics"):
        development_summary(pretest_path)


def test_summary_rejects_persisted_selected_alpha_that_disagrees_with_grid(tmp_path: Path) -> None:
    payload = _internal_pretest_payload()
    payload["selection"]["selected_alpha"] = 0.001
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PipelineContractError, match="selected alpha"):
        development_summary(pretest_path)


def test_summary_reapplies_exact_tie_break_to_larger_frozen_alpha(tmp_path: Path) -> None:
    pretest_path = tmp_path / "pretest.json"
    pretest_path.write_text(json.dumps(_internal_pretest_payload()), encoding="utf-8")

    summary = development_summary(pretest_path)

    assert summary["selection"]["selected_alpha"] == 1000.0


def test_public_redaction_rejects_forbidden_keys_and_canonical_internal_paths() -> None:
    with pytest.raises(PublicSummaryError, match="forbidden key"):
        validate_public_summary({"development": {"predictions": [0.2]}})

    with pytest.raises(PublicSummaryError, match="forbidden path"):
        validate_public_summary(
            {"source": {"location": "labs/rmd17_system_state/results/locked-metrics.json"}}
        )

    with pytest.raises(PublicSummaryError, match="forbidden key"):
        validate_public_summary({"development": {"split_membership": {"train": [1]}}})

    for forbidden_key in ("row_ids", "frameId", "FRAME-ID"):
        with pytest.raises(PublicSummaryError, match="forbidden key"):
            validate_public_summary({"development": {forbidden_key: [1]}})

    with pytest.raises(PublicSummaryError, match="forbidden path"):
        validate_public_summary({"source": {"location": "labs/rmd17_system_state/data"}})
