"""Defective protocol and evidence must fail before any summary is written."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.asset_openness_audit import summary
from aidd_commons.asset_openness_audit.analysis import AuditError
from aidd_commons.asset_openness_audit.protocol import ProtocolError
from aidd_commons.asset_openness_audit.records import load_catalogue

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/asset_openness_audit/protocol.json"
CATALOGUE = ROOT / "catalog/resources"


@pytest.mark.parametrize("mutation", ["dimension", "unknown_id", "review_rule", "licence_fields"])
def test_changed_protocol_refused_without_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    altered = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "dimension":
        altered["dimensions"].pop()
    elif mutation == "unknown_id":
        altered["examined_record_ids"][0] = "model-no-such-record"
    elif mutation == "review_rule":
        altered["review_date_rule"] = "any text"
    else:
        altered["claim_values"]["license_fields"].remove("scope")
    original_read = Path.read_text

    def changed_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == PROTOCOL:
            return json.dumps(altered)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", changed_read)
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        summary.build_summary(PROTOCOL, CATALOGUE, output=output)
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["collapsed", "missing_evidence", "unscoped_licence"])
def test_changed_record_refused_without_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    catalogue = copy.deepcopy(load_catalogue(CATALOGUE))
    record = catalogue["model-boltz-2"]
    if mutation == "collapsed":
        del record["openness"]["weights"]
    elif mutation == "missing_evidence":
        record["openness"]["weights"]["evidence"] = ["never-recorded"]
    else:
        record["licenses"][0]["scope"] = ""
    monkeypatch.setattr(summary, "load_catalogue", lambda *_: catalogue)
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        summary.build_summary(PROTOCOL, CATALOGUE, output=output)
    assert not output.exists()
