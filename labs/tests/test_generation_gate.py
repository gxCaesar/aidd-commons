"""The gate must reject an uncheckable objective and a screen that relaxes it."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/generation_gate"

# The novelty reference is a FreeSolv run output. The curated public release withholds
# run outputs, so there this module skips instead of failing on a missing file.
pytestmark = pytest.mark.skipif(
    not (ROOT / "labs/freesolv/results/splits/scaffold.csv").is_file(),
    reason="FreeSolv run outputs are intentionally absent from the public release",
)

_spec = importlib.util.spec_from_file_location("inspect_gate", LAB / "inspect_gate.py")
gate = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gate)


@pytest.fixture(scope="module")
def loaded():
    return gate.load()


def test_the_committed_objective_and_screen_pass_every_check(loaded, capsys):
    objective, candidates, reference = loaded
    assert gate.check(objective, candidates, reference) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 17


def test_the_single_validity_figure_overstates_the_survivors(loaded):
    """The teaching point: one percentage replaces six denominators."""
    objective, candidates, reference = loaded
    result = gate.screen(objective, candidates, reference)
    total = len(candidates["candidates"])
    valid = total - result["funnel"][0]["stopped"]
    assert (valid, total) == (18, 20)
    assert len(result["survivors"]) == 6
    # Each gate is applied only to what reached it.
    for index, step in enumerate(result["funnel"][1:], start=1):
        assert step["entered"] == result["funnel"][index - 1]["survived"]


def test_memorization_is_the_novelty_gate_against_a_different_set(loaded):
    """Not a seventh gate: the same check, a narrower reference."""
    objective, candidates, reference = loaded
    result = gate.screen(objective, candidates, reference)
    grouped = gate.memorization_split(result)
    assert grouped == {"test": ["c11", "c12"], "train": ["c13", "c14"]}
    # Every non-novel candidate was stopped by one gate, not two.
    stopped = [row for row in result["rows"] if row["gate"] == "novelty"]
    assert {row["id"] for row in stopped} == {"c11", "c12", "c13", "c14"}


def test_route_feasibility_is_never_established(loaded):
    """The synthesis gate is a proxy and the objective says so."""
    objective, _, _ = loaded
    assert objective["synthesis_limits"]["route_feasibility"] == "not_assessed"


def test_the_frozen_selection_rule_is_the_one_implemented(loaded):
    """The rule names heavy-atom count, so the code must order by that."""
    objective, candidates, reference = loaded
    result = gate.screen(objective, candidates, reference)
    batch = gate.selected_batch(objective, result)
    assert len(batch) == objective["experimental_decision"]["batch_size"]
    from rdkit import Chem

    counts = [
        Chem.MolFromSmiles(
            next(row["canonical"] for row in result["survivors"] if row["id"] == identifier)
        ).GetNumHeavyAtoms()
        for identifier in batch
    ]
    assert counts == sorted(counts)


def test_the_abstention_rule_fires_instead_of_relaxing_a_gate(loaded):
    """With too few survivors the batch shrinks; no gate is loosened to fill it."""
    objective, candidates, reference = loaded
    thin = copy.deepcopy(candidates)
    keep = {"c01", "c02", "c07", "c11", "c15"}
    thin["candidates"] = [row for row in thin["candidates"] if row["id"] in keep]
    result = gate.screen(objective, thin, reference)
    batch = gate.selected_batch(objective, result)
    assert len(batch) == 2 < objective["experimental_decision"]["batch_size"]
    assert set(batch) == {"c01", "c02"}


def test_runs_offline_and_prints_both_halves():
    for action, marker in (
        ("objective", "FROZEN DESIGN OBJECTIVE"),
        ("screen", "GATE FUNNEL OVER"),
    ):
        result = subprocess.run(
            [sys.executable, str(LAB / "inspect_gate.py"), action],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )
        assert marker in result.stdout
    assert (
        "NOVELTY IS NOT ONE FACT"
        in subprocess.run(
            [sys.executable, str(LAB / "inspect_gate.py"), "screen"],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        ).stdout
    )


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # An objective that never names the decision cannot say what a pass is for.
        (lambda o, c: o.pop("experimental_decision"), "declares all five required parts"),
        # A property without a bound is a wish rather than a gate.
        (
            lambda o, c: o["desired_properties"][1]["bound"].pop("maximum"),
            "two-sided bound",
        ),
        # A motif that does not compile silently stops excluding anything.
        (
            lambda o, c: o["prohibited_motifs"][0].update({"smarts": "[C(((("}),
            "applicable pattern",
        ),
        # Dropping the abstention rule is how a thin batch gets filled by relaxing a gate.
        (lambda o, c: o["experimental_decision"].pop("abstention_rule"), "too few candidates"),
        # Claiming route feasibility from structural proxies.
        (
            lambda o, c: o["synthesis_limits"].update({"route_feasibility": "acceptable"}),
            "not assessed",
        ),
        # Retrofitting a bound so a stopped candidate would pass.
        (
            lambda o, c: o["desired_properties"][3]["bound"].update({"maximum": 40}),
            "the gate its teaching label names",
        ),
        # Misdeclaring the reference set the novelty rate is quoted against.
        (
            lambda o, c: o["target_context"].update({"reference_set_size": 700}),
            "reference set size matches the file",
        ),
        (
            lambda o, c: o["target_context"].update({"training_split_size": 600}),
            "training split size matches the file",
        ),
        # Removing the frozen-before-generation record.
        (lambda o, c: o.update({"declared_before_generation": False}), "frozen before generation"),
        # A candidate whose label no longer matches the gate that stops it.
        (
            lambda o, c: c["candidates"][0].update({"constructed_for": "validity"}),
            "the gate its teaching label names",
        ),
        # Claiming a memorized candidate came from a held-out split.
        (
            lambda o, c: next(row for row in c["candidates"] if row["id"] == "c13").update(
                {"expected_reference_split": "test"}
            ),
            "reference split its label names",
        ),
    ],
)
def test_an_uncheckable_objective_or_relaxed_screen_is_rejected(loaded, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    objective, candidates, reference = loaded
    broken_objective = copy.deepcopy(objective)
    broken_candidates = copy.deepcopy(candidates)
    mutate(broken_objective, broken_candidates)
    failures = gate.check(broken_objective, broken_candidates, reference)
    assert any(expected in failure for failure in failures), failures


def test_the_gates_are_computed_from_structure_not_from_the_teaching_label():
    """Relabelling every candidate must not change a single gate outcome."""
    objective, candidates, reference = gate.load()
    relabelled = copy.deepcopy(candidates)
    for entry in relabelled["candidates"]:
        entry["constructed_for"] = "none"
    before = gate.screen(objective, candidates, reference)
    after = gate.screen(objective, relabelled, reference)
    assert [row["gate"] for row in before["rows"]] == [row["gate"] for row in after["rows"]]


def test_the_committed_artifacts_are_frozen_json_beside_the_lab():
    for path in (gate.OBJECTIVE, gate.CANDIDATES):
        assert path.parent == LAB
        assert path.suffix == ".json"
        json.loads(path.read_text(encoding="utf-8"))
    # The reference set is a committed split table from a completed lab.
    objective = json.loads(gate.OBJECTIVE.read_text(encoding="utf-8"))
    reference = ROOT / objective["target_context"]["reference_set"]
    assert reference.is_file() and reference.suffix == ".csv"
