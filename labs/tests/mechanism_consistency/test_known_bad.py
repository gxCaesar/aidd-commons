"""Changed contracts and a false support verdict must fail before export."""

import json
from pathlib import Path

import pytest
from aidd_commons.mechanism_consistency import summary
from aidd_commons.mechanism_consistency.analysis import AuditError, Verdict, audit_verdicts
from aidd_commons.mechanism_consistency.protocol import ProtocolError, load_protocol

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/mechanism_consistency/protocol.json"


@pytest.mark.parametrize(
    "mutation",
    [
        "threshold",
        "threshold_rule",
        "generic_rule",
        "shared_control_rule",
        "undecided_rule",
        "source_route",
        "reader",
        "excluded_claims",
    ],
)
def test_bad_protocol_refused_before_snapshot_or_output(tmp_path, monkeypatch, mutation):
    document = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "threshold":
        document["comparison"]["informative_rho_minimum"] = 0.0
    elif mutation == "threshold_rule":
        document["comparison"]["threshold_rule"] = "Low values support."
    elif mutation == "generic_rule":
        document["comparison"]["generic_stress"] = "Ignore the mismatch."
    elif mutation == "shared_control_rule":
        document["comparison"]["shared_control"] = "Count shared control as support."
    elif mutation == "undecided_rule":
        document["comparison"]["undecided_rule"] = "Undecided supports."
    elif mutation == "source_route":
        document["source"]["route"] = ".cache/other/"
    elif mutation == "reader":
        document["source"]["reader"] = "a.second.reader"
    else:
        document["excluded_by_design"] = []
    lab = tmp_path / "lab"
    lab.mkdir()
    (lab / "protocol.json").write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "summary.json"

    def forbidden_snapshot(_cache):
        raise AssertionError("snapshot read before protocol validation")

    monkeypatch.setattr(summary, "load_cached_cell_lines", forbidden_snapshot)
    with pytest.raises(ProtocolError):
        summary.export_summary(lab, tmp_path / "cache", output)
    assert not output.exists()


def test_false_support_with_informative_mismatched_control_refused_before_output(
    tmp_path, monkeypatch
):
    row = Verdict("A", "A", 0.5, 0.5, "mediator_specific", "match_without_informative_control")
    assert any("verdict violates" in failure for failure in audit_verdicts((row,)))

    def constructed_analyse(_datasets):
        return (row,), {
            "admitted_mcf7": 1,
            "admitted_pc3": 1,
            "admitted_union": 1,
            "shared_testable": 1,
            "mcf7_only": 0,
            "pc3_only": 0,
        }

    monkeypatch.setattr(summary, "load_cached_cell_lines", lambda _cache: {})
    monkeypatch.setattr(summary, "analyse", constructed_analyse)
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError, match="verdict violates"):
        summary.export_summary(PROTOCOL.parent, tmp_path, output)
    assert not output.exists()


def test_original_protocol_loads():
    assert load_protocol(PROTOCOL)["issued_on"] == "2026-10-23"
