"""Mutated contracts fail before an output artifact can be written."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.generalization_unit_audit.protocol import ProtocolError, load_protocol
from aidd_commons.generalization_unit_audit.summary import export_summary

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/generalization_unit_audit/protocol.json"


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        (None, "protocol_id", "changed"),
        ("cohort", "resolved_parents", []),
        ("endpoint", "standard_units", "uM"),
        ("endpoint", "exclusion_priority", []),
        (None, "candidate_units", []),
        (None, "units_table_cannot_name", []),
        (None, "measurement_rule", {}),
        (None, "rdkit_version", "0.0.0"),
        (None, "artifacts", []),
        (None, "excluded_by_design", []),
    ],
)
def test_known_bad_protocol_leaves_no_output(
    tmp_path: Path, section: str | None, field: str, replacement: Any
) -> None:
    lab = tmp_path / "lab"
    lab.mkdir()
    document = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    target = document if section is None else document[section]
    target[field] = replacement
    (lab / "protocol.json").write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        export_summary(lab, tmp_path / "missing-cache", output)
    assert not output.exists()
    with pytest.raises(ProtocolError):
        load_protocol(lab / "protocol.json")
