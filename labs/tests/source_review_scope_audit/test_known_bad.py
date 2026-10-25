"""Changed contracts and broken references cannot produce a summary."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.source_review_scope_audit import summary
from aidd_commons.source_review_scope_audit.analysis import AuditError
from aidd_commons.source_review_scope_audit.protocol import ProtocolError
from aidd_commons.source_review_scope_audit.records import load_catalogue

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/source_review_scope_audit/protocol.json"


@pytest.mark.parametrize("mutation", ["field_rule", "rule_text", "record_id", "route"])
def test_changed_protocol_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    altered = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "field_rule":
        altered["parts"]["date"]["field"] = "last_verified"
    elif mutation == "rule_text":
        altered["parts"]["date"]["rule"] = "Count dates in the label as carried"
    elif mutation == "record_id":
        altered["examined_record_ids"][0] = "no-such-record"
    else:
        altered["unmeasurable_routes"].pop(0)
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
    "mutation",
    ["duplicate_entry", "missing_reference", "missing_dimension", "invalid_date", "invalid_url"],
)
def test_changed_record_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    catalogue = copy.deepcopy(load_catalogue(ROOT / "catalog/resources"))
    record = catalogue["model-boltz-2"]
    if mutation == "duplicate_entry":
        record["evidence"].append(copy.deepcopy(record["evidence"][0]))
    elif mutation == "missing_reference":
        record["openness"]["weights"]["evidence"] = ["never-recorded"]
    elif mutation == "missing_dimension":
        del record["openness"]["weights"]
    elif mutation == "invalid_date":
        record["evidence"][0]["reviewed_on"] = "2026-02-30"
    else:
        record["evidence"][0]["url"] = "not-a-url"
    monkeypatch.setattr(summary, "load_catalogue", lambda *_: catalogue)
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        summary.build_summary(ROOT, PROTOCOL, output=output)
    assert not output.exists()
