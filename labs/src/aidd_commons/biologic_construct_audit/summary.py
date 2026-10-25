"""Build, validate and export the compact construct-record audit."""

from __future__ import annotations

import json
import platform
from datetime import date, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from .analysis import audit_records, check_invariants, load_snapshot
from .protocol import PROTOCOL_ID, SUMMARY_SCHEMA_VERSION, load_protocol

PACKAGE_NAME = "aidd-commons-labs"
DECLARED_PACKAGE_VERSION = "0.2.0rc1"
BOUNDARY = (
    "A modality is not a construct. A source record that gives a construct without "
    "a production host does not define a construct, and neither does a record with "
    "neither field. An unstated field is missing from that record, not necessarily "
    "from the therapeutic entity or the underlying science."
)


def package_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return DECLARED_PACKAGE_VERSION


def build_summary(lab_dir: Path, *, computed_on: str | None = None) -> dict[str, Any]:
    protocol = load_protocol(lab_dir / "protocol.json")
    snapshot = load_snapshot(lab_dir, protocol)
    audit = audit_records(snapshot, protocol)
    versions = [
        {
            "source": record["source"],
            "key": record["key"],
            "version": record["entry_version"]
            if record["source"] == "uniprot"
            else record["version"],
        }
        for record in snapshot["records"]
    ]
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {
            "python": platform.python_version(),
            "aidd_commons_labs": package_version(),
        },
        "source_fetched_at_utc": snapshot["fetched_at_utc"],
        "source_versions": versions,
        **audit,
        "boundary": BOUNDARY,
        "enforced_rules": {
            "aggregation": protocol["aggregation_rule"],
            "definition": protocol["definition_rule"],
            "comparison": protocol["comparison_rule"],
        },
    }


def validate_summary(document: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    required = {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "source_fetched_at_utc",
        "source_versions",
        "entity_count",
        "per_field_counts",
        "entities_by_fields",
        "per_entity",
        "per_source",
        "gaps",
        "source_coverage_differences",
        "source_disagreements",
        "boundary",
        "enforced_rules",
    }
    if set(document) != required:
        failures.append("summary field set")
    if document.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary schema version")
    if document.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary protocol id")
    try:
        if date.fromisoformat(document["computed_on"]).isoformat() != document["computed_on"]:
            failures.append("summary computation date")
        fetched = datetime.fromisoformat(document["source_fetched_at_utc"])
        offset = fetched.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            failures.append("summary fetch time")
    except (KeyError, TypeError, ValueError, AttributeError):
        failures.append("summary dates")
    software = document.get("software")
    if not isinstance(software, dict) or not all(
        isinstance(software.get(name), str) and software[name]
        for name in ("python", "aidd_commons_labs")
    ):
        failures.append("summary software versions")
    if document.get("boundary") != BOUNDARY:
        failures.append("boundary statement")
    if not isinstance(document.get("source_versions"), list) or not document["source_versions"]:
        failures.append("source versions")
    if not isinstance(document.get("source_disagreements"), list):
        failures.append("source disagreements")
    if not isinstance(document.get("source_coverage_differences"), list):
        failures.append("source coverage differences")
    if not isinstance(document.get("enforced_rules"), dict) or set(document["enforced_rules"]) != {
        "aggregation",
        "definition",
        "comparison",
    }:
        failures.append("enforced rules")
    failures.extend(check_invariants(document))
    return failures


def check_summary(lab_dir: Path, artifact_path: Path) -> list[str]:
    try:
        document = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return [f"summary cannot be read: {error}"]
    if not isinstance(document, dict):
        return ["summary must be an object"]
    failures = validate_summary(document)
    fresh = build_summary(lab_dir, computed_on=document.get("computed_on"))
    for key in (
        "source_fetched_at_utc",
        "source_versions",
        "entity_count",
        "per_field_counts",
        "entities_by_fields",
        "per_entity",
        "per_source",
        "gaps",
        "source_coverage_differences",
        "source_disagreements",
        "enforced_rules",
    ):
        if document.get(key) != fresh[key]:
            failures.append(f"summary differs from snapshot or protocol: {key}")
    return failures


def export_summary(lab_dir: Path, output: Path) -> dict[str, Any]:
    """Overwrite the compact summary only after all inputs and invariants pass."""
    result = build_summary(lab_dir)
    failures = validate_summary(result)
    if failures:
        raise ValueError("; ".join(failures))
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
