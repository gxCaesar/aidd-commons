"""A larger space must not be mistaken for a space that reaches more chemistry."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/design_space"

_spec = importlib.util.spec_from_file_location("inspect_space", LAB / "inspect_space.py")
design = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(design)


@pytest.fixture(scope="module")
def data():
    return design.load()


def test_the_committed_spaces_pass_every_check(data, capsys):
    assert design.check(data) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 13


def test_sizes_are_enumerated_rather_than_stated(data):
    spaces = {name: design.enumerate_space(spec) for name, spec in data["spaces"].items()}
    assert spaces["enumeration"]["nominal"] == 25
    assert spaces["enumeration_grown"]["nominal"] == 100
    assert spaces["scaffold_hop"]["nominal"] == 25
    for name, block in spaces.items():
        spec = data["spaces"][name]
        assert block["nominal"] == len(spec["r1"]) * len(spec["r2"])
        assert block["unbuildable"] == 0
        assert block["distinct"] == len(block["members"])


def test_growing_a_space_buys_more_of_the_same_reach(data):
    table = design.reach(data)
    gained = [k for k, row in table.items() if row["enumeration_grown"] and not row["enumeration"]]
    never = [
        k for k, row in table.items() if not row["enumeration"] and not row["enumeration_grown"]
    ]
    assert gained == ["t2"]
    assert never == ["t3", "t4"]
    # The core never changed, which is why the second group stays out at any size.
    assert data["spaces"]["enumeration"]["core"] == data["spaces"]["enumeration_grown"]["core"]


def test_two_spaces_of_equal_size_can_be_disjoint(data):
    spaces = {name: design.enumerate_space(spec) for name, spec in data["spaces"].items()}
    assert spaces["scaffold_hop"]["nominal"] == spaces["enumeration"]["nominal"]
    assert not (spaces["scaffold_hop"]["members"] & spaces["enumeration"]["members"])
    assert not (spaces["scaffold_hop"]["members"] & spaces["enumeration_grown"]["members"])


def test_a_different_construction_reaches_different_chemistry(data):
    table = design.reach(data)
    assert table["t3"]["scaffold_hop"] is True
    assert table["t3"]["enumeration"] is False
    assert table["t3"]["enumeration_grown"] is False


def test_one_target_is_reachable_nowhere(data):
    table = design.reach(data)
    assert [k for k, row in table.items() if not any(row.values())] == ["t4"]


def test_runs_offline_and_states_that_reachable_is_not_makeable():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_space.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "SIZE DOES NOT BUY REACH" in result.stdout
    assert "WHAT REACHABILITY IS NOT" in result.stdout
    assert "A space is a generator, not a plan." in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Changing the grown space's core makes the size comparison meaningless.
        (
            lambda d: d["spaces"]["enumeration_grown"].update(
                {"core": "O=C(N[*:1])c1ccc([*:2])nc1"}
            ),
            "shares the core",
        ),
        # Making the third space larger confuses construction with size.
        (
            lambda d: d["spaces"]["scaffold_hop"]["r1"].extend(["CCCC", "CCCCC"]),
            "same nominal size as the first",
        ),
        # Giving the third space the original core removes the disjointness.
        (
            lambda d: d["spaces"]["scaffold_hop"].update({"core": "O=C(N[*:1])c1ccc([*:2])cc1"}),
            "differs in construction rather than in size",
        ),
        # A space that states no limit invites being read as unlimited.
        (lambda d: d["spaces"]["enumeration"].pop("cannot_reach"), "what it cannot reach"),
        # An unbuildable input would make the space quietly smaller than its size.
        (
            lambda d: d["spaces"]["enumeration"]["r2"].append("C((("),
            "every declared product builds",
        ),
        # Removing the target nothing reaches hides that these are three constructions
        # among many rather than a survey of chemistry.
        (
            lambda d: d.__setitem__("targets", [t for t in d["targets"] if t["id"] != "t4"]),
            "reachable in none of the declared spaces",
        ),
        (
            lambda d: d.__setitem__("what_reachability_is_not", ""),
            "reachable does not mean makeable",
        ),
    ],
)
def test_a_misleading_space_comparison_is_rejected(data, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    broken = copy.deepcopy(data)
    mutate(broken)
    failures = design.check(broken)
    assert any(expected in failure for failure in failures), failures
