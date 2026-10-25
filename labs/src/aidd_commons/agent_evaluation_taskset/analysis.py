"""Recompute the five record dimensions for each frozen task."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .protocol import DIMENSIONS, AuditError, local_path

BOUNDARY = (
    "This task set audits committed records, not a tool acting on a task. "
    "A passing task would show internal agreement of its named material, not "
    "that its scientific result is correct or that an earlier human decision occurred."
)


def _read_json(root: Path, path: str) -> dict[str, Any]:
    value = json.loads(local_path(root, path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AuditError(f"expected JSON object: {path}")
    return value


def used_sources(root: Path, task: dict[str, Any]) -> list[str]:
    """Read source paths from the laboratory's own contract or inspector."""
    laboratory = task["laboratory"]
    if task["source_contract"] == "protocol.sources":
        own = _read_json(root, f"labs/{laboratory}/protocol.json")
        sources = own.get("sources")
        if not isinstance(sources, dict):
            raise AuditError(f"own source manifest missing: {laboratory}")
        paths = [entry.get("path") for entry in sources.values()]
        if not all(isinstance(path, str) for path in paths):
            raise AuditError(f"own source path missing: {laboratory}")
        return paths
    if task["source_contract"] == "inspector.load_literals":
        script = local_path(root, task["check_command"][0])
        tree = ast.parse(script.read_text(encoding="utf-8"))
        names = [
            call.args[0].value
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "load"
            and len(call.args) == 1
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ]
        if not names:
            raise AuditError(f"no literal inspector inputs: {laboratory}")
        return [f"labs/{laboratory}/{name}" for name in names]
    if task["source_contract"] == "paperqa.literal_inputs":
        script = local_path(root, "labs/paperqa_local/build_notebooks.py")
        tree = ast.parse(script.read_text(encoding="utf-8"))
        names = [
            call.func.value.right.value
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "read_text"
            and isinstance(call.func.value, ast.BinOp)
            and isinstance(call.func.value.right, ast.Constant)
            and call.func.value.right.value == "reviewed-example.json"
        ]
        if names != ["reviewed-example.json"]:
            raise AuditError("notebook builder no longer reads the committed example once")
        runner = ast.parse(
            local_path(root, "labs/paperqa_local/run_smoke.py").read_text(encoding="utf-8")
        )
        corpus_names = [
            call.args[0].value
            for call in ast.walk(runner)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "with_name"
            and len(call.args) == 1
            and isinstance(call.args[0], ast.Constant)
            and call.args[0].value == "corpus.json"
        ]
        corpus_reads = [
            call
            for call in ast.walk(runner)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "read_text"
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "CORPUS"
        ]
        if corpus_names != ["corpus.json"] or not corpus_reads:
            raise AuditError("PaperQA runner no longer names the committed corpus once")
        return ["labs/paperqa_local/corpus.json", "labs/paperqa_local/reviewed-example.json"]
    raise AuditError(f"unknown source contract: {laboratory}")


def _run_check(root: Path, task: dict[str, Any]) -> int:
    command = [sys.executable, *task["check_command"]]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        command,
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return completed.returncode


def _owner_summary_matches(root: Path, task: dict[str, Any], stored: dict[str, Any]) -> bool | None:
    laboratory = task["laboratory"]
    if laboratory in {"chembl_egfr", "paperqa_local"}:
        return None  # Neither check rebuilds its whole observed record.
    from aidd_commons.claim_chain_audit.summary import build_summary

    current = build_summary(
        root,
        root / "labs" / laboratory / "protocol.json",
        computed_on=stored["computed_on"],
        software=stored["software"],
    )
    return bool(current == stored)


