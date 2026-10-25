"""Scores from different protocols must not become comparable by sharing units."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/docking_protocol"

_spec = importlib.util.spec_from_file_location("inspect_protocol", LAB / "inspect_protocol.py")
docking = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(docking)


@pytest.fixture(scope="module")
def data():
    return docking.load()


def test_the_committed_protocols_pass_every_check(data, capsys):
    assert docking.check(data) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 11


def test_every_protocol_declares_all_seven_components(data):
    names = set(data["components"])
    assert len(names) == 7
    for protocol in data["protocols"]:
        assert names <= set(protocol)


def test_the_cleanest_incomparable_pair_differs_in_one_component(data):
    baseline = next(p for p in data["protocols"] if p["id"] == "p-baseline")
    rescored = next(p for p in data["protocols"] if p["id"] == "p-rescored")
    assert docking.differences(data, baseline, rescored) == ["rescoring"]
    ok, blocking = docking.comparable(data, baseline, rescored)
    assert ok is False and blocking == ["rescoring"]
    # Same ligand, same structure, different number, entirely from the protocol.
    assert baseline["reported_score_for_reference_ligand"] == -8.2
    assert rescored["reported_score_for_reference_ligand"] == -10.7


def test_no_pair_in_the_set_is_comparable(data):
    from itertools import combinations

    for left, right in combinations(data["protocols"], 2):
        ok, blocking = docking.comparable(data, left, right)
        assert ok is False
        assert blocking


def test_decoys_and_validation_move_meaning_not_the_number(data):
    assert set(docking.evidence_components(data)) == {"decoys", "validation"}
    assert set(docking.scoring_components(data)) == {
        "search",
        "pose_generation",
        "scoring",
        "rescoring",
        "constraints",
    }


def test_a_protocol_without_validation_cannot_claim_its_scores_behave(data):
    unvalidated = [p for p in data["protocols"] if p["validation"] == "none"]
    assert unvalidated
    for protocol in unvalidated:
        claims = docking.unsupported_claims(data, protocol)
        assert any("never" not in line and "validated" in line for line in claims)
    validated = [p for p in data["protocols"] if p["validation"] != "none"]
    for protocol in validated:
        assert all("validated" not in line for line in docking.unsupported_claims(data, protocol))


def test_runs_offline_and_states_what_a_score_is_not():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_protocol.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "WHICH PAIRS MAY BE COMPARED" in result.stdout
    assert "THE MOST TEMPTING COMPARISON IS THE ONE TO REFUSE" in result.stdout
    assert "not comparable to a number produced by a different protocol" in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Dropping a component from a protocol leaves the score's provenance incomplete.
        (lambda d: d["protocols"][0].pop("rescoring"), "declares all seven components"),
        # Declaring rescoring not to move the number makes two scales look like one.
        (
            lambda d: d["components"]["rescoring"].update({"affects_the_number": False}),
            "move meaning rather than the number",
        ),
        # Making validation a score-affecting component confuses evidence with scale.
        (
            lambda d: d["components"]["validation"].update({"affects_the_number": True}),
            "move meaning rather than the number",
        ),
        # A component with no stated reason cannot be argued with.
        (lambda d: d["components"]["search"].pop("why"), "says why"),
        # Removing the statement of what a score is not.
        (lambda d: d.__setitem__("what_a_score_is_not", ""), "what a reported score is not"),
        # Making the baseline and rescored protocols identical erases the cleanest case.
        (
            lambda d: d["protocols"][1].update({"rescoring": "none"}),
            "differ in exactly one component",
        ),
    ],
)
def test_a_collapsed_protocol_set_is_rejected(data, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    broken = copy.deepcopy(data)
    mutate(broken)
    failures = docking.check(broken)
    assert any(expected in failure for failure in failures), failures
