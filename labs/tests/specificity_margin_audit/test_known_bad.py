"""Changed counting contracts and malformed rows must be refused."""

import json
from pathlib import Path

import pytest
from aidd_commons.specificity_margin_audit import summary
from aidd_commons.specificity_margin_audit.analysis import AuditError, MeasurementRow, audit_rows
from aidd_commons.specificity_margin_audit.protocol import ProtocolError, load_protocol

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/specificity_margin_audit/protocol.json"


@pytest.mark.parametrize(
    "mutation",
    [
        "source_bytes",
        "source_route",
        "pair_unit",
        "measurement_rule",
        "partner_rule",
        "one_partner",
        "comparable_pair",
        "excluded_claim",
    ],
)
def test_bad_protocol_edit_refused_before_output(tmp_path, monkeypatch, mutation):
    document = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "source_bytes":
        document["source"]["expected_bytes"] += 1
    elif mutation == "source_route":
        document["source"]["retrieval_url"] = "https://example.invalid/other"
    elif mutation == "pair_unit":
        document["counted_unit"]["protein_pair"] = "Ordered pair"
    elif mutation == "measurement_rule":
        document["counted_unit"]["measurement_rule"] = "Count all rows"
    elif mutation == "partner_rule":
        document["partner_rule"]["definition"] = "Count rows"
    elif mutation == "one_partner":
        document["partner_rule"]["one_partner"] = "One partner proves selectivity"
    elif mutation == "comparable_pair":
        document["partner_rule"]["comparable_pair"] = "Either protein is enough"
    else:
        document["excluded_by_design"] = []
    lab = tmp_path / "lab"
    lab.mkdir()
    (lab / "protocol.json").write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "summary.json"

    def forbid_snapshot(_cache):
        raise AssertionError("snapshot was read before contract validation")

    monkeypatch.setattr(summary, "load_snapshot", forbid_snapshot)
    with pytest.raises(ProtocolError):
        summary.export_summary(lab, tmp_path / "cache", output)
    assert not output.exists()


@pytest.mark.parametrize(
    "rows",
    [
        (MeasurementRow(1, "A", "B", True),),
        (MeasurementRow(0, "A", "A", True),),
        (MeasurementRow(0, "A", "B", False),),
    ],
)
def test_bad_rows_refused(rows):
    with pytest.raises(AuditError):
        audit_rows(rows)


def test_original_protocol_is_loadable():
    assert load_protocol(PROTOCOL)["protocol_id"] == "skempi2-specificity-margin-v1"
