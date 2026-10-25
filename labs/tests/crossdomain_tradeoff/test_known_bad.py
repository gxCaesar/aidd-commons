"""The known-bad cases the decision laboratory must refuse."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.crossdomain_tradeoff.analysis import audit_decisions, decide_teaching_case
from aidd_commons.crossdomain_tradeoff.protocol import (
    TEACHING_CASES,
    ProtocolContractError,
    load_protocol_document,
)

LAB = Path(__file__).resolve().parents[2] / "crossdomain_tradeoff"


def test_a_protocol_that_relaxes_a_threshold_is_refused(tmp_path: Path) -> None:
    """The thresholds are frozen, so a document that moves one is not the protocol."""
    document = json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))
    document["inputs"][0]["threshold"]["maximum_nm"] = 5000.0
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    with pytest.raises(ProtocolContractError):
        load_protocol_document(path)


def test_a_protocol_that_adds_an_input_is_refused(tmp_path: Path) -> None:
    """The rule names five inputs, and a sixth is a different rule."""
    document = json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))
    document["inputs"].append({"name": "synthesis", "state_rule": "not covered", "threshold": None})
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    with pytest.raises(ProtocolContractError):
        load_protocol_document(path)


def test_a_decision_that_orders_the_candidates_is_refused() -> None:
    """A ranking is not a decision."""
    decisions = [decide_teaching_case(case) for case in TEACHING_CASES]
    tampered = [dict(row) for row in decisions]
    tampered[0]["rank"] = 1
    with pytest.raises(ValueError):
        audit_decisions(tampered)


def test_a_decision_that_names_a_blocking_input_that_passes_is_refused() -> None:
    """The blocking input must be one the candidate does not meet."""
    decisions = [decide_teaching_case(case) for case in TEACHING_CASES]
    tampered = [dict(row) for row in decisions]
    tampered[0]["blocking_input"] = "potency"
    with pytest.raises(ValueError):
        audit_decisions(tampered)


def test_a_decision_that_marks_a_candidate_complete_despite_a_gap_is_refused() -> None:
    """Completeness follows the inputs, not the reader's preference."""
    decisions = [decide_teaching_case(case) for case in TEACHING_CASES]
    tampered = [dict(row) for row in decisions]
    tampered[2]["complete"] = True
    with pytest.raises(ValueError):
        audit_decisions(tampered)


def test_a_decision_that_points_at_changing_the_requirement_is_refused() -> None:
    """Changing a threshold is a change to the requirement."""
    decisions = [decide_teaching_case(case) for case in TEACHING_CASES]
    tampered = [dict(row) for row in decisions]
    tampered[0]["next_decision"] = "change the product profile"
    with pytest.raises(ValueError):
        audit_decisions(tampered)
