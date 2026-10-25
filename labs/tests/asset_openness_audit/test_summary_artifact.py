"""The committed artifact is a compact and current projection of the audit."""

import json
from pathlib import Path

from aidd_commons.asset_openness_audit.protocol import EXAMINED_IDS
from aidd_commons.asset_openness_audit.summary import SCHEMA_VERSION, build_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/asset_openness_audit"


def test_committed_summary_matches_current_catalogue() -> None:
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    actual = build_summary(
        LAB / "protocol.json",
        ROOT / "catalog/resources",
        computed_on=artifact["computed_on"],
        software=artifact["software"],
    )
    assert artifact == actual
    assert artifact["schema_version"] == SCHEMA_VERSION
    assert artifact["examined_record_ids"] == list(EXAMINED_IDS)
    assert len(artifact["records"]) == 24
    assert all(len(row["openness"]) == 7 for row in artifact["records"])
    assert artifact["examined_counts"]["available"] == 57
    assert artifact["whole_catalogue"]["records_with_seven_separate_dimensions"] == 232
    assert "caveats" not in artifact["records"][0]
