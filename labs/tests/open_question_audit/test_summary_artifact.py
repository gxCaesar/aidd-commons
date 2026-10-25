"""The committed projection agrees with the current three source records."""

import json
from pathlib import Path

from aidd_commons.open_question_audit.summary import SCHEMA_VERSION, build_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/open_question_audit"


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
    assert artifact["topic_count"] == 93
    assert sum(artifact["state_counts"].values()) == 93
    assert artifact["open_with_falsifier"] == [
        topic
        for topic in artifact["state_topics"]["open"]
        if topic not in artifact["open_without_falsifier"]
    ]
    assert artifact["boundary_statement"] and artifact["enforced_rules"]
    assert "rows" not in artifact
