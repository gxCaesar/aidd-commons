"""The committed compact result is reproducible from the committed snapshot."""

import json
from pathlib import Path

from aidd_commons.biologic_construct_audit.analysis import audit_records, load_snapshot
from aidd_commons.biologic_construct_audit.protocol import EXPECTED_PROTOCOL
from aidd_commons.biologic_construct_audit.summary import (
    BOUNDARY,
    build_summary,
    check_summary,
    validate_summary,
)

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/biologic_construct_audit"


def test_committed_summary_matches_snapshot_and_protocol():
    artifact_path = LAB / "summary.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    snapshot = load_snapshot(LAB, EXPECTED_PROTOCOL)
    fresh = build_summary(LAB, computed_on=artifact["computed_on"])
    audit = audit_records(snapshot, EXPECTED_PROTOCOL)
    assert artifact["entity_count"] == 6
    assert artifact["entity_count"] == audit["entity_count"]
    assert artifact["per_field_counts"] == audit["per_field_counts"]
    assert artifact["per_entity"] == audit["per_entity"]
    assert artifact["source_disagreements"] == audit["source_disagreements"]
    assert artifact["source_fetched_at_utc"] == snapshot["fetched_at_utc"]
    assert artifact["boundary"] == BOUNDARY
    assert artifact["enforced_rules"]["aggregation"] == EXPECTED_PROTOCOL["aggregation_rule"]
    assert artifact["enforced_rules"]["definition"] == EXPECTED_PROTOCOL["definition_rule"]
    assert artifact["enforced_rules"]["comparison"] == EXPECTED_PROTOCOL["comparison_rule"]
    assert validate_summary(artifact) == []
    assert check_summary(LAB, artifact_path) == []
    for key in (
        "entity_count",
        "per_field_counts",
        "entities_by_fields",
        "per_entity",
        "per_source",
        "gaps",
        "source_coverage_differences",
        "source_disagreements",
    ):
        assert artifact[key] == fresh[key]
    summary_text = artifact_path.read_text(encoding="utf-8")
    assert "pharmaceutical_text" not in summary_text
    assert "description" not in summary_text
    assert "mechanism" not in summary_text
    assert "retrieved_bytes" not in summary_text


def test_false_definition_is_detected(tmp_path):
    artifact = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    row = next(item for item in artifact["per_entity"] if item["entity"] == "human-insulin-humulin")
    row["defined_construct"] = True
    output = tmp_path / "false-definition.json"
    output.write_text(json.dumps(artifact), encoding="utf-8")
    assert check_summary(LAB, output)
