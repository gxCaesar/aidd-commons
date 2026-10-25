"""Load the frozen task selection without admitting arbitrary paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aidd-commons.agent-evaluation-taskset-protocol.v1"
PROTOCOL_ID = "aidd-commons-agent-evaluation-taskset-v1"
DIMENSIONS = (
    "source_resolution",
    "execution_correctness",
    "recovery",
    "claim_accuracy",
    "action_authorization",
)
LABORATORIES = ("claim_chain_audit", "paperqa_local", "chembl_egfr")


class AuditError(ValueError):
    """A task contract or result cannot be accepted."""


def local_path(root: Path, value: str) -> Path:
    """Resolve one repository-relative file without allowing an escape."""
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or path.parts[0] == ".":
        raise AuditError(f"invalid repository-relative path: {value}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise AuditError(f"path escapes repository: {value}")
    return resolved


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("issued_on") != "2026-10-23"
        or value.get("counted_unit") != "one task, each naming one laboratory"
    ):
        raise AuditError("unexpected task-set identity or counted unit")
    source = value.get("source")
    if not isinstance(source, dict) or source.get("selection_glob") != "labs/*/":
        raise AuditError("task selection glob changed")
    if source.get("laboratory_directories") != [f"labs/{name}" for name in LABORATORIES]:
        raise AuditError("frozen laboratory selection changed")
    if source.get("download") != "none" or source.get("network") != "none":
        raise AuditError("the task set must remain local")
    if set(value.get("dimensions", {})) != set(DIMENSIONS):
        raise AuditError("five dimension rules are required")
    if not isinstance(value.get("passing_rule"), str):
        raise AuditError("passing rule is missing")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or [task.get("laboratory") for task in tasks] != list(
        LABORATORIES
    ):
        raise AuditError("the fixed task list changed")
    if len({task.get("id") for task in tasks}) != len(tasks):
        raise AuditError("task identifiers must be unique")
    required = {
        "id",
        "laboratory",
        "files",
        "source_contract",
        "declared_sources",
        "check_command",
        "summary_file",
        "expectations",
        "expected_dimensions",
        "negative_record",
        "authorization_record",
    }
    for task in tasks:
        if set(task) != required:
            raise AuditError(f"unexpected task fields: {task.get('id')}")
        files = task["files"]
        sources = task["declared_sources"]
        command = task["check_command"]
        if (
            not isinstance(files, list)
            or not isinstance(sources, list)
            or not files
            or not sources
            or len(files) != len(set(files))
            or len(sources) != len(set(sources))
            or not set(sources).issubset(files)
            or not isinstance(command, list)
            or task["summary_file"] not in files
        ):
            raise AuditError(f"invalid files or command: {task['id']}")
        for path in files:
            if not isinstance(path, str) or not path.startswith(("labs/", "catalog/")):
                raise AuditError(f"invalid file declaration: {task['id']}")
            if ".." in Path(path).parts or Path(path).is_absolute():
                raise AuditError(f"unsafe file declaration: {task['id']}")
        valid_command = (
            len(command) == 2 and command[0] in files and command[1] == "check"
        ) or command == [
            "-m",
            "pytest",
            "labs/tests/test_paperqa_notebook.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ]
        expected_dimensions = task["expected_dimensions"]
        if (
            not valid_command
            or not isinstance(task["expectations"], dict)
            or not isinstance(expected_dimensions, dict)
            or set(expected_dimensions) != set(DIMENSIONS)
            or any(
                state not in {"pass", "incomplete", "fail"}
                for state in expected_dimensions.values()
            )
        ):
            raise AuditError(f"check script or expectations missing: {task['id']}")
        if task["source_contract"] not in {
            "protocol.sources",
            "inspector.load_literals",
            "paperqa.literal_inputs",
        }:
            raise AuditError(f"unknown source contract: {task['id']}")
    return value


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AuditError(f"cannot read protocol: {path}") from error
    if not isinstance(value, dict):
        raise AuditError("protocol must be an object")
    return validate_protocol(value)
