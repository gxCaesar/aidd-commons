"""The committed count table must still match the local records."""

from __future__ import annotations

import json
from pathlib import Path

from aidd_commons.agent_evaluation_taskset.protocol import DIMENSIONS, load_protocol
from aidd_commons.agent_evaluation_taskset.summary import (
    SCHEMA_VERSION,
    build_summary,
    validate_summary,
)

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/agent_evaluation_taskset"


def test_committed_summary_matches_live_records() -> None:
    protocol = load_protocol(LAB / "protocol.json")
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    current = build_summary(
        ROOT,
        LAB / "protocol.json",
        computed_on=artifact["computed_on"],
        software=artifact["software"],
    )
    validate_summary(artifact, protocol)
    assert artifact == current
    assert artifact["schema_version"] == SCHEMA_VERSION
    assert artifact["task_count"] == len(protocol["tasks"])
    assert set(artifact["dimension_pass_counts"]) == set(DIMENSIONS)
    assert artifact["dimension_pass_counts"] == {
        name: sum(row["dimensions"][name] == "pass" for row in artifact["per_task"])
        for name in DIMENSIONS
    }
    assert artifact["passing_task_count"] == 0
    assert all("answers" not in row and "contexts" not in row for row in artifact["per_task"])
