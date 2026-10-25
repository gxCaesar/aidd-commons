"""The committed summary is the current compact projection of the three records."""

from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.claim_chain_audit.summary import SCHEMA_VERSION, build_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/claim_chain_audit"


def test_committed_summary_matches_records() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    current = build_summary(
        ROOT,
        LAB / "protocol.json",
        computed_on=artifact["computed_on"],
        software=artifact["software"],
    )
    assert artifact == current
    assert artifact["schema_version"] == SCHEMA_VERSION
    assert len(artifact["chains"]) == 2
    assert sum(x["link_count"] for x in artifact["chains"]) == 16
    assert all(sum(x["link_state_counts"].values()) == x["link_count"] for x in artifact["chains"])
    assert artifact["total_disagreement_links"] == sum(
        x["disagreement_count"] for x in artifact["chains"]
    )
    assert all(x["claim_scope"] == "named-topic-material-only" for x in artifact["chains"])
    assert all("links" not in x and "evidence_ids" not in x for x in artifact["chains"])
