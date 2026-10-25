"""The decision rule must be complete before it is applied, and abstention must survive."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/property_decision"

# The nominal coverage is read from a FreeSolv run output. The curated public release
# withholds run outputs, so there this module skips instead of failing on a missing file.
pytestmark = pytest.mark.skipif(
    not (ROOT / "labs/freesolv/results/metrics.json").is_file(),
    reason="FreeSolv run outputs are intentionally absent from the public release",
)

_spec = importlib.util.spec_from_file_location("inspect_decision", LAB / "inspect_decision.py")
decision = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(decision)


@pytest.fixture(scope="module")
def loaded():
    return decision.load()


def test_the_committed_rule_and_evidence_pass_every_check(loaded, capsys):
    rule, results, nominal = loaded
    assert decision.check(rule, results, nominal) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 20


def test_only_one_combination_reaches_the_coverage_it_was_built_for(loaded):
    rule, results, nominal = loaded
    assert nominal == 0.9
    rows = decision.combinations(results, nominal)
    meeting = [row for row in rows if row["meets_nominal"]]
    assert len(meeting) == 1
    assert (meeting[0]["split"], meeting[0]["model"]) == ("scaffold", "morgan_random_forest")
    # And it is the widest band, not the narrowest.
    assert meeting[0]["band"] == max(row["band"] for row in rows)


def test_a_tighter_interval_is_not_a_better_interval(loaded):
    """The narrowest band has the largest shortfall, on committed numbers."""
    rule, results, nominal = loaded
    rows = decision.combinations(results, nominal)
    narrowest = min(rows, key=lambda row: row["band"])
    assert (narrowest["split"], narrowest["model"]) == ("random", "morgan_ridge")
    assert narrowest["shortfall"] == max(row["shortfall"] for row in rows)
    assert round(narrowest["shortfall"], 4) == 0.1656


def test_the_point_arm_never_abstains_and_the_interval_arm_does(loaded):
    """The whole teaching point: a number is always on one side of a threshold."""
    rule, results, nominal = loaded
    for row in decision.combinations(results, nominal):
        outcome = decision.decisions(rule, row)
        assert outcome["point_counts"]["abstain"] == 0
        assert outcome["counts"]["abstain"] > 0
        assert sum(outcome["counts"].values()) == outcome["total"]


def test_more_trustworthy_intervals_decide_less(loaded):
    """Abstention rises with the band, and the covering combination abstains most."""
    rule, results, nominal = loaded
    rows = sorted(decision.combinations(results, nominal), key=lambda row: row["band"])
    abstentions = [decision.decisions(rule, row)["counts"]["abstain"] for row in rows]
    assert abstentions == [7, 11, 11, 13]
    assert rows[-1]["meets_nominal"] is True


def test_the_two_criteria_disagree_the_same_way_on_both_splits(loaded):
    rule, results, nominal = loaded
    flips = decision.ranking_flip(decision.combinations(results, nominal))
    assert set(flips) == {"random", "scaffold"}
    assert all(flip["flipped"] for flip in flips.values())
    assert {flip["point_choice"] for flip in flips.values()} == {"morgan_ridge"}
    assert {flip["interval_choice"] for flip in flips.values()} == {"morgan_random_forest"}


def test_the_band_is_exactly_two_radii_and_matches_its_bounds(loaded):
    rule, results, nominal = loaded
    threshold = rule["threshold"]["value"]
    for row in decision.combinations(results, nominal):
        assert row["band"] == 2 * row["radius"]
        outcome = decision.decisions(rule, row)
        assert outcome["band_low"] == threshold - row["radius"]
        assert outcome["band_high"] == threshold + row["radius"]
        for point in decision.grid_points(rule):
            expected = "abstain" if abs(point - threshold) <= row["radius"] else None
            got = decision.decide_one(point, threshold, row["radius"])
            if expected:
                assert got == "abstain"
            else:
                assert got in {"advance", "reject"}


def test_runs_offline_and_states_what_it_cannot_compute():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_decision.py"), "decide"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "WHAT THIS CANNOT COMPUTE" in result.stdout
    assert "not per-compound test" in result.stdout
    assert "MORE TRUSTWORTHY INTERVALS DECIDE LESS" in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # A rule with no abstention outcome collapses to a point decision.
        (
            lambda r, s: r["decision_rule"].pop("abstain"),
            "declares an abstention outcome",
        ),
        # Presenting the threshold as derived rather than declared.
        (
            lambda r, s: r["threshold"].pop("how_this_value_was_chosen"),
            "how the threshold value was chosen",
        ),
        (lambda r, s: r.pop("prediction_grid"), "declares its prediction_grid"),
        (lambda r, s: r.pop("selection_between_models"), "declares its selection_between_models"),
        # Widening the covering model's interval so a second one appears to cover.
        (
            lambda r, s: s["splits"]["random"]["interval_metrics"]["morgan_ridge"].update(
                {"coverage": 0.95}
            ),
            "exactly one combination reaches nominal coverage",
        ),
        # Breaking the relationship the lesson quotes: narrow band, worst coverage.
        (
            lambda r, s: s["splits"]["random"]["interval_metrics"]["morgan_ridge"].update(
                {"coverage": 0.89}
            ),
            "narrowest band has the largest coverage shortfall",
        ),
        # Making the point criterion and the interval criterion agree.
        (
            lambda r, s: s["splits"]["scaffold"]["point_metrics"]["morgan_random_forest"].update(
                {"mae": 0.5}
            ),
            "disagree on every split",
        ),
        # A radius of zero removes the band, so abstention silently disappears.
        (
            lambda r, s: [
                interval.update({"radius": 0.0})
                for split in s["splits"].values()
                for interval in split["interval_metrics"].values()
            ],
            "wider than a single grid point",
        ),
    ],
)
def test_an_incomplete_rule_or_softened_evidence_is_rejected(loaded, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    rule, results, nominal = loaded
    broken_rule = copy.deepcopy(rule)
    broken_results = copy.deepcopy(results)
    mutate(broken_rule, broken_results)
    failures = decision.check(broken_rule, broken_results, nominal)
    assert any(expected in failure for failure in failures), failures


def test_an_incomplete_rule_is_never_applied_to_the_evidence(loaded, capsys):
    """A rule that cannot be applied has nothing to be applied to."""
    rule, results, nominal = loaded
    broken = copy.deepcopy(rule)
    broken["decision_rule"].pop("abstain")
    decision.check(broken, results, nominal)
    printed = capsys.readouterr().out
    assert "is not applied to the evidence" in printed
    assert "abstention band" not in printed


def test_the_threshold_value_does_not_change_the_band_width(loaded):
    """The rule says the arithmetic does not depend on the declared value."""
    rule, results, nominal = loaded
    rows = decision.combinations(results, nominal)
    moved = copy.deepcopy(rule)
    moved["threshold"]["value"] = -3.0
    for row in rows:
        original = decision.decisions(rule, row)
        shifted = decision.decisions(moved, row)
        assert shifted["band_high"] - shifted["band_low"] == pytest.approx(
            original["band_high"] - original["band_low"]
        )
