"""Read committed catalogue and independent-reading YAML without copying it."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .protocol import EXAMINED_IDS


class RecordError(ValueError):
    """A declared input is absent or structurally unusable."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise RecordError(f"cannot read YAML: {path.name}") from error
    if not isinstance(value, dict):
        raise RecordError(f"YAML is not an object: {path.name}")
    return value


def load_catalogue(
    directory: Path, examined_ids: tuple[str, ...] = EXAMINED_IDS
) -> dict[str, dict[str, Any]]:
    if len(set(examined_ids)) != len(examined_ids):
        raise RecordError("protocol repeats a record id")
    if any(
        re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier) is None for identifier in examined_ids
    ):
        raise RecordError("protocol has an invalid record id")
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise RecordError("catalogue holds no YAML records")
    catalogue: dict[str, dict[str, Any]] = {}
    for path in files:
        record = load_yaml(path)
        identifier = record.get("id")
        if not isinstance(identifier, str) or identifier != path.stem:
            raise RecordError(f"record id differs from filename: {path.name}")
        if identifier in catalogue:
            raise RecordError(f"duplicate catalogue id: {identifier}")
        catalogue[identifier] = record
    missing = [identifier for identifier in examined_ids if identifier not in catalogue]
    if missing:
        raise RecordError(f"protocol names missing catalogue records: {', '.join(missing)}")
    return catalogue


def load_reading(root: Path, protocol: dict[str, Any]) -> dict[str, str]:
    sources = protocol["sources"]
    reading = load_yaml(root / sources["independent_reading"])
    own = load_yaml(root / sources["own_comparison_record"])
    if reading.get("system_id") != "aidd-commons" or own.get("id") != "aidd-commons":
        raise RecordError("comparison records have the wrong system id")
    topic = protocol["topic_id"]
    readings = reading.get("readings")
    coverage = own.get("coverage")
    if not isinstance(readings, list) or not isinstance(coverage, list):
        raise RecordError("comparison records have no topic rows")
    rows = [item for item in readings if isinstance(item, dict) and item.get("topic_id") == topic]
    own_rows = [
        item for item in coverage if isinstance(item, dict) and item.get("topic_id") == topic
    ]
    if len(rows) != 1 or len(own_rows) != 1:
        raise RecordError("source-review topic is missing or repeated")
    if (
        rows[0].get("depth") != protocol["independent_depth"]
        or own_rows[0].get("depth") != protocol["recorded_depth"]
    ):
        raise RecordError("source-review depth differs from frozen reading")
    return {
        "topic_id": topic,
        "recorded_depth": own_rows[0]["depth"],
        "independent_depth": rows[0]["depth"],
        "independent_run_basis": str(rows[0].get("run_basis", "")),
    }
