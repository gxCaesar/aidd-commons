"""Known defects cannot produce a passing task or an exported artifact."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from aidd_commons.agent_evaluation_taskset.analysis import evaluate_task
from aidd_commons.agent_evaluation_taskset.protocol import (
    AuditError,
    load_protocol,
    validate_protocol,
)
from aidd_commons.agent_evaluation_taskset.summary import build_summary, validate_summary

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/agent_evaluation_taskset"


def _result(protocol: dict) -> list[dict]:
    results = []
    for task in protocol["tasks"]:
        evidence = {
            "used_sources": task["declared_sources"],
            "files_present": True,
            "check_exit": 0,
            "summary_matches": True,
            "negative_retained": True,
            "numbers": task["expectations"],
            "claim_boundary_ok": True,
            "authorization_boundary": True,
            "human_decision_record": True,
        }
        row = evaluate_task(task, evidence)
        row["dimensions"] = task["expected_dimensions"].copy()
        row["passing"] = all(state == "pass" for state in row["dimensions"].values())
        results.append(row)
    return results


@pytest.mark.parametrize("defect", ["unsafe_path", "missing_rule", "extra_task_field"])
def test_loader_refuses_bad_contract_without_output(defect: str, tmp_path: Path) -> None:
    protocol = deepcopy(load_protocol(LAB / "protocol.json"))
    if defect == "unsafe_path":
        protocol["tasks"][0]["files"].append("labs/../private.json")
    elif defect == "missing_rule":
        del protocol["dimensions"]["recovery"]
    else:
        protocol["tasks"][0]["passing"] = True
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(AuditError):
        build_summary(
            ROOT,
            LAB / "protocol.json",
            output=output,
            protocol_override=protocol,
            results_override=_result(load_protocol(LAB / "protocol.json")),
        )
    assert not output.exists()


@pytest.mark.parametrize("defect", ["claimed_unused_source", "wrong_number", "failed_check"])
def test_audit_refuses_bad_task_without_output(defect: str, tmp_path: Path) -> None:
    protocol = deepcopy(load_protocol(LAB / "protocol.json"))
    task = protocol["tasks"][0]
    evidence = {
        "used_sources": task["declared_sources"].copy(),
        "files_present": True,
        "check_exit": 0,
        "summary_matches": True,
        "negative_retained": True,
        "numbers": task["expectations"].copy(),
        "claim_boundary_ok": True,
        "authorization_boundary": True,
        "human_decision_record": True,
    }
    if defect == "claimed_unused_source":
        task["declared_sources"].append("labs/claim_chain_audit/not-used.json")
        task["files"].append("labs/claim_chain_audit/not-used.json")
    elif defect == "wrong_number":
        evidence["numbers"]["chain_count"] += 1
    else:
        evidence["check_exit"] = 1
    result = evaluate_task(task, evidence)
    assert result["passing"] is False
    results = _result(protocol)
    results[0] = result
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(AuditError):
        build_summary(
            ROOT,
            LAB / "protocol.json",
            output=output,
            protocol_override=validate_protocol(protocol),
            results_override=results,
        )
    assert not output.exists()


def test_false_passing_row_is_refused() -> None:
    protocol = load_protocol(LAB / "protocol.json")
    summary = json.loads((LAB / "summary.json").read_text(encoding="utf-8"))
    assert summary["per_task"][1]["dimensions"]["claim_accuracy"] == "fail"
    summary["per_task"][1]["passing"] = True
    with pytest.raises(AuditError, match="nonpassing dimension"):
        validate_summary(summary, protocol)
