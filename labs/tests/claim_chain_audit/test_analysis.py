"""Constructed links exercise resolution and the ordinal minimum."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from aidd_commons.claim_chain_audit.analysis import analyze, check_invariants
from aidd_commons.claim_chain_audit.protocol import CHAINS, load_protocol

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = load_protocol(ROOT / "labs/claim_chain_audit/protocol.json")


def constructed_records() -> dict[str, dict[str, Any]]:
    topics = list(dict.fromkeys(topic for chain in CHAINS.values() for topic in chain))
    return {
        "taxonomy": {"tracks": [{"id": "teaching", "topics": [{"id": x} for x in topics]}]},
        "self_record": {
            "id": "aidd-commons",
            "coverage": [
                {"topic_id": x, "depth": "assessed", "run_basis": "authored", "evidence": [x]}
                for x in topics
            ],
            "evidence": [
                {"id": x, "access": "opened", "repository_path": "README.md"} for x in topics
            ],
        },
        "independent_reading": {
            "system_id": "aidd-commons",
            "readings": [
                {"topic_id": x, "depth": "assessed", "run_basis": "authored"} for x in topics
            ],
        },
    }


def test_non_opened_evidence_breaks_chain() -> None:
    records = constructed_records()
    first = CHAINS["candidate-evidence"][0]
    entry = next(x for x in records["self_record"]["evidence"] if x["id"] == first)
    entry["access"] = "unverified"
    result = analyze(records, PROTOCOL, ROOT)
    chain = result["chains"][0]
    assert chain["links"][0]["state"] == "unresolved"
    assert chain["weakest_link"] == {"topic_id": first, "depth": "unresolved"}
    assert chain["supported_claim"] is False
    assert chain["link_state_counts"]["unresolved"] == 1
    assert check_invariants(result, PROTOCOL) == []

    empty = copy.deepcopy(records)
    empty["self_record"]["coverage"][0]["evidence"] = []
    assert analyze(empty, PROTOCOL, ROOT)["chains"][0]["supported_claim"] is False


def test_weakest_link_is_minimum_not_average() -> None:
    records = constructed_records()
    first = CHAINS["candidate-evidence"][0]
    records["self_record"]["coverage"][0]["depth"] = "worked"
    records["self_record"]["coverage"][0]["run_basis"] = "none"
    result = analyze(records, PROTOCOL, ROOT)
    chain = result["chains"][0]
    assert chain["weakest_link"] == {"topic_id": first, "depth": "worked"}
    assert chain["below_strongest_count"] == 1
    assert chain["link_state_counts"]["assessed"] == 7
    assert chain["supported_claim"] is True
    assert check_invariants(result, PROTOCOL) == []


def test_assessed_without_runnable_basis_licenses_only_written_work() -> None:
    records = constructed_records()
    first = records["self_record"]["coverage"][0]
    first["run_basis"] = "none"
    result = analyze(records, PROTOCOL, ROOT)
    link = result["chains"][0]["links"][0]
    assert link["state"] == "worked"
    assert link["licence"] == "A worked case or written exercise, not a measurement"
