"""Known bad contracts and results are refused before export writes output."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import aidd_commons.target_product_profile.summary as summary_module
import pytest
from aidd_commons.target_product_profile.protocol import ProtocolContractError
from aidd_commons.target_product_profile.summary import (
    SummaryContractError,
    audit_summary,
    export_summary,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = json.loads((ROOT / "labs/target_product_profile/protocol.json").read_text())
SUMMARY = json.loads((ROOT / "labs/target_product_profile/summary.json").read_text())


@pytest.mark.parametrize("defect", ["threshold", "kind", "source", "join", "exclusions"])
def test_mutated_protocol_leaves_no_output(tmp_path: Path, defect: str) -> None:
    altered = copy.deepcopy(PROTOCOL)
    if defect == "threshold":
        altered["profile"]["requirements"][0]["threshold"] = 100000
    elif defect == "kind":
        altered["profile"]["requirements"][0]["kind"] = "preference"
    elif defect == "source":
        altered["sources"][0]["snapshot_byte_length"] += 1
    elif defect == "join":
        altered["counted_unit"]["join_rule"] = "Join by compound name."
    else:
        altered["excluded_by_design"] = []
    lab = tmp_path / "lab"
    lab.mkdir()
    (lab / "protocol.json").write_text(json.dumps(altered), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolContractError):
        export_summary(lab, ROOT / ".cache", output)
    assert not output.exists()


@pytest.mark.parametrize(
    "defect",
    [
        "failing_as_satisfying",
        "unmeasured_as_satisfying",
        "preference_as_failure",
        "unmeasured_as_pass",
        "removed_failure",
    ],
)
def test_mutated_summary_leaves_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    altered = copy.deepcopy(SUMMARY)
    if defect == "failing_as_satisfying":
        failed = altered["per_gate"]["response_ic50"]["failing_parent_ids"][0]
        altered["satisfying_parent_ids"].append(failed)
        altered["counts"]["profile_satisfying_compound_count"] += 1
    elif defect == "unmeasured_as_satisfying":
        altered["satisfying_parent_ids"].append("CHEMBL1232461")
        altered["counts"]["profile_satisfying_compound_count"] += 1
    elif defect == "preference_as_failure":
        altered["counts"]["contradicted_compound_count"] += 1
    elif defect == "unmeasured_as_pass":
        clinical = altered["per_gate"]["clinical_response"]
        clinical["unmeasured"] -= 1
        clinical["pass"] += 1
    else:
        potency = altered["per_gate"]["response_ic50"]
        potency["fail"] -= 1
        potency["pass"] += 1
        potency["failing_parent_ids"] = []
    with pytest.raises(SummaryContractError):
        audit_summary(altered)
    # Isolate candidate rejection; the cached-source recomputation has its own test.
    monkeypatch.setattr(summary_module, "build_summary", lambda _: copy.deepcopy(SUMMARY))
    output = tmp_path / "summary.json"
    with pytest.raises(SummaryContractError):
        export_summary(
            ROOT / "labs/target_product_profile", ROOT / ".cache", output, candidate=altered
        )
    assert not output.exists()
