"""Mutated contracts and impossible audits fail without output."""

import json
from pathlib import Path

import pytest
from aidd_commons.nomination_readiness_audit.analysis import AuditError
from aidd_commons.nomination_readiness_audit.protocol import ProtocolError
from aidd_commons.nomination_readiness_audit.summary import build_summary

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "labs/nomination_readiness_audit/protocol.json"
CACHE = ROOT / ".cache/decision_unit_scope"


@pytest.mark.parametrize(
    "mutation", ["threshold", "parent", "endpoint", "artifact_length", "missing_rule"]
)
def test_changed_protocol_refused_without_output(tmp_path: Path, mutation: str) -> None:
    altered = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if mutation == "threshold":
        altered["readiness_rule"]["thresholds"]["independent_measurements"] = 1
    elif mutation == "parent":
        altered["cohort"]["resolved_parents"].pop()
    elif mutation == "endpoint":
        altered["endpoint"]["point_relation"] = ">"
    elif mutation == "artifact_length":
        altered["artifacts"][0]["byte_length"] += 1
    else:
        del altered["readiness_rule"]["missing_measurement_rule"]
    altered_path = tmp_path / "protocol.json"
    altered_path.write_text(json.dumps(altered), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolError):
        build_summary(altered_path, CACHE, output=output)
    assert not output.exists()


def test_invalid_analysis_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aidd_commons.nomination_readiness_audit import summary

    def bad_analysis(_census: object) -> dict[str, object]:
        return {
            "parents": [],
            "cohort_size": 10,
            "admitted_measurement_count": 486,
            "thresholds": {},
            "state_counts": {},
            "state_members": {},
        }

    monkeypatch.setattr(summary, "analyze", bad_analysis)
    # The rejected object is synthetic; loading real measurements is unrelated here.
    monkeypatch.setattr(summary, "load_cached_cohort", lambda _: object())
    monkeypatch.setattr(summary, "census_cohort", lambda _: object())
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        build_summary(PROTOCOL, CACHE, output=output)
    assert not output.exists()
