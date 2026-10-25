"""Read committed YAML records without copying them into the laboratory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .protocol import EXAMINED_IDS, calendar_date


class RecordError(ValueError):
    """A catalogue input or declared record cannot be read safely."""


def load_record(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise RecordError(f"cannot read record: {path.name}") from error
    if not isinstance(data, dict) or not isinstance(data.get("id"), str):
        raise RecordError(f"record needs an id: {path.name}")
    return data


def load_catalogue(
    directory: Path,
    examined_ids: tuple[str, ...] = EXAMINED_IDS,
) -> dict[str, dict[str, Any]]:
    if len(set(examined_ids)) != len(examined_ids):
        raise RecordError("protocol repeats a record id")
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise RecordError("catalogue holds no YAML records")
    catalogue: dict[str, dict[str, Any]] = {}
    for path in files:
        record = load_record(path)
        identifier = record["id"]
        if identifier in catalogue:
            raise RecordError(f"duplicate catalogue id: {identifier}")
        catalogue[identifier] = record
    missing = [identifier for identifier in examined_ids if identifier not in catalogue]
    if missing:
        raise RecordError(f"protocol names missing catalogue records: {', '.join(missing)}")
    for identifier in examined_ids:
        if not calendar_date(catalogue[identifier].get("last_verified")):
            raise RecordError(f"invalid last_verified calendar date: {identifier}")
    return catalogue
