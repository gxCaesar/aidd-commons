"""The committed projection agrees with a fresh catalogue computation."""

import json
from pathlib import Path

from aidd_commons.relational_graph_audit.summary import SCHEMA_VERSION, build_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/relational_graph_audit"


def test_committed_summary_matches_catalogue() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    actual = build_summary(
        LAB / "protocol.json",
        ROOT / "catalog/resources",
        computed_on=artifact["computed_on"],
        software=artifact["software"],
    )
    assert artifact == actual
    assert artifact["schema_version"] == SCHEMA_VERSION
    assert artifact["node_count"] == sum(artifact["node_counts_by_kind"].values())
    assert artifact["edge_count"] == sum(artifact["edge_counts_by_type"].values())
    assert artifact["edge_count"] == (
        artifact["evidenced_edge_count"] + artifact["unevidenced_edge_count"]
    )
    assert artifact["candidate_edge_count"] == 10560
    assert "records" not in artifact
