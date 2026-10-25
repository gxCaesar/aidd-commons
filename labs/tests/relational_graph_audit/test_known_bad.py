"""Known defects stop export before any artifact is written."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.relational_graph_audit import summary
from aidd_commons.relational_graph_audit.analysis import AuditError
from aidd_commons.relational_graph_audit.graph import GraphError, load_catalogue
from aidd_commons.relational_graph_audit.protocol import ProtocolError

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/relational_graph_audit/protocol.json"
CATALOGUE = ROOT / "catalog/resources"


@pytest.mark.parametrize("mutation", ["kind", "edge_type", "candidate_rule"])
def test_changed_protocol_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    altered = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "kind":
        altered["node_types"].pop()
    elif mutation == "edge_type":
        altered["edge_types"].pop()
    else:
        altered["candidate_edge_rule"] = "Guess the missing relation"
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


@pytest.mark.parametrize(
    "mutation",
    ["missing_record", "missing_target", "unknown_type", "duplicate_id", "missing_support"],
)
def test_changed_catalogue_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    records = copy.deepcopy(load_catalogue(CATALOGUE))
    by_id = {record["id"]: record for record in records}
    source = by_id["model-boltz-2"]
    if mutation == "missing_record":
        records.remove(source)
    elif mutation == "missing_target":
        source["relations"][0]["target"] = "model-not-in-catalogue"
    elif mutation == "unknown_type":
        source["relations"][0]["type"] = "unfrozen-edge-type"
    elif mutation == "duplicate_id":
        records.append(copy.deepcopy(source))
    else:
        for entry in source["evidence"]:
            if "relations" in entry["supports"]:
                entry["supports"].remove("relations")
    monkeypatch.setattr(summary, "load_catalogue", lambda *_: records)
    output = tmp_path / "summary.json"
    with pytest.raises((GraphError, AuditError)):
        summary.build_summary(PROTOCOL, CATALOGUE, output=output)
    assert not output.exists()
