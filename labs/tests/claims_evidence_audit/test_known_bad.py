"""Known defects are refused before a summary artifact can be created."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.claims_evidence_audit import summary
from aidd_commons.claims_evidence_audit.analysis import AuditError
from aidd_commons.claims_evidence_audit.protocol import ProtocolError, load_protocol
from aidd_commons.claims_evidence_audit.records import load_sources

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/claims_evidence_audit/protocol.json"


@pytest.mark.parametrize("mutation", ["track", "state_rule"])
def test_changed_protocol_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    altered = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "track":
        altered["track"]["topic_ids"].pop()
    else:
        altered["state_rules"]["unresolved-field"] = "Treat defaults as absence"
    original_read = Path.read_text

    def changed_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == PROTOCOL:
            return json.dumps(altered)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", changed_read)
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        summary.build_summary(ROOT, PROTOCOL, output=output)
    assert not output.exists()


@pytest.mark.parametrize(
    "mutation", ["no_evidence", "undeclared_evidence", "missing_file", "count", "reading"]
)
def test_changed_source_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    protocol = load_protocol(PROTOCOL)
    bundle = copy.deepcopy(load_sources(ROOT, protocol))
    provider = bundle["providers"]["aidd-commons"]
    cell = provider["coverage"][0]
    if mutation == "no_evidence":
        cell["evidence"] = []
        bundle["comparison"]["rows"] = [
            {**row, "evidence": []}
            if row["provider_id"] == "aidd-commons" and row["topic_id"] == cell["topic_id"]
            else row
            for row in bundle["comparison"]["rows"]
        ]
    elif mutation == "undeclared_evidence":
        cell["evidence"] = ["no-such-evidence"]
        bundle["comparison"]["rows"] = [
            {**row, "evidence": [{"evidence_id": "no-such-evidence"}]}
            if row["provider_id"] == "aidd-commons" and row["topic_id"] == cell["topic_id"]
            else row
            for row in bundle["comparison"]["rows"]
        ]
    elif mutation == "missing_file":
        identifier = cell["evidence"][0]
        entry = next(row for row in provider["evidence"] if row["id"] == identifier)
        entry["repository_path"] = "no-such-comparison-evidence.txt"
    elif mutation == "count":
        bundle["comparison"]["observations"]["direct_cells"] += 1
    else:
        reading = next(
            row for row in bundle["reading"]["readings"] if row["topic_id"] == cell["topic_id"]
        )
        reading["depth"] = "explained"
    monkeypatch.setattr(summary, "load_sources", lambda *_: bundle)
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        summary.build_summary(ROOT, PROTOCOL, output=output)
    assert not output.exists()
