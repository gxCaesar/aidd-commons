"""The five kinds of safety evidence must stay separated, and alerts must stay computed."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/safety_evidence"

_spec = importlib.util.spec_from_file_location("inspect_safety", LAB / "inspect_safety.py")
safety = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(safety)


@pytest.fixture(scope="module")
def data():
    return safety.load()


def test_the_committed_record_passes_every_check(data, capsys):
    assert safety.check(data) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 14


def test_alerts_are_computed_and_never_stored(data):
    """Storing an alert beside a measurement is the collapse the lab is about."""
    source = (LAB / "dataset.json").read_text(encoding="utf-8")
    assert '"alerts": [' not in source
    for compound in data["compounds"]:
        assert set(compound) == {"id", "smiles", "findings"}
        for row in compound["findings"]:
            assert row["level"] in safety.MEASURED_LEVELS
    # Recomputing gives a non-trivial split rather than everything or nothing.
    fired = {c["id"]: safety.alerts_for(data, c["smiles"]) for c in data["compounds"]}
    assert 0 < len([k for k, v in fired.items() if v]) < len(fired)


def test_most_alerting_compounds_were_never_measured(data):
    rows = [safety.profile(data, compound) for compound in data["compounds"]]
    alerting = [row for row in rows if row["alerts"]]
    silent = [row for row in alerting if row["findings"] == 0]
    assert len(alerting) == 7
    assert [row["id"] for row in silent] == ["c03", "c04", "c05", "c06", "c07"]


def test_the_alert_count_can_rise_without_evidence(data):
    rows = {row["id"]: row for row in (safety.profile(data, c) for c in data["compounds"])}
    assert rows["c05"]["alert_count"] == 2
    assert rows["c05"]["findings"] == 0


def test_the_levels_disagree_in_both_directions(data):
    both = safety.disagreements(data)
    assert both["alert_contradicted"] == ["c01"]
    assert both["alert_untested"] == ["c03", "c04", "c05", "c06", "c07"]
    assert both["positive_without_alert"] == ["c08", "c09"]


def test_a_contradicted_alert_is_kept_apart_from_an_unchecked_one(data):
    """Different situations: one was tested and lost, the other was never tested."""
    both = safety.disagreements(data)
    assert set(both["alert_contradicted"]) & set(both["alert_untested"]) == set()
    contradicted = next(c for c in data["compounds"] if c["id"] == both["alert_contradicted"][0])
    assert contradicted["findings"]
    for identifier in both["alert_untested"]:
        untested = next(c for c in data["compounds"] if c["id"] == identifier)
        assert untested["findings"] == []


def test_dose_context_is_missing_and_said_to_be_missing(data):
    assays = [
        row
        for compound in data["compounds"]
        for row in safety.findings_at(compound, "assay-outcome")
    ]
    missing = [row for row in assays if row["concentration_micromolar"] is None]
    assert (len(missing), len(assays)) == (2, 7)
    assert data["exposure"]["declared"] is False
    assert data["exposure"]["why_it_matters"]


def test_the_top_level_is_nearly_empty(data):
    rows = [safety.profile(data, compound) for compound in data["compounds"]]
    top = [row for row in rows if row["has_organism_level"]]
    assert [row["id"] for row in top] == ["c10"]


def test_runs_offline_and_refuses_to_assess_anything():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_safety.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "AN ALERT IS NOT A FINDING" in result.stdout
    assert "WITHOUT A DOSE CONTEXT" in result.stdout
    assert "It assesses nothing" in result.stdout
    assert "does not say alerts are useless" in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Writing an alert into a compound record is the collapse itself.
        (lambda d: d["compounds"][0].update({"alerts": ["nitroaromatic"]}), "stores an alert"),
        # Recording a finding against an alert name rather than an assay system.
        (
            lambda d: d["compounds"][0]["findings"][0].update({"system": "nitroaromatic"}),
            "no finding is recorded against one",
        ),
        # Declaring the alert level to require an experiment hides that it is free.
        (
            lambda d: d["levels"]["molecular-alert"].update({"computed_here": False}),
            "only the alert level is computed here",
        ),
        # Giving every assay outcome a concentration hides the comparability gap.
        (
            lambda d: [
                row.update({"concentration_micromolar": 10.0})
                for c in d["compounds"]
                for row in c["findings"]
                if row["level"] == "assay-outcome"
            ],
            "carry no concentration",
        ),
        # Declaring an exposure that the record does not contain.
        (lambda d: d["exposure"].update({"declared": True}), "no exposure is declared"),
        # Measuring every alerting compound removes the point that alerts are free.
        (
            lambda d: [
                c["findings"].append(
                    {
                        "level": "assay-outcome",
                        "system": "hepatocyte viability",
                        "outcome": "negative",
                        "concentration_micromolar": 10.0,
                    }
                )
                for c in d["compounds"]
                if c["id"] in {"c03", "c04", "c05", "c06", "c07"}
            ],
            "carry no measured finding at all",
        ),
        # A broken alert pattern silently stops matching.
        (
            lambda d: d["alerts"]["patterns"].update({"epoxide": "C1OC1))"}),
            "alert pattern compiles",
        ),
    ],
)
def test_a_collapsed_record_is_rejected(data, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    broken = copy.deepcopy(data)
    mutate(broken)
    failures = safety.check(broken)
    assert any(expected in failure for failure in failures), failures
