"""Read and audit every committed laboratory return record."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import check_record


class AuditError(ValueError):
    """The local return-record collection cannot be audited."""


@dataclass(frozen=True)
class LabRecord:
    laboratory: str
    return_record: dict[str, Any]
    protocol_present: bool
    readme_present: bool


def _has_field(record: dict[str, Any], dotted_field: str) -> bool:
    current: Any = record
    for part in dotted_field.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def load_records(
    labs_dir: Path, source: dict[str, Any], *, exclude: str | None = None
) -> list[LabRecord]:
    """Read the immediate laboratories directly from disk.

    The audit excludes the laboratory named by `exclude`, which is this
    laboratory. Its return record is the file this audit writes, so counting
    it would make the summary depend on its own output, and a change to the
    contract would change the record that records the contract.
    """
    records: list[LabRecord] = []
    for path in sorted(labs_dir.glob(source["return_glob"])):
        if not path.is_file() or path.parent.parent != labs_dir:
            raise AuditError(f"invalid return path: {path}")
        if exclude is not None and path.parent.name == exclude:
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise AuditError(f"unreadable return record: {path}") from error
        if not isinstance(document, dict):
            raise AuditError(f"return record is not an object: {path}")
        records.append(
            LabRecord(
                path.parent.name,
                document,
                (path.parent / source["protocol_file"]).is_file(),
                (path.parent / source["readme_file"]).is_file(),
            )
        )
    if not records:
        raise AuditError(f"no return records under {labs_dir}")
    return records


def audit_records(records: list[LabRecord], contract: dict[str, Any]) -> dict[str, Any]:
    """Count field coverage and retain a field-specific verdict for each lab."""
    if not records or len({item.laboratory for item in records}) != len(records):
        raise AuditError("empty or duplicate laboratory return collection")
    named_fields = contract["schema"]["field_coverage"]
    limit_fields = contract["scientific_meaning"]["limit_field_names"]
    field_counts = {
        field: sum(_has_field(item.return_record, field) for item in records)
        for field in named_fields
    }
    # The counts are keyed by the field they count, and one of the counted
    # field names is also a name the release hygiene scan reserves for
    # pipeline state. The key here is therefore the field name with a prefix,
    # so the two never collide.
    keyed_field_counts = {
        f"records_carrying_{field}": count for field, count in field_counts.items()
    }
    per_laboratory: list[dict[str, Any]] = []
    verdict_counts: Counter[str] = Counter()
    for item in records:
        verdict = check_record(item.return_record, contract)
        verdict_counts[verdict.name] += 1
        per_laboratory.append(
            {
                "laboratory": item.laboratory,
                "verdict": verdict.name,
                "failed_fields": [
                    {"field": failure.field, "reason": failure.reason}
                    for failure in verdict.failures
                ],
                "protocol_present": item.protocol_present,
                "readme_present": item.readme_present,
                "declared_limit_fields": [
                    field for field in limit_fields if field in item.return_record
                ],
            }
        )
    count = len(records)
    limit_count = sum(bool(row["declared_limit_fields"]) for row in per_laboratory)
    result = {
        "return_record_count": count,
        "field_counts": keyed_field_counts,
        "fields_in_every_record": [field for field in named_fields if field_counts[field] == count],
        "fields_in_some_records": [
            field for field in named_fields if 0 < field_counts[field] < count
        ],
        "fields_in_no_records": [field for field in named_fields if field_counts[field] == 0],
        "limit_fields_checked": limit_fields,
        "records_with_declared_limits": limit_count,
        "records_without_declared_limits": count - limit_count,
        # The counts are keyed by the field they count, and one of the counted
        # field names is also a name the release hygiene scan reserves for
        # pipeline state. The key here is therefore the field name with a
        # prefix, so the two never collide.
        "error_field_counts": {
            f"records_carrying_{field}": field_counts[field]
            for field in contract["error_states"]["observed_field_names"]
        },
        "protocol_file_count": sum(item.protocol_present for item in records),
        "readme_file_count": sum(item.readme_present for item in records),
        "verdict_counts": {
            name: verdict_counts[name] for name in ("pass", "no_result", "halt", "invalid")
        },
        "per_laboratory": per_laboratory,
    }
    if sum(result["verdict_counts"].values()) != count:
        raise AuditError("verdict counts do not reconcile")
    return result
