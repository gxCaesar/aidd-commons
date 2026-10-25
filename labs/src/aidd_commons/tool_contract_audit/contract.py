"""Check one laboratory return against the six declared contract parts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from typing import Any


@dataclass(frozen=True)
class Failure:
    field: str
    reason: str


@dataclass(frozen=True)
class Verdict:
    name: str
    failures: tuple[Failure, ...]
    usable_result: bool
    must_stop: bool


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _date(value: Any) -> bool:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _declared_type(value: Any, kind: str) -> bool:
    if kind == "nonempty_string":
        return _nonempty(value)
    if kind == "iso_date":
        return _date(value)
    if kind == "version_map":
        return (
            isinstance(value, dict)
            and bool(value)
            and all(_nonempty(key) and _nonempty(version) for key, version in value.items())
        )
    if kind == "object":
        return isinstance(value, dict)
    if kind == "status":
        return isinstance(value, str)
    raise ValueError(f"unsupported contract type: {kind}")


def _string_list(value: Any, *, nonempty: bool) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(_nonempty(item) for item in value)
    )


def check_record(record: Mapping[str, Any], contract: Mapping[str, Any]) -> Verdict:
    """Return all field-specific failures; a pass describes the artefact only."""
    if not isinstance(record, dict):
        return Verdict("invalid", (Failure("record", "expected_object"),), False, False)
    failures: list[Failure] = []
    required = contract["schema"]["required"]
    for field in sorted(required):
        kind = required[field]
        if field not in record:
            failures.append(Failure(field, "missing_required_field"))
        elif not _declared_type(record[field], kind):
            failures.append(Failure(field, "invalid_or_empty_value"))

    software = record.get("software")
    if isinstance(software, dict):
        if "python" not in software:
            failures.append(Failure("software.python", "missing_required_field"))
        elif not _nonempty(software["python"]):
            failures.append(Failure("software.python", "invalid_or_empty_value"))

    environment = record.get("environment")
    if isinstance(environment, dict):
        for field in ("requires", "unavailable"):
            if field not in environment:
                failures.append(Failure(f"environment.{field}", "missing_required_field"))
            elif not _string_list(environment[field], nonempty=True):
                failures.append(Failure(f"environment.{field}", "invalid_or_empty_value"))
        if "can_attest_external_execution" not in environment:
            failures.append(
                Failure("environment.can_attest_external_execution", "missing_required_field")
            )
        elif environment["can_attest_external_execution"] is not False:
            failures.append(Failure("environment.can_attest_external_execution", "must_be_false"))

    side_effects = record.get("side_effects")
    if isinstance(side_effects, dict):
        if "allowed_writes" not in side_effects:
            failures.append(Failure("side_effects.allowed_writes", "missing_required_field"))
        else:
            paths = side_effects["allowed_writes"]
            if not _string_list(paths, nonempty=False):
                failures.append(Failure("side_effects.allowed_writes", "invalid_or_empty_value"))
            elif any(
                PurePosixPath(path).is_absolute()
                or ".." in PurePosixPath(path).parts
                or path in {"", "."}
                for path in paths
            ):
                failures.append(Failure("side_effects.allowed_writes", "non_relative_path"))

    status = record.get(contract["error_states"]["field"])
    if "outcome_status" in record and status not in contract["error_states"]["statuses"]:
        failures.append(Failure("outcome_status", "unknown_status"))

    meaning = record.get("scientific_meaning")
    if isinstance(meaning, dict):
        for field in contract["scientific_meaning"]["required"]:
            if field not in meaning:
                failures.append(Failure(f"scientific_meaning.{field}", "missing_required_field"))
            elif not _nonempty(meaning[field]):
                failures.append(Failure(f"scientific_meaning.{field}", "invalid_or_empty_value"))

    for field in contract["scientific_meaning"]["limit_field_names"]:
        if field in record and not (
            _nonempty(record[field]) or _string_list(record[field], nonempty=True)
        ):
            failures.append(Failure(field, "invalid_or_empty_value"))

    if failures:
        return Verdict("invalid", tuple(failures), False, False)
    return Verdict(
        "pass" if status == "complete" else str(status),
        (),
        status == "complete",
        status in contract["error_states"]["must_stop"],
    )
