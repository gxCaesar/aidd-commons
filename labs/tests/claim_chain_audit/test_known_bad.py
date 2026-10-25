"""Known defects cannot create a committed summary."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from aidd_commons.claim_chain_audit import summary
from aidd_commons.claim_chain_audit.analysis import AuditError, analyze, load_records
from aidd_commons.claim_chain_audit.protocol import ProtocolError, load_protocol

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "labs/claim_chain_audit/protocol.json"


@pytest.mark.parametrize(
    "mutation",
    [
        "changed_chain",
        "biological_rule",
        "undeclared_evidence",
        "missing_file",
        "duplicate_reading",
        "false_support",
        "biological_claim",
        "wrong_weakest",
    ],
)
def test_known_bad_refused_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    output = tmp_path / "summary.json"
    protocol_path = PROTOCOL_PATH
    if mutation in ("changed_chain", "biological_rule"):
        altered = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        if mutation == "changed_chain":
            altered["chains"][0]["topic_ids"].pop()
        else:
            altered["rules"]["no_biological_conclusion"] = "A target conclusion is allowed."
        protocol_path = tmp_path / "protocol.json"
        protocol_path.write_text(json.dumps(altered), encoding="utf-8")
        with pytest.raises(ProtocolError):
            summary.build_summary(ROOT, protocol_path, output=output)
    else:
        protocol = load_protocol(PROTOCOL_PATH)
        records = copy.deepcopy(load_records(ROOT, protocol))
        first_id = protocol["chains"][0]["topic_ids"][0]
        cell = next(x for x in records["self_record"]["coverage"] if x["topic_id"] == first_id)
        if mutation == "undeclared_evidence":
            cell["evidence"] = ["not-declared"]
        elif mutation == "missing_file":
            reference = cell["evidence"][0]
            entry = next(x for x in records["self_record"]["evidence"] if x["id"] == reference)
            entry["repository_path"] = "missing-comparison-evidence.txt"
        elif mutation == "duplicate_reading":
            records["independent_reading"]["readings"].append(
                copy.deepcopy(records["independent_reading"]["readings"][0])
            )
        elif mutation == "false_support":
            cell["evidence"] = []
        monkeypatch.setattr(summary, "load_records", lambda *_: records)
        if mutation in ("false_support", "biological_claim", "wrong_weakest"):
            original_analyze = analyze

            def bad_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
                result = original_analyze(*args, **kwargs)
                chain = result["chains"][0]
                if mutation == "false_support":
                    chain["supported_claim"] = True
                elif mutation == "biological_claim":
                    chain["claim_scope"] = "target-validated"
                else:
                    chain["weakest_link"] = {"topic_id": first_id, "depth": "assessed"}
                return result

            monkeypatch.setattr(summary, "analyze", bad_result)
        with pytest.raises(AuditError):
            summary.build_summary(ROOT, protocol_path, output=output)
    assert not output.exists()
