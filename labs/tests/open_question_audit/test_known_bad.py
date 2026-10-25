"""Known defects are refused before an export appears."""

import copy
from pathlib import Path

import pytest
from aidd_commons.open_question_audit import summary
from aidd_commons.open_question_audit.analysis import analyze
from aidd_commons.open_question_audit.protocol import AuditError, load_protocol, load_sources

from .test_analysis import constructed_bundle

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "labs/open_question_audit/protocol.json"


@pytest.mark.parametrize(
    "mutation",
    ["duplicate_topic", "missing_reason", "invalid_depth", "wrong_identity", "false_well_posed"],
)
def test_known_bad_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    protocol = load_protocol(PROTOCOL_PATH)
    bundle = copy.deepcopy(load_sources(ROOT, protocol))
    if mutation == "duplicate_topic":
        bundle["self_record"]["coverage"].append(
            copy.deepcopy(bundle["self_record"]["coverage"][0])
        )
    elif mutation == "missing_reason":
        bundle["independent_reading"]["readings"][0].pop("reason")
    elif mutation == "invalid_depth":
        bundle["self_record"]["coverage"][0]["depth"] = "invented"
    elif mutation == "wrong_identity":
        bundle["independent_reading"]["system_id"] = "another-system"
    else:
        bundle = constructed_bundle()
        original_analyze = analyze

        def false_audit(source: dict, rules: dict) -> dict:
            result = original_analyze(source, rules)
            victim = "open"
            assert result["open_without_falsifier"] == [victim]
            result["open_without_falsifier"].remove(victim)
            result["open_with_falsifier"].append(victim)
            next(row for row in result["rows"] if row["topic_id"] == victim)["names_falsifier"] = (
                True
            )
            return result

        monkeypatch.setattr(summary, "analyze", false_audit)
    monkeypatch.setattr(summary, "load_sources", lambda *_: bundle)
    output = tmp_path / "summary.json"
    with pytest.raises(AuditError):
        summary.build_summary(ROOT, PROTOCOL_PATH, output=output)
    assert not output.exists()
