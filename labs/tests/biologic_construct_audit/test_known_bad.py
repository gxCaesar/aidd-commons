"""Known defects are refused before any new summary is written."""

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.biologic_construct_audit import summary as summary_module
from aidd_commons.biologic_construct_audit.analysis import load_snapshot, render_snapshot
from aidd_commons.biologic_construct_audit.protocol import EXPECTED_PROTOCOL, ProtocolError
from aidd_commons.biologic_construct_audit.summary import export_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/biologic_construct_audit"


def temporary_lab(tmp_path, protocol, snapshot):
    lab = tmp_path / "labs/biologic_construct_audit"
    lab.mkdir(parents=True)
    (lab / "protocol.json").write_text(json.dumps(protocol), encoding="utf-8")
    snapshot_path = tmp_path / "labs/src/aidd_commons/biologic_construct_audit/__init__.py"
    snapshot_path.parent.mkdir(parents=True)
    snapshot_path.write_text(render_snapshot(snapshot), encoding="utf-8")
    return lab


@pytest.mark.parametrize(
    "mutation",
    [
        "query",
        "field_rule",
        "excluded_claim",
        "missing_source_record",
        "missing_product_quote",
        "missing_host_quote",
        "modality_only_marked_defined",
    ],
)
def test_known_bad_edit_is_refused_without_output(tmp_path, monkeypatch, mutation):
    protocol = copy.deepcopy(EXPECTED_PROTOCOL)
    snapshot = copy.deepcopy(load_snapshot(LAB, protocol))
    if mutation == "query":
        protocol["sources"]["uniprot"]["query"] = "reviewed:true"
    elif mutation == "field_rule":
        protocol["four_fields"]["construct"]["rule"] = "A modality defines a construct."
    elif mutation == "excluded_claim":
        protocol["excluded_by_design"] = []
    elif mutation == "missing_source_record":
        snapshot["records"] = snapshot["records"][1:]
    elif mutation == "missing_product_quote":
        record = next(
            row
            for row in snapshot["records"]
            if row["source"] == "uniprot" and row["key"] == "P20333"
        )
        record["pharmaceutical_text"] = ["Enbrel is listed without molecular detail."]
    elif mutation == "missing_host_quote":
        record = next(
            row
            for row in snapshot["records"]
            if row["source"] == "uniprot" and row["key"] == "P06280"
        )
        record["pharmaceutical_text"] = ["Fabrazyme is listed without a production host."]
    lab = temporary_lab(tmp_path, protocol, snapshot)
    output = tmp_path / "out.json"
    if mutation == "modality_only_marked_defined":
        false_report = summary_module.build_summary(lab)
        row = next(
            item for item in false_report["per_entity"] if item["entity"] == "human-insulin-humulin"
        )
        row["defined_construct"] = True
        monkeypatch.setattr(summary_module, "build_summary", lambda _lab: false_report)
        with pytest.raises(ValueError, match="entity definition rule"):
            export_summary(lab, output)
    elif mutation in {"query", "field_rule", "excluded_claim"}:
        with pytest.raises(ProtocolError):
            export_summary(lab, output)
    else:
        with pytest.raises(ValueError):
            export_summary(lab, output)
    assert not output.exists()
