"""Mutated contracts must fail before any summary is written."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from aidd_commons.multi_endpoint_tradeoff.protocol import ProtocolContractError
from aidd_commons.multi_endpoint_tradeoff.summary import export_summary

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = json.loads((ROOT / "labs/multi_endpoint_tradeoff/protocol.json").read_text())


@pytest.mark.parametrize(
    "defect", ["protocol_id", "family_mapping", "artifact_length", "exclusions"]
)
def test_known_bad_contract_leaves_no_output(tmp_path: Path, defect: str) -> None:
    altered = copy.deepcopy(ORIGINAL)
    if defect == "protocol_id":
        altered["protocol_id"] = "unfrozen"
    elif defect == "family_mapping":
        altered["family_rule"]["type_to_family"]["Kd"] = "exposure"
    elif defect == "artifact_length":
        altered["artifacts"][0]["byte_length"] += 1
    else:
        altered["excluded_by_design"] = []
    lab = tmp_path / "lab"
    lab.mkdir()
    (lab / "protocol.json").write_text(json.dumps(altered), encoding="utf-8")
    output = tmp_path / "summary.json"
    with pytest.raises(ProtocolContractError):
        export_summary(lab, tmp_path / "missing-cache", output)
    assert not output.exists()
