"""An explanation of a well-fitted model must not be readable as a causal atom claim."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/sar_attribution"

_spec = importlib.util.spec_from_file_location(
    "inspect_attribution", LAB / "inspect_attribution.py"
)
sar = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(sar)


@pytest.fixture(scope="module")
def data():
    return sar.load()


@pytest.fixture(scope="module")
def model(data):
    return sar.fit(data)


def test_the_committed_dataset_passes_every_check(data, capsys):
    assert sar.check(data) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 14


def test_the_construction_makes_cause_and_proxy_indistinguishable(data):
    """Perfect correlation in training is what the analogues exist to break."""
    for row in data["training"]:
        mol, _, _ = sar.featurise(row["smiles"])
        assert sar.label(data, mol) == int(sar.carries_confounder(data, mol))


def test_the_model_fits_which_is_what_makes_the_explanation_feel_safe(data, model):
    weights, centre = model
    for row in data["training"]:
        mol, _, _ = sar.featurise(row["smiles"])
        error = abs(sar.predict(weights, centre, row["smiles"]) - sar.label(data, mol))
        assert error < 0.1


def test_the_explanation_credits_atoms_that_cause_nothing(data, model):
    """The load-bearing observation, on a set where the cause is known."""
    weights, _ = model
    actives = [
        row for row in data["training"] if sar.label(data, sar.featurise(row["smiles"])[0]) == 1
    ]
    splits = [sar.credit_split(data, weights, row["smiles"]) for row in actives]
    assert all(split["proxy"] > 0 for split in splits)
    wins = [split for split in splits if split["proxy"] > split["cause"]]
    assert len(wins) > len(actives) / 2


def test_the_ranking_of_the_broken_pair_is_inverted(data, model):
    """Opposite true activity, and the model puts them the wrong way round."""
    weights, centre = model
    rows = {row["id"]: row for row in sar.analogue_rows(data, weights, centre)}
    assert rows["a01"]["truth"] == 0 and rows["a01"]["confounder"] is True
    assert rows["a02"]["truth"] == 1 and rows["a02"]["confounder"] is False
    assert rows["a01"]["prediction"] > rows["a02"]["prediction"]
    assert abs(rows["a01"]["prediction"] - rows["a02"]["prediction"]) < 0.1
    assert rows["a02"]["call"] != rows["a02"]["truth"]


def test_the_controls_behave_as_the_rule_dictates(data, model):
    weights, centre = model
    rows = {row["id"]: row for row in sar.analogue_rows(data, weights, centre)}
    assert rows["a03"]["truth"] == 1 and rows["a03"]["call"] == 1
    assert rows["a04"]["truth"] == 0 and rows["a04"]["call"] == 0
    # Both signals present scores far above either alone.
    assert rows["a03"]["prediction"] > rows["a01"]["prediction"] + 0.3
    assert rows["a03"]["prediction"] > rows["a02"]["prediction"] + 0.3


def test_labels_come_from_the_rule_and_nothing_else(data):
    """No label is stored anywhere, so no label can drift from its cause."""
    source = (LAB / "dataset.json").read_text(encoding="utf-8")
    assert '"label"' not in source
    assert '"active"' not in source
    for row in data["training"] + data["analogues"]["members"]:
        assert set(row) <= {"id", "smiles", "breaks"}


def test_runs_offline_and_states_what_it_does_not_license():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_attribution.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "THE RANKING IS INVERTED" in result.stdout
    assert "WHAT THIS DOES AND DOES NOT LICENSE" in result.stdout
    assert "does not license a causal atom effect" in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Breaking the correlation in training removes the whole demonstration.
        (
            lambda d: d["training"].append({"id": "t17", "smiles": "OC(=O)CCc1ccccc1"}),
            "perfectly correlated",
        ),
        # Claiming the confounder is causal after the fact.
        (lambda d: d["confounder"].update({"causal_role": "contributes"}), "no causal role"),
        # Choosing the threshold after seeing predictions.
        (
            lambda d: d["threshold"].update({"declared_before_fitting": False}),
            "declared before fitting",
        ),
        # Dropping the analogue that carries the cause without the proxy.
        (
            lambda d: d["analogues"]["members"].__setitem__(
                1, {"id": "a02", "smiles": "OC(=O)CCc1ccoc1", "breaks": "cause without confounder"}
            ),
            "lacks the confounder",
        ),
        # A training set with only one class cannot separate anything.
        (
            lambda d: d.__setitem__(
                "training", [r for r in d["training"] if r["id"] in {"t01", "t02", "t03"}]
            ),
            "carries both classes",
        ),
    ],
)
def test_a_broken_construction_is_rejected(data, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    broken = copy.deepcopy(data)
    mutate(broken)
    failures = sar.check(broken)
    assert any(expected in failure for failure in failures), failures
