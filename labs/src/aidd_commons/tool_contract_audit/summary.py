"""Build and verify the compact contract-audit return record."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib import metadata
from pathlib import Path
from typing import Any

from .analysis import audit_records, load_records
from .contract import check_record
from .protocol import BOUNDARY, PROTOCOL_ID, SUMMARY_SCHEMA_VERSION, expected_fields, load_protocol

PACKAGE_NAME = "aidd-commons-labs"
DECLARED_PACKAGE_VERSION = "0.2.0rc1"
RESULT_FIELDS = (
    "return_record_count",
    "field_counts",
    "fields_in_every_record",
    "fields_in_some_records",
    "fields_in_no_records",
    "limit_fields_checked",
    "records_with_declared_limits",
    "records_without_declared_limits",
    "error_field_counts",
    "protocol_file_count",
    "readme_file_count",
    "verdict_counts",
    "per_laboratory",
)


def package_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return DECLARED_PACKAGE_VERSION


def build_summary(
    lab_dir: Path, labs_dir: Path, *, computed_on: str | None = None
) -> dict[str, Any]:
    protocol = load_protocol(lab_dir / "protocol.json")
    result = audit_records(
        load_records(
            labs_dir, protocol["source"], exclude=protocol["source"]["exclude_laboratory"]
        ),
        protocol["contract"],
    )
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {
            "python": platform.python_version(),
            "aidd_commons_labs": package_version(),
        },
        "environment": {
            "requires": ["Python 3.11", "committed local laboratory return records"],
            "unavailable": ["external execution attestation", "independent measurement validation"],
            "can_attest_external_execution": False,
        },
        "side_effects": {"allowed_writes": ["labs/tool_contract_audit/summary.json"]},
        "outcome_status": "complete",
        "scientific_meaning": {
            "licenses": "The laboratory produced a self-describing contract-audit artefact.",
            "does_not_license": (
                "The audit does not prove measurement truth, actual execution environment "
                "or independent reproduction from a return record."
            ),
        },
        "contract": protocol["contract"],
        **result,
        "boundary": BOUNDARY,
    }


def validate_summary(summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary.schema_version")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary.protocol_id")
    if summary.get("boundary") != BOUNDARY:
        failures.append("summary.boundary")
    if summary.get("contract") != expected_fields()["contract"]:
        failures.append("summary.contract")
    if check_record(summary, expected_fields()["contract"]).name != "pass":
        failures.append("summary return contract")
    expected_keys = {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "environment",
        "side_effects",
        "outcome_status",
        "scientific_meaning",
        "contract",
        "boundary",
        *RESULT_FIELDS,
    }
    if set(summary) != expected_keys:
        failures.append("summary field set")
    count_value = summary.get("return_record_count")
    count = count_value if type(count_value) is int else -1
    rows = summary.get("per_laboratory")
    counts = summary.get("verdict_counts")
    if count < 1:
        failures.append("summary.return_record_count")
    if not isinstance(rows, list) or len(rows) != count:
        failures.append("summary.per_laboratory")
    if not isinstance(counts, dict) or set(counts) != {"pass", "no_result", "halt", "invalid"}:
        failures.append("summary.verdict_counts")
    elif (
        any(type(value) is not int or value < 0 for value in counts.values())
        or sum(counts.values()) != count
    ):
        failures.append("summary.verdict_counts total")
    fields = summary.get("field_counts")
    if not isinstance(fields, dict) or set(fields) != {
        f"records_carrying_{field}"
        for field in expected_fields()["contract"]["schema"]["field_coverage"]
    }:
        failures.append("summary.field_counts")
    elif any(type(value) is not int or value < 0 or value > count for value in fields.values()):
        failures.append("summary.field_counts values")
    with_limits = summary.get("records_with_declared_limits")
    without_limits = summary.get("records_without_declared_limits")
    if (
        type(with_limits) is not int
        or type(without_limits) is not int
        or with_limits + without_limits != count
    ):
        failures.append("summary limit totals")
    return failures


def check_summary(lab_dir: Path, labs_dir: Path, artifact_path: Path) -> list[str]:
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return [f"summary cannot be read: {error}"]
    if not isinstance(artifact, dict):
        return ["summary must be an object"]
    failures = validate_summary(artifact)
    current = build_summary(lab_dir, labs_dir, computed_on=artifact.get("computed_on"))
    for key in ("contract", *RESULT_FIELDS, "boundary"):
        if artifact.get(key) != current[key]:
            failures.append(f"summary differs from current records: {key}")
    return failures


def export_summary(lab_dir: Path, labs_dir: Path, output: Path) -> dict[str, Any]:
    """Write only after protocol, source and summary checks pass."""
    summary = build_summary(lab_dir, labs_dir)
    failures = validate_summary(summary)
    if failures:
        raise ValueError("; ".join(failures))
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
