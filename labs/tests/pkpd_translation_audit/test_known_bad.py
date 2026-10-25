"""Consequential contract edits are refused before any summary is written."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from aidd_commons.pkpd_translation_audit.protocol import (
    ProtocolError,
    expected_protocol,
    load_protocol,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("section", "key", "replacement"),
    [
        ("source", "snapshot_bytes", 1),
        ("source", "licence", "unverified"),
        ("model", "translation_rule", "fixed rat-to-human factor"),
        ("counted_unit", "modelled_if", "any assay"),
        ("top", "excluded_by_design", []),
    ],
)
def test_bad_protocol_edit_leaves_no_output(
    tmp_path: Path, section: str, key: str, replacement: object
) -> None:
    document = deepcopy(expected_protocol())
    target = document if section == "top" else document[section]
    target[key] = replacement
    protocol_path = tmp_path / "protocol.json"
    output = tmp_path / "summary.json"
    protocol_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProtocolError):
        load_protocol(protocol_path)
    from aidd_commons.pkpd_translation_audit.summary import build_summary

    with pytest.raises(ProtocolError):
        result = build_summary(protocol_path, ROOT / ".cache/az_clearance_system")
        output.write_text(json.dumps(result), encoding="utf-8")
    assert not output.exists()


def test_unsourced_parameter_edit_leaves_no_output(tmp_path: Path) -> None:
    document = deepcopy(expected_protocol())
    document["model"]["parameters"]["emax"]["source"] = ""
    protocol_path = tmp_path / "protocol.json"
    output = tmp_path / "summary.json"
    protocol_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ProtocolError):
        load_protocol(protocol_path)
    assert not output.exists()