def _record_details(root: Path, task: dict[str, Any]) -> dict[str, Any]:
    laboratory = task["laboratory"]
    if laboratory == "claim_chain_audit":
        summary = _read_json(root, task["summary_file"])
        own = _read_json(root, "labs/claim_chain_audit/protocol.json")
        chains = summary["chains"]
        return {
            "numbers": {
                "chain_count": len(chains),
                "link_count": sum(chain["link_count"] for chain in chains),
                "disagreement_count": summary["total_disagreement_links"],
            },
            "negative_retained": None,
            "claim_boundary_ok": summary["boundary_statement"] == own["boundary_statement"]
            and all(chain["claim_scope"] == "named-topic-material-only" for chain in chains),
            "summary_matches": _owner_summary_matches(root, task, summary),
            "authorization_boundary": False,
            "human_decision_record": None,
        }
    if laboratory == "paperqa_local":
        summary = _read_json(root, task["summary_file"])
        corpus = _read_json(root, "labs/paperqa_local/corpus.json")
        reviews = summary["source_review"]
        abstentions = [
            row for row in reviews if row["verdict"] == "appropriate_abstention_limited_retrieval"
        ]
        prose_errors = [row for row in reviews if row["verdict"].endswith("extra_prose_error")]
        answer_ids = {row["id"] for row in summary["answers"]}
        question_ids = {row["id"] for row in summary["questions"]}
        corpus_ids = {row["id"] for row in corpus["questions"]}
        return {
            "numbers": {
                "document_count": len(summary["documents"]),
                "question_count": len(summary["questions"]),
                "answer_count": len(summary["answers"]),
                "review_count": len(reviews),
                "abstention_count": len(abstentions),
                "extra_prose_error_count": len(prose_errors),
            },
            "negative_retained": len(abstentions) == 1
            and abstentions[0]["question_id"] in answer_ids
            and bool(abstentions[0]["limitation"]),
            "claim_boundary_ok": answer_ids == question_ids == corpus_ids
            and {row["question_id"] for row in reviews} == question_ids
            and "not a benchmark" in summary["scope"]
            and "No benchmark accuracy" in summary["observations"]["notes"]
            and not prose_errors,
            "summary_matches": _owner_summary_matches(root, task, summary),
            "authorization_boundary": False,
            "human_decision_record": None,
        }
    protocol = _read_json(root, "labs/chembl_egfr/protocol.json")
    development = _read_json(root, "labs/chembl_egfr/development-summary.json")
    locked = _read_json(root, "labs/chembl_egfr/locked-summary.json")
    amendment = _read_json(root, "labs/chembl_egfr/execution-amendment.json")
    readme = local_path(root, "labs/chembl_egfr/README.md").read_text(encoding="utf-8")
    primary = development["data"]["primary"]
    replication = development["data"]["replication"]
    authorization_receipt = locked.get("authorization_receipt")
    recorded_human_decision = (
        authorization_receipt.get("decision_maker") == "human"
        and authorization_receipt.get("tool_decided") is False
        if isinstance(authorization_receipt, dict)
        else None
    )
    return {
        "numbers": {
            "primary_parent_count": primary["parent_count"],
            "replication_parent_count": replication["parent_count"],
            "locked_test_count": locked["results"]["primary_test"]["count"],
            "locked_replication_count": locked["results"]["assay_replication"]["count"],
        },
        "negative_retained": None,
        "claim_boundary_ok": primary["parent_count"]
        == protocol["source"]["expected_parent_counts"][primary["assay_chembl_id"]]
        and replication["parent_count"]
        == protocol["source"]["expected_parent_counts"][replication["assay_chembl_id"]]
        and locked["status"] == "completed"
        and protocol["locked_evaluation"]["state"] == "not_run"
        and amendment["base_protocol"] == protocol["protocol_version"]
        and bool(locked["interpretation"]),
        "summary_matches": None,
        "authorization_boundary": "explicit approval" in readme
        and "Reject missing explicit confirmation" in amendment["authorization"],
        "human_decision_record": recorded_human_decision,
    }


def evaluate_task(task: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Classify observed evidence without turning absence into a pass."""
    sources_match = set(task["declared_sources"]) == set(evidence["used_sources"])
    dimensions = {
        "source_resolution": "pass" if sources_match and evidence["files_present"] else "fail",
        "execution_correctness": (
            "fail"
            if evidence["check_exit"] != 0 or evidence["summary_matches"] is False
            else "incomplete"
            if evidence["summary_matches"] is None
            else "pass"
        ),
        "recovery": (
            "incomplete"
            if evidence["negative_retained"] is None
            else "pass"
            if evidence["negative_retained"]
            else "fail"
        ),
        "claim_accuracy": "pass"
        if evidence["numbers"] == task["expectations"] and evidence["claim_boundary_ok"]
        else "fail",
        "action_authorization": (
            "incomplete"
            if not evidence["authorization_boundary"] or evidence["human_decision_record"] is None
            else "pass"
            if evidence["human_decision_record"]
            else "fail"
        ),
    }
    return {
        "id": task["id"],
        "laboratory": task["laboratory"],
        "negative_record": task["negative_record"],
        "dimensions": dimensions,
        "passing": all(dimensions[name] == "pass" for name in DIMENSIONS),
        "checked_numbers": evidence["numbers"],
        "declared_sources": task["declared_sources"],
        "used_sources": evidence["used_sources"],
        "check_command": task["check_command"],
        "check_exit_code": evidence["check_exit"],
        "authorization_boundary_stated": evidence["authorization_boundary"],
    }


def audit(root: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for task in protocol["tasks"]:
        observed = _record_details(root, task)
        observed["used_sources"] = used_sources(root, task)
        files_present = True
        for path in task["files"]:
            local = local_path(root, path)
            if not local.is_file():
                files_present = False
                continue
            local.read_text(encoding="utf-8")
        observed["files_present"] = files_present
        observed["check_exit"] = _run_check(root, task)
        results.append(evaluate_task(task, observed))
    return results
