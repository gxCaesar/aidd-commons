"""Read the canonical comparison files without making a laboratory copy."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class RecordError(ValueError):
    """A comparison record is missing or structurally unusable."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise RecordError(f"cannot read {path.name}") from error
    if not isinstance(value, dict):
        raise RecordError(f"{path.name} must contain an object")
    return value


def load_provider(directory: Path, provider_id: str) -> dict[str, Any]:
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", provider_id) is None:
        raise RecordError(f"invalid provider id: {provider_id}")
    path = directory / f"{provider_id}.yaml"
    record = load_yaml(path)
    if record.get("id") != provider_id:
        raise RecordError(f"provider id differs from filename: {provider_id}")
    coverage = record.get("coverage")
    evidence = record.get("evidence")
    default = record.get("coverage_default")
    if not isinstance(coverage, list) or not isinstance(evidence, list):
        raise RecordError(f"provider needs coverage and evidence lists: {provider_id}")
    if not isinstance(default, dict) or default.get("depth") != "unverified":
        raise RecordError(f"provider needs an unverified default: {provider_id}")
    if default.get("evidence") != []:
        raise RecordError(f"provider default must have no evidence: {provider_id}")
    reviewed_on = record.get("last_verified")
    if isinstance(reviewed_on, date):
        reviewed_on = reviewed_on.isoformat()
    if not isinstance(reviewed_on, str):
        raise RecordError(f"provider has no review date: {provider_id}")
    try:
        if date.fromisoformat(reviewed_on).isoformat() != reviewed_on:
            raise ValueError
    except ValueError as error:
        raise RecordError(f"provider has invalid review date: {provider_id}") from error
    for name, items, key in (("coverage", coverage, "topic_id"), ("evidence", evidence, "id")):
        identifiers = [item.get(key) if isinstance(item, dict) else None for item in items]
        if any(not isinstance(identifier, str) for identifier in identifiers):
            raise RecordError(f"invalid {name} identifier: {provider_id}")
        if len(set(identifiers)) != len(identifiers):
            raise RecordError(f"duplicate {name} identifier: {provider_id}")
    for cell in coverage:
        if not isinstance(cell.get("depth"), str) or not isinstance(cell.get("note"), str):
            raise RecordError(f"coverage lacks depth or note: {provider_id}/{cell['topic_id']}")
    if not isinstance(default.get("note"), str):
        raise RecordError(f"default lacks note: {provider_id}")
    return record


def load_sources(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    source = protocol["sources"]
    directory = root / "catalog/comparisons/systems"
    actual = {path.stem for path in directory.glob("*.yaml")}
    declared = set(protocol["provider_ids"])
    if actual != declared:
        raise RecordError(
            f"provider files differ from protocol: missing={sorted(declared - actual)}, "
            f"extra={sorted(actual - declared)}"
        )
    providers = {
        identifier: load_provider(directory, identifier) for identifier in protocol["provider_ids"]
    }
    taxonomy = load_yaml(root / source["taxonomy"])
    reading = load_yaml(root / source["independent_reading"])
    try:
        comparison = json.loads((root / source["comparison_record"]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RecordError("cannot read comparison record") from error
    if not isinstance(comparison, dict):
        raise RecordError("comparison record must be an object")
    return {
        "providers": providers,
        "taxonomy": taxonomy,
        "reading": reading,
        "comparison": comparison,
    }
