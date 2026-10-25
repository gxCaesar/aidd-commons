"""Positives, negatives, decoys, balance and the unit must stay visible as choices."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/binder_definition"

_spec = importlib.util.spec_from_file_location("inspect_definition", LAB / "inspect_definition.py")
binder = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(binder)


@pytest.fixture(scope="module")
def data():
    return binder.load()


def test_the_committed_dataset_passes_every_check(data, capsys):
    assert binder.check(data) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 16


def test_the_dataset_stores_no_class_label(data):
    """A class is produced by a choice, so storing one would hide the choice."""
    source = (LAB / "dataset.json").read_text(encoding="utf-8")
    for forbidden in ('"label"', '"active"', '"is_binder"', '"class"'):
        assert forbidden not in source
    for row in data["measured"]:
        assert set(row) == {"id", "smiles", "value"}
    for row in data["decoys"]["members"]:
        assert set(row) == {"id", "smiles"}


def test_the_same_measurements_give_different_positive_counts(data):
    counts = {cutoff: len(binder.positives(data, cutoff)) for cutoff in data["threshold_grid"]}
    assert counts == {5.0: 9, 5.5: 8, 6.0: 6, 6.5: 4, 7.0: 4}
    assert max(counts.values()) >= 2 * min(counts.values())


def test_some_classes_are_decided_by_noise(data):
    """Within the declared assay uncertainty, the reading places the compound, not the assay."""
    primary = data["primary_threshold"]["value"]
    near = binder.undetermined(data, primary)
    assert near == ["m03", "m04", "m06", "m09"]
    values = {row["id"]: row["value"] for row in data["measured"]}
    assert any(values[i] >= primary for i in near)
    assert any(values[i] < primary for i in near)


def test_decoys_change_the_balance_without_adding_evidence(data):
    primary = data["primary_threshold"]["value"]
    without = binder.composition(data, primary, include_decoys=False)
    with_decoys = binder.composition(data, primary, include_decoys=True)
    assert without["positives"] == with_decoys["positives"]
    assert without["prevalence"] == 0.5
    assert with_decoys["prevalence"] == 0.25
    assert without["never_measured_share"] == 0.0
    assert with_decoys["never_measured_share"] > 0.5


def test_the_generalization_unit_collapses_and_is_sometimes_undefined(data):
    units = binder.unit_counts(data["measured"])
    assert units["molecules"] == 12
    assert units["scaffolds"] == 4
    assert units["undefined"] == ["m11"]
    primary = data["primary_threshold"]["value"]
    positive_ids = set(binder.positives(data, primary))
    positive_units = binder.unit_counts(
        [row for row in data["measured"] if row["id"] in positive_ids]
    )
    assert (positive_units["molecules"], positive_units["scaffolds"]) == (6, 3)


def test_runs_offline_and_refuses_to_rank_the_choices():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_definition.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "A NEGATIVE IS TWO DIFFERENT THINGS" in result.stdout
    assert "THE GENERALIZATION UNIT IS NOT THE MOLECULE" in result.stdout
    assert "does not say which choices are correct" in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Giving a decoy a measurement makes it an inactive compound, not a decoy.
        (
            lambda d: d["decoys"]["members"][0].update({"value": 4.0}),
            "carries a measurement",
        ),
        # Dropping the stated assumption presents an assumption as evidence.
        (lambda d: d["decoys"].update({"assumption": ""}), "states the assumption"),
        # Choosing the cutoff after looking.
        (
            lambda d: d["primary_threshold"].update({"declared_before_analysis": False}),
            "declared before the analysis",
        ),
        # A grid with one cutoff hides that the cutoff is a choice at all.
        (lambda d: d.__setitem__("threshold_grid", [6.0]), "different positive counts"),
        # An assay with no uncertainty makes every class look determined.
        (
            lambda d: d["endpoint"].update({"assay_uncertainty": 0.0}),
            "positive assay uncertainty",
        ),
        # A set where every molecule has its own scaffold hides the unit problem.
        (
            lambda d: d.__setitem__(
                "measured",
                [row for row in d["measured"] if row["id"] in {"m01", "m05", "m08", "m11"}],
            ),
            "collapse to",
        ),
    ],
)
def test_a_hidden_choice_is_rejected(data, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    broken = copy.deepcopy(data)
    mutate(broken)
    failures = binder.check(broken)
    assert any(expected in failure for failure in failures), failures
