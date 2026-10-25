"""The committed summary agrees with the cached computation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aidd_commons.crossdomain_tradeoff.protocol import load_protocol_document
from aidd_commons.crossdomain_tradeoff.summary import build_summary, check_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs" / "crossdomain_tradeoff"


@pytest.mark.skipif(
    not (ROOT / ".cache/decision_unit_scope").is_dir(),
    reason="the ChEMBL source snapshots are not cached",
)
def test_the_committed_summary_matches_the_cached_computation() -> None:
    """The committed artefact is the computation, not a hand-written number."""
    committed = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    computed = build_summary(ROOT / ".cache", computed_on=committed["computed_on"])
    check_summary(committed, computed)


def test_the_protocol_document_is_the_frozen_one() -> None:
    """The protocol is the contract, and the contract is checked before the run."""
    document = load_protocol_document(LAB / "protocol.json")
    assert document["protocol_id"] == "chembl37-crossdomain-tradeoff-v1"
    assert len(document["inputs"]) == 5
    assert len(document["teaching_cases"]) == 3


def test_the_summary_states_the_counts_the_readme_states() -> None:
    """The numbers a reader is told are the numbers the summary carries."""
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert summary["teaching_blocking_counts"] == {
        "selectivity_ratio": 1,
        "exposure_ratio": 1,
        "safety_package": 1,
    }
    assert summary["teaching_next_decision_counts"] == {
        "revise the candidate": 2,
        "close an evidence gap": 1,
    }
    assert summary["teaching_complete_count"] == 0
    assert summary["measured_candidate_count"] == 58
    assert summary["measured_blocking_counts"] == {"potency": 58}
    assert summary["measured_next_decision_counts"] == {"close an evidence gap": 58}
    assert summary["measured_complete_count"] == 0
    assert summary["measured_input_state_counts"] == {
        "potency": {"absent": 57, "indeterminate": 1},
        "selectivity_ratio": {"not covered": 58},
        "exposure_ratio": {"not covered": 58},
        "safety_package": {"not covered": 58},
        "functional_validation": {"not covered": 58},
    }


def test_the_summary_carries_no_score_and_no_ordering() -> None:
    """A composite or a ranking is what the laboratory refuses to produce."""
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    text = json.dumps(summary)
    assert '"score"' not in text
    assert '"rank"' not in text
    assert summary["boundary_statement"]
    assert summary["rules"]["composite_score"]
