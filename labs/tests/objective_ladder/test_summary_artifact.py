"""The committed summary: what it must hold, checked without a network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[2] / "objective_ladder"
SUMMARY_PATH = LAB / "summary.json"
PROTOCOL_PATH = LAB / "protocol.json"

pytestmark = pytest.mark.skipif(
    not SUMMARY_PATH.exists(), reason="the summary has not been computed on this machine"
)


@pytest.fixture(scope="module")
def summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_the_summary_names_the_protocol_it_was_computed_under(summary, protocol) -> None:
    assert summary["protocol_id"] == protocol["protocol_id"]
    assert summary["schema_version"] == "aidd-commons.objective-ladder-summary.v1"


def test_the_summary_carries_a_computation_date_and_its_software(summary) -> None:
    assert summary["computed_on"]
    assert summary["software"]
    assert summary["software"].get("python")


def test_every_target_carries_one_outcome_per_declared_objective(summary, protocol) -> None:
    objectives = protocol["objectives"]
    assert len(summary["targets"]) == len(protocol["targets"])
    for target in summary["targets"]:
        assert [outcome["objective"] for outcome in target["outcomes"]] == objectives
        assert target["evidenced_objectives"] + target["empty_objectives"] == len(objectives)


def test_the_counts_agree_with_the_targets(summary) -> None:
    counts = summary["counts"]
    assert counts["targets"] == len(summary["targets"])
    assert counts["objectives"] == len(summary["objectives"])
    assert counts["cells"] == counts["targets"] * counts["objectives"]
    filled = sum(target["evidenced_objectives"] for target in summary["targets"])
    assert counts["filled_cells"] == filled
    assert counts["empty_cells"] == counts["cells"] - filled
    for index, name in enumerate(summary["objectives"]):
        recorded = sum(1 for target in summary["targets"] if target["outcomes"][index]["found"])
        assert counts["filled_per_objective"][name] == recorded


def test_a_filled_cell_names_a_record_and_an_empty_cell_names_a_reason(summary) -> None:
    for target in summary["targets"]:
        for outcome in target["outcomes"]:
            if outcome["found"]:
                assert outcome["record"]
                assert not outcome["absence_reason"]
            else:
                assert not outcome["record"]
                assert outcome["absence_reason"]
                assert outcome["detail"]


def test_the_summary_is_small_and_carries_no_archive_payload(summary) -> None:
    text = SUMMARY_PATH.read_text(encoding="utf-8")
    assert len(text) < 200_000
    for target in summary["targets"]:
        for outcome in target["outcomes"]:
            assert "coordinates" not in outcome["record"].lower()
