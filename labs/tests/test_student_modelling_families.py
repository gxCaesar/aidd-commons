"""The sandbox must compare two model families under one selection procedure."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/student_modelling"

_spec = importlib.util.spec_from_file_location("student_run_lab", LAB / "run_lab.py")
run_lab = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules.setdefault("student_run_lab", run_lab)
_spec.loader.exec_module(run_lab)


@pytest.fixture
def report():
    return run_lab.run(run_lab.teaching_rows())


def test_both_families_are_selected_under_the_same_rule(report):
    """Only the assumption set may differ between the two arms."""
    assert report["selection"]["regression_alpha"] == 0.0
    assert report["selection"]["stump_min_leaf"] == 1
    # Lowest validation MAE, ties to the less constrained candidate, in both arms.
    linear = min(report["validation_scores"], key=lambda row: (row["regression_mae"], row["alpha"]))
    tree = min(
        report["stump_validation_scores"],
        key=lambda row: (row["regression_mae"], row["min_leaf"]),
    )
    assert linear["alpha"] == report["selection"]["regression_alpha"]
    assert tree["min_leaf"] == report["selection"]["stump_min_leaf"]


def test_the_leaf_grid_is_uninformative_on_these_records(report):
    """The lesson claims the grid decided nothing here, so that must stay true."""
    thresholds = {row["split_threshold"] for row in report["stump_validation_scores"]}
    errors = {row["regression_mae"] for row in report["stump_validation_scores"]}
    assert thresholds == {2.5}
    assert errors == {1.0}


def test_the_stump_cannot_extrapolate(report):
    """The whole teaching point: outside the training range it repeats a constant."""
    stump = report["models"]["stump"]
    train_features = [row["feature"] for row in run_lab.teaching_rows() if row["split"] == "train"]
    far_outside = [max(train_features) + 10, max(train_features) + 1000]
    predictions = run_lab.predict_stump(stump, far_outside)
    assert predictions[0] == predictions[1] == stump[2]


def test_the_families_are_scored_on_the_same_records_against_the_same_baseline(report):
    metrics = report["test_metrics"]
    assert {"ridge", "stump", "train_mean"} <= set(metrics)
    # The constructed regime: the linear arm loses to the constant, the tree arm does not.
    assert metrics["ridge"]["mae"] > metrics["train_mean"]["mae"] > metrics["stump"]["mae"]


def test_an_impossible_leaf_size_degenerates_to_the_constant_it_contains():
    """A family with no admissible split must fall back, not raise or invent one."""
    x = [0.0, 1.0, 2.0]
    y = [1.0, 3.0, 5.0]
    threshold, left, right = run_lab.fit_stump(x, y, min_leaf=3)
    assert threshold is None
    assert left == right == run_lab.mean(y)
    assert run_lab.predict_stump((threshold, left, right), [99.0]) == [run_lab.mean(y)]


def test_the_notebook_teaches_the_comparison_rather_than_only_running_it():
    """A runnable comparison without the argument is not the topic."""
    import json

    for suffix in ("", ".zh-CN"):
        notebook = json.loads(
            (LAB / f"student_modelling_tutorial{suffix}.ipynb").read_text(encoding="utf-8")
        )
        prose = "\n".join(
            "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown"
        )
        code = "\n".join(
            "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
        )
        assert "fit_stump" in code and "predict_stump" in code
        # The reader must be warned against reading the win as evidence about families.
        for marker in ("extrapolat", "外推"):
            if marker in prose:
                break
        else:
            raise AssertionError("neither edition explains the extrapolation argument")
        assert "5." in prose


def test_compute_buys_decision_stability_before_probability_agreement(report):
    """The observed pattern the lesson argues from must stay observable."""
    summary = {row["steps"]: row for row in report["budget_summary"]}
    assert set(summary) == {50, 200, 500}
    assert summary[50]["gradient_evaluations"] == 300
    assert summary[500]["gradient_evaluations"] == 3000
    # Three starting points disagree on the decision at the cheapest budget only.
    assert summary[50]["decisions_agree"] is False
    assert summary[200]["decisions_agree"] is True
    assert summary[500]["decisions_agree"] is True
    # Spread keeps shrinking after the decision has already stopped moving.
    spreads = [summary[steps]["largest_probability_spread"] for steps in (50, 200, 500)]
    assert spreads[0] > spreads[1] > spreads[2]


def test_the_optimiser_sweep_changes_nothing_but_the_search(report):
    """Data, penalty and selection rule must be identical across the attempts."""
    attempts = report["optimisation_variability"]
    assert len(attempts) == 9
    assert {tuple(row["start"]) for row in attempts} == {(0.0, 0.0), (-2.0, 1.0), (2.0, -1.0)}
    for row in attempts:
        assert row["gradient_evaluations"] == row["steps"] * report["counts"]["train"]
        assert len(row["validation_probabilities"]) == report["counts"]["validation"]
        assert row["validation_decisions"] == [
            int(probability >= 0.5) for probability in row["validation_probabilities"]
        ]


def test_the_default_optimiser_arguments_reproduce_the_original_fit():
    """Adding the knobs must not have moved the fit that earlier results describe."""
    rows = run_lab.teaching_rows()
    train = [row for row in rows if row["split"] == "train"]
    x = [row["feature"] for row in train]
    hits = [row["hit"] for row in train]
    assert run_lab.fit_logistic(x, hits, 0.0) == run_lab.fit_logistic(
        x, hits, 0.0, steps=500, start=(0.0, 0.0)
    )
