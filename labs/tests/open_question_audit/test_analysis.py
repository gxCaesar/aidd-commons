"""The fixed vocabulary separates record states from testability."""

import copy
from pathlib import Path

import pytest
from aidd_commons.open_question_audit.analysis import analyze, check_invariants
from aidd_commons.open_question_audit.protocol import AuditError, load_protocol

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = load_protocol(ROOT / "labs/open_question_audit/protocol.json")


def constructed_bundle() -> dict:
    topics = ["open", "measured", "held", "lowered", "unexamined"]
    notes = [
        "More work is needed.",
        "The lab reports that two sites lack a measured outcome.",
        "The self record takes the shallower of the two, executable.",
        "Lowered from assessed to worked after the independent reading.",
        "",
    ]
    reasons = [
        "More work is needed.",
        "A local result was reported.",
        "No executable comparison of two controls is supplied.",
        "No runnable task tests the claim.",
        "",
    ]
    return {
        "taxonomy": {"tracks": [{"id": "test", "topics": [{"id": t} for t in topics]}]},
        "self_record": {
            "id": "aidd-commons",
            "caveats": [],
            "coverage": [
                {"topic_id": t, "depth": depth, "note": note}
                for t, depth, note in zip(
                    topics,
                    ["worked", "assessed", "executable", "worked", "worked"],
                    notes,
                    strict=True,
                )
            ],
        },
        "independent_reading": {
            "system_id": "aidd-commons",
            "reviewer": "independent",
            "isolation": "declared",
            "readings": [
                {"topic_id": t, "depth": depth, "run_basis": basis, "reason": reason}
                for t, depth, basis, reason in zip(
                    topics,
                    ["assessed", "assessed", "assessed", "worked", "worked"],
                    ["none", "authored", "real-data", "none", "none"],
                    reasons,
                    strict=True,
                )
            ],
        },
    }


def test_states_and_generic_open_question() -> None:
    result = analyze(constructed_bundle(), PROTOCOL)
    assert result["state_counts"] == {
        "open": 1,
        "settled by measurement": 1,
        "held by a reading": 1,
        "lowered by a reading": 1,
        "unexamined": 1,
    }
    assert result["open_with_falsifier"] == []
    assert result["open_without_falsifier"] == ["open"]
    assert result["lowered_topics"] == [{"topic_id": "lowered", "names_missing": True}]
    assert check_invariants(result, PROTOCOL) == []


def test_lowering_requires_self_record_correction() -> None:
    bundle = copy.deepcopy(constructed_bundle())
    bundle["self_record"]["coverage"][3]["depth"] = "assessed"
    with pytest.raises(AuditError, match="still exceeds"):
        analyze(bundle, PROTOCOL)
    bundle["self_record"]["coverage"][3]["depth"] = "worked"
    assert analyze(bundle, PROTOCOL)["state_topics"]["lowered by a reading"] == ["lowered"]
