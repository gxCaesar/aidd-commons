"""Known defects must fail before an export creates output."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import aidd_commons.multi_endpoint_integration.summary as summary_module
import pytest
from aidd_commons.multi_endpoint_integration.protocol import ProtocolContractError
from aidd_commons.multi_endpoint_integration.summary import (
    SummaryContractError,
    audit_summary,
    export_summary,
)

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = json.loads((ROOT / "labs/multi_endpoint_integration/protocol.json").read_text())
SUMMARY = json.loads((ROOT / "labs/multi_endpoint_integration/summary.json").read_text())


@pytest.mark.parametrize(
    "defect", ["composite_rule", "missing_default", "source_length", "join_key", "exclusions"]
)
def test_mutated_contract_leaves_no_output(tmp_path: Path, defect: str) -> None:
    altered = copy.deepcopy(PROTOCOL)
    if defect == "composite_rule":
        altered["rules"]["composite_score"] = "Compute a weighted composite score."
    elif defect == "missing_default":
        altered["rules"]["missing_family"] = "Assume no risk."
    elif defect == "source_length":
        altered["sources"][0]["snapshot_byte_length"] += 1
    elif defect == "join_key":
        altered["counted_unit"]["join_rule"] = "Join by structure."
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
    "defect", ["combined_score", "missing_family_value", "cross_unit_fold", "legacy_parent_key"]
)
def test_mutated_summary_leaves_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    altered = copy.deepcopy(SUMMARY)
    if defect == "combined_score":
        altered["profiles"][0]["combined_score"] = 0.8
    elif defect == "missing_family_value":
        altered["profiles"][0]["efficacy"] = {"value": 0.0, "unit": "nM"}
    elif defect == "legacy_parent_key":
        profile = altered["profiles"][0]
        profile["parent_molecule_chembl_id"] = profile.pop("parent_chembl_id")
    else:
        profile = next(p for p in altered["profiles"] if p["parent_chembl_id"] == "CHEMBL1232461")
        profile["exposure"]["fold_change"] = 14.13 / 10.23
    with pytest.raises(SummaryContractError):
        audit_summary(altered)
    # Isolate candidate rejection; the cached-source recomputation has its own test.
    monkeypatch.setattr(summary_module, "build_summary", lambda _: copy.deepcopy(SUMMARY))
    output = tmp_path / "summary.json"
    with pytest.raises(SummaryContractError):
        export_summary(
            ROOT / "labs/multi_endpoint_integration", ROOT / ".cache", output, candidate=altered
        )
    assert not output.exists()
