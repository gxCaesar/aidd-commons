"""Disconnection families must stay distinguishable, and recovery apart from feasibility."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/retro_disconnection"

_spec = importlib.util.spec_from_file_location(
    "inspect_disconnection", LAB / "inspect_disconnection.py"
)
retro = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(retro)


@pytest.fixture(scope="module")
def loaded():
    return retro.load()


def test_the_committed_set_passes_every_check(loaded, capsys):
    routes, methods = loaded
    assert retro.check(routes, methods) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 13


def test_the_three_families_score_differently_for_different_reasons(loaded):
    routes, methods = loaded
    members = set(routes["precedent_set"]["members"])
    unseen = {row["id"] for row in routes["routes"]} - members
    scores = {}
    for family in retro.runnable_families(methods):
        results = retro.run_family(routes, methods, family)
        scores[family] = (
            retro.score(results),
            retro.score(results, members),
            retro.score(results, unseen),
        )
    assert scores["rule"][0] == (10, 10)
    assert scores["template"][0] == (8, 10)
    assert scores["retrieval"][0] == (5, 10)
    # All three are perfect inside the precedent set; only outside it do they separate.
    for family in scores:
        assert scores[family][1] == (5, 5)
    assert scores["rule"][2] == (5, 5)
    assert scores["template"][2] == (3, 5)
    assert scores["retrieval"][2] == (0, 5)


def test_retrieval_generalises_to_nothing(loaded):
    """A lookup succeeding on its own table is the split talking, not the method."""
    routes, methods = loaded
    results = retro.run_family(routes, methods, "retrieval")
    for key, row in results.items():
        assert row["recovered"] is row["in_precedent"], key


def test_templates_inherit_the_coverage_of_their_dataset(loaded):
    routes, methods = loaded
    absent = set(routes["precedent_set"]["classes_absent"])
    template = retro.run_family(routes, methods, "template")
    rule = retro.run_family(routes, methods, "rule")
    for key, row in template.items():
        if row["transformation_class"] in absent:
            assert row["recovered"] is False
            # The same route is recovered by a hand-written rule, so the cause differs.
            assert rule[key]["recovered"] is True


def test_recovery_is_not_selection(loaded):
    """Several proposals can contain the record; that is not the method being right."""
    routes, methods = loaded
    rule = retro.run_family(routes, methods, "rule")
    multi = [key for key, row in rule.items() if row["proposals"] > 1]
    assert set(multi) == {"p07", "p08", "p10"}
    for key in multi:
        assert rule[key]["recovered"] is True


def test_feasibility_is_never_established(loaded):
    routes, _ = loaded
    assert routes["laboratory_feasibility"] == "not_assessed"
    assert routes["why_feasibility_is_not_assessed"]


def test_runs_offline_and_states_its_boundary():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_disconnection.py"), "compare"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "DECLARED, NOT RUN" in result.stdout
    assert "THE FAMILIES FAIL FOR DIFFERENT REASONS" in result.stdout
    assert "WHAT NO SCORE ABOVE ESTABLISHES" in result.stdout
    assert "RECOVERING A ROUTE IS NOT BEING RIGHT" in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Quietly running the learned family would claim a comparison never made.
        (
            lambda r, m: m["families"]["learned"].update({"runs_here": True}),
            "declared without being run",
        ),
        (lambda r, m: m["families"]["learned"].pop("why_not_run"), "states why"),
        # Claiming feasibility from a recovery score.
        (lambda r, m: r.update({"laboratory_feasibility": "acceptable"}), "not assessed"),
        # Giving templates a class their dataset never held erases the distinction.
        (
            lambda r, m: m["families"]["template"]["transforms"].update(
                {"suzuki-biaryl": "[c:1]-[c:2]>>[c:1][Br].[c:2]B(O)O"}
            ),
            "recover nothing in a class the precedent set never contained",
        ),
        # Or declaring a precedent class the set does not contain.
        (
            lambda r, m: r["precedent_set"]["classes_present"].append("suzuki-biaryl"),
            "exactly the classes present in the precedent set",
        ),
        # Putting an unseen route into the precedent set makes retrieval look general.
        (
            lambda r, m: r["precedent_set"]["members"].append("p09"),
            "declared classes match the classes its members actually carry",
        ),
        # A route whose recorded reactants no longer parse.
        (
            lambda r, m: r["routes"][0].update({"recorded_reactants": ["C(((", "N"]}),
            "recorded reactant",
        ),
    ],
)
def test_a_collapsed_comparison_is_rejected(loaded, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    routes, methods = loaded
    broken_routes = copy.deepcopy(routes)
    broken_methods = copy.deepcopy(methods)
    mutate(broken_routes, broken_methods)
    failures = retro.check(broken_routes, broken_methods)
    assert any(expected in failure for failure in failures), failures
