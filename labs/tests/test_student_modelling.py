"""Literal numerical oracles and a real CLI test for the isolated teaching lab."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "student_modelling" / "run_lab.py"


def module():
    assert SCRIPT.is_file(), "The standalone student training runner is not implemented"
    spec = importlib.util.spec_from_file_location("student_modelling", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_ridge_matches_hand_solution_and_unpenalized_intercept():
    lab = module()
    # x mean 1, y mean 3; covariance sum 4, centered x square sum 2.
    assert lab.fit_ridge([0, 1, 2], [1, 3, 5], 0) == pytest.approx((1, 2))
    assert lab.fit_ridge([0, 1, 2], [1, 3, 5], 2) == pytest.approx((2, 1))
    assert lab.fit_ridge([1, 1], [2, 4], 0) == pytest.approx((3, 0))


def test_classification_loss_and_confusion_have_independent_literal_oracles():
    lab = module()
    assert lab.log_loss([0, 1], [0.2, 0.8]) == pytest.approx(0.2231435513142097)
    assert lab.classification_metrics([0, 1, 1, 0], [0.2, 0.8, 0.4, 0.7]) == {
        "tp": 1,
        "tn": 1,
        "fp": 1,
        "fn": 1,
        "accuracy": 0.5,
        "precision": 0.5,
        "recall": 0.5,
    }
    assert lab.classification_metrics([1, 0], [0.1, 0.1])["precision"] is None


def test_logistic_training_learns_direction_and_uses_train_scaling():
    lab = module()
    model = lab.fit_logistic([-2, -1, 1, 2], [0, 0, 1, 1], 0)
    assert model["mean"] == 0
    assert model["scale"] == pytest.approx(1.5811388300841898)
    predictions = lab.predict_logistic(model, [-2, 2])
    assert predictions[0] < 0.1 and predictions[1] > 0.9
    assert lab.sigmoid(-1000) == 0
    assert lab.sigmoid(1000) == 1


def test_validation_selects_without_refitting_and_test_labels_cannot_select():
    lab = module()
    rows = lab.teaching_rows()
    original = lab.run(rows)
    changed = copy.deepcopy(rows)
    for row in changed:
        if row["split"] == "test":
            row["response"] += 100
            row["hit"] = 1 - row["hit"]
    mutated = lab.run(changed)
    assert original["selection"] == mutated["selection"]
    assert original["models"] == mutated["models"]
    assert [r["prediction"] for r in original["test_predictions"]] == [
        r["prediction"] for r in mutated["test_predictions"]
    ]
    assert original["test_metrics"] != mutated["test_metrics"]
    assert original["counts"] == {"train": 6, "validation": 2, "test": 2}
    # Validation labels may change the choice, but not candidate training parameters.
    for row in changed:
        if row["split"] == "validation":
            # Both labels at the train mean favor shrinkage; zero labels instead
            # make all three positive prediction pairs tie at MAE 6.
            row["response"] = 6
    validation_changed = lab.run(changed)
    assert original["candidate_models"] == validation_changed["candidate_models"]
    assert (
        original["selection"]["regression_alpha"]
        != validation_changed["selection"]["regression_alpha"]
    )


@pytest.mark.parametrize("mutation", ["overlap", "nan", "nonbinary", "empty-validation"])
def test_known_bad_records_fail_before_fit(mutation):
    lab = module()
    rows = lab.teaching_rows()
    if mutation == "overlap":
        rows[-1]["entity_id"] = rows[0]["entity_id"]
    elif mutation == "nan":
        rows[0]["feature"] = float("nan")
    elif mutation == "nonbinary":
        rows[0]["hit"] = 2
    else:
        rows = [row for row in rows if row["split"] != "validation"]
    with pytest.raises(ValueError):
        lab.run(rows)


def test_real_cli_writes_only_a_fresh_sandbox_report(tmp_path):
    module()
    # Script roots itself at its checkout; subprocess CWD cannot redirect output elsewhere.
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path / "escape.json")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not (tmp_path / "escape.json").exists()


def test_writer_refuses_overwrite_traversal_and_symlink_escape(tmp_path):
    lab = module()
    root = tmp_path / "sandbox"
    root.mkdir()
    result = {"data_kind": "synthetic-teaching-example"}
    destination = root / "first.json"
    lab.write_report(result, destination, root)
    assert json.loads(destination.read_text()) == result
    with pytest.raises(FileExistsError):
        lab.write_report(result, destination, root)
    with pytest.raises(ValueError):
        lab.write_report(result, root / ".." / "escape.json", root)
    (root / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        lab.write_report(result, root / "link" / "escape.json", root)
    outside = tmp_path / "outside"
    outside.mkdir()
    linked_root = tmp_path / "linked-sandbox"
    linked_root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        lab.write_report(result, linked_root / "escape.json", linked_root)


def test_writer_does_not_follow_a_parent_swapped_after_path_check(tmp_path, monkeypatch):
    lab = module()
    root = tmp_path / "sandbox"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    original_check = Path.is_symlink
    swapped = False

    def swap_after_last_check(path):
        nonlocal swapped
        result = original_check(path)
        if path == Path("/") and not swapped:
            root.rename(tmp_path / "original-sandbox")
            root.symlink_to(outside, target_is_directory=True)
            swapped = True
        return result

    # Real filesystem replacement, timed at the end of the preflight check.
    monkeypatch.setattr(Path, "is_symlink", swap_after_last_check)
    with pytest.raises((ValueError, OSError)):
        lab.write_report({"example": True}, root / "escape.json", root)
    assert swapped
    assert not (outside / "escape.json").exists()


def test_writer_creates_an_entirely_absent_nested_sandbox_root(tmp_path):
    lab = module()
    root = tmp_path / "missing" / "student-modelling"
    destination = root / "nested" / "report.json"

    lab.write_report({"example": True}, destination, root)

    assert json.loads(destination.read_text()) == {"example": True}


def test_writer_does_not_follow_an_ancestor_swapped_after_path_check(tmp_path, monkeypatch):
    lab = module()
    ancestor = tmp_path / "anchor"
    root = ancestor / "sandbox"
    root.mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "sandbox").mkdir(parents=True)
    original_check = Path.is_symlink
    swapped = False

    def swap_after_last_check(path):
        nonlocal swapped
        result = original_check(path)
        if path == Path("/") and not swapped:
            ancestor.rename(tmp_path / "original-anchor")
            ancestor.symlink_to(outside, target_is_directory=True)
            swapped = True
        return result

    monkeypatch.setattr(Path, "is_symlink", swap_after_last_check)
    with pytest.raises((ValueError, OSError)):
        lab.write_report({"example": True}, root / "escape.json", root)
    assert swapped
    assert not (outside / "sandbox" / "escape.json").exists()
