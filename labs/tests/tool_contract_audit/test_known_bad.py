"""Changed protocols and malformed local returns are refused before export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.tool_contract_audit.analysis import AuditError, load_records
from aidd_commons.tool_contract_audit.protocol import ProtocolError, expected_fields, load_protocol
from aidd_commons.tool_contract_audit.summary import export_summary

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        ("source", "return_glob", "*/result.json"),
        ("schema", "rule", "accept anything"),
        ("version", "fields", []),
        ("environment", "unavailable", []),
        ("side_effects", "field", "writes"),
        ("error_states", "must_stop", []),
        ("scientific_meaning", "required", []),
        ("top", "excluded_by_design", []),
    ],
)
def test_changed_protocol_leaves_no_output(
    tmp_path: Path, section: str, field: str, replacement: Any
) -> None:
    document = expected_fields()
    target = (
        document if section == "top" else document.get(section, document["contract"].get(section))
    )
    assert isinstance(target, dict)
    target[field] = replacement
    lab = tmp_path / "lab"
    lab.mkdir()
    (lab / "protocol.json").write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        load_protocol(lab / "protocol.json")
    with pytest.raises(ProtocolError):
        export_summary(lab, ROOT / "labs", output)
    assert not output.exists()


@pytest.mark.parametrize("payload", ["{", "[]", "null"])
def test_malformed_return_leaves_no_output(tmp_path: Path, payload: str) -> None:
    lab = tmp_path / "lab"
    lab.mkdir()
    (lab / "protocol.json").write_text(json.dumps(expected_fields()), encoding="utf-8")
    source = tmp_path / "sources"
    (source / "broken").mkdir(parents=True)
    (source / "broken" / "summary.json").write_text(payload, encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        load_records(source, expected_fields()["source"])
    with pytest.raises(AuditError):
        export_summary(lab, source, output)
    assert not output.exists()
