"""Known defects must fail before an export creates output."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import aidd_commons.candidate_evidence_chain.summary as summary_module
import pytest
from aidd_commons.candidate_evidence_chain.protocol import ProtocolContractError
from aidd_commons.candidate_evidence_chain.summary import (
    SummaryContractError,
    audit_summary,
    export_summary,
)

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/candidate_evidence_chain"
PROTOCOL = json.loads((LAB / "protocol.json").read_text(encoding="utf-8"))
SUMMARY = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("defect", ["source_status", "link_order", "claim_gate", "join_rule"])
def test_bad_protocol_leaves_no_output(tmp_path: Path, defect: str) -> None:
    changed = copy.deepcopy(PROTOCOL)
    if defect == "source_status":
        changed["sources"][3]["status"] = "measured"
    elif defect == "link_order":
        changed["links"][0], changed["links"][1] = changed["links"][1], changed["links"][0]
    elif defect == "claim_gate":
        changed["rules"]["claim_gate"] = "Constructed links may support claims."
    else:
        changed["counted_unit"]["join_rule"] = "Join by molecule name."
    lab = tmp_path / "lab"
    lab.mkdir()
    (lab / "protocol.json").write_text(json.dumps(changed), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolContractError):
        export_summary(lab, ROOT / ".cache", output)
    assert not output.exists()


@pytest.mark.parametrize(
    "defect",
    ["constructed_supports_claim", "filled_absence", "wrong_first_stop", "overbroad_claim"],
)
def test_bad_chain_leaves_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    changed = copy.deepcopy(SUMMARY)
    chain = changed["chains"][0]
    if defect == "constructed_supports_claim":
        chain["links"][5]["state"] = "constructed"
        chain["links"][5]["source"] = "safety_evidence"
        chain["counts"]["constructed"] = 1
        chain["counts"]["not covered"] -= 1
        chain["supports_claim"] = True
        chain["bounded_claim"] = "Candidate is safe"
    elif defect == "filled_absence":
        chain["links"][3]["measurements"] = [{"value": 0, "unit": "pChEMBL"}]
    elif defect == "wrong_first_stop":
        chain["first_non_measured"] = "activity"
    else:
        chain["supports_claim"] = True
        chain["bounded_claim"] = "Development candidate"
    with pytest.raises(SummaryContractError):
        audit_summary(changed)
    # Isolate candidate rejection; the cached-source recomputation has its own test.
    monkeypatch.setattr(summary_module, "build_summary", lambda _: copy.deepcopy(SUMMARY))
    output = tmp_path / "summary.json"
    with pytest.raises(SummaryContractError):
        export_summary(LAB, ROOT / ".cache", output, candidate=changed)
    assert not output.exists()
