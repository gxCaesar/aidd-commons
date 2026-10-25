"""The committed projection agrees with the current source records."""

import json
from pathlib import Path

from aidd_commons.claims_evidence_audit.summary import SCHEMA_VERSION, build_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/claims_evidence_audit"


def test_committed_summary_matches_live_records() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    current = build_summary(
        ROOT,
        LAB / "protocol.json",
        computed_on=artifact["computed_on"],
        software=artifact["software"],
    )
    assert artifact == current
    assert artifact["schema_version"] == SCHEMA_VERSION
    assert len(artifact["examined_provider_ids"]) == 13
    assert len(artifact["examined_topic_ids"]) == 4
    assert sum(row["direct-observation"] for row in artifact["state_counts"].values()) == 14
    assert sum(row["unresolved-field"] for row in artifact["state_counts"].values()) == 38
    assert artifact["unsupported_claims"] == []
    # The disagreements are the ones the live records show, so a raise that
    # removes one is not a failure of the laboratory.
    assert all(row["topic_id"] and row["direction"] for row in artifact["disagreements"])
    assert all(row["status"] == "not_established" for row in artifact["claims"].values())
    assert "cells" not in artifact
