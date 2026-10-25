"""Contract mutations fail before creating a summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.functional_validation_audit.protocol import ProtocolError, load_protocol
from aidd_commons.functional_validation_audit.summary import export_summary

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/functional_validation_audit/protocol.json"


@pytest.mark.parametrize(
    ("section", "key", "replacement"),
    [
        (None, "protocol_id", "changed"),
        ("admitted_measurement", "standard_units", "uM"),
        ("admitted_measurement", "bound_relations", []),
        ("record_kinds", "concentration_response_table", "any numeric row"),
        ("claim_rule", "clinical_outcome", "assumed from response"),
        (None, "unmeasurable_routes", {}),
        (None, "excluded_by_design", []),
    ],
)
def test_mutation_is_refused_without_output(
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
        export_summary(lab, tmp_path / "missing-chembl", tmp_path / "missing-pubchem", output)
    assert not output.exists()
    with pytest.raises(ProtocolError):
        load_protocol(lab / "protocol.json")
