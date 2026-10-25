"""Mutated frozen fields fail before a summary artifact can be produced."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.split_leakage_audit.protocol import ProtocolError, load_protocol
from aidd_commons.split_leakage_audit.summary import export_summary

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/split_leakage_audit/protocol.json"


@pytest.mark.parametrize(
    ("section", "key", "replacement"),
    [
        ("split", "seed", 9),
        ("split", "train_fraction", 0.9),
        ("endpoint", "standard_units", "uM"),
        ("cohort", "resolved_parents", []),
        ("source", "release_date", "2026-01-01"),
        (None, "rdkit_version", "0.0.0"),
        (None, "tested_routes", []),
        (None, "untestable_routes", []),
        (None, "artifacts", []),
        (None, "excluded_by_design", []),
    ],
)
def test_known_bad_protocol_leaves_no_output(
    tmp_path: Path, section: str | None, key: str, replacement: Any
) -> None:
    lab = tmp_path / "lab"
    lab.mkdir()
    document = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    target = document if section is None else document[section]
    target[key] = replacement
    (lab / "protocol.json").write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        export_summary(lab, tmp_path / "missing-cache", output)
    assert not output.exists()
    with pytest.raises(ProtocolError):
        load_protocol(lab / "protocol.json")
