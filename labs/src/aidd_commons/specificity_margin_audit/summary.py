"""Build and verify the committed census against the cached archive."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib import metadata
from pathlib import Path
from typing import Any

from aidd_commons.skempi_affinity.data import CACHE_FILENAME, validate_size

from .analysis import audit_rows, rows_from_payload
from .protocol import PROTOCOL_ID, SUMMARY_SCHEMA_VERSION, load_protocol

# The laboratories run from a published export and from a blind-reading
# sandbox, and neither carries the repository's `pyproject.toml`. Reading the
# package version from that file made the inspection command fail in both
# places, so the version comes from the installed distribution instead, with
# the declared value as the fallback when the package is not installed.
PACKAGE_NAME = "aidd-commons-labs"
DECLARED_PACKAGE_VERSION = "0.2.0rc1"


def package_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return DECLARED_PACKAGE_VERSION


EXPECTED_COUNTS = {
    "rows": 7085,
    "protein_pairs": 102,
    "proteins": 171,
    "rows_with_parsed_measurement": 2544,
    "counted_pair_rows": 2487,
    "parsed_rows_without_pair_labels": 57,
}


def load_snapshot(cache_dir: Path) -> bytes:
    path = cache_dir / CACHE_FILENAME
    if not path.is_file():
        raise ValueError("snapshot is not cached; run download first")
    payload = path.read_bytes()
    validate_size(payload)
    return payload


def build_summary(
    lab_dir: Path, cache_dir: Path, *, computed_on: str | None = None
) -> dict[str, Any]:
    load_protocol(lab_dir / "protocol.json")
    result = audit_rows(rows_from_payload(load_snapshot(cache_dir)))
    if result["archive_counts"] != EXPECTED_COUNTS:
        raise ValueError("archive counts differ from the frozen source reading")
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {
            "python": platform.python_version(),
            "aidd_commons_labs": package_version(),
        },
        **result,
    }


def validate_summary(summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary schema version")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary protocol id")
    try:
        date.fromisoformat(summary["computed_on"])
    except (KeyError, TypeError, ValueError):
        failures.append("summary computation date")
    software = summary.get("software")
    if not isinstance(software, dict) or not all(
        isinstance(software.get(name), str) and software[name]
        for name in ("python", "aidd_commons_labs")
    ):
        failures.append("summary software versions")
    if summary.get("archive_counts") != EXPECTED_COUNTS:
        failures.append("archive counts")
    try:
        rows = summary["per_protein"]
        counts = summary["partner_distribution"]
        frequency = counts["proteins_by_distinct_partner_count"]
        if len(rows) != EXPECTED_COUNTS["proteins"]:
            failures.append("per-protein table length")
        if len({item["protein"] for item in rows}) != len(rows):
            failures.append("duplicate protein label")
        if (
            sum(item["measurement_count"] for item in rows)
            != 2 * EXPECTED_COUNTS["counted_pair_rows"]
        ):
            failures.append("per-protein measurement count")
        if any(item["beyond_one_partner"] != (item["distinct_partners"] > 1) for item in rows):
            failures.append("per-protein partner indicator")
        if sum(frequency.values()) != len(rows):
            failures.append("partner distribution total")
        if counts["exactly_one_partner"] != frequency.get("1", 0):
            failures.append("one-partner count")
        if not 0 <= summary["comparable_pair_count"] <= EXPECTED_COUNTS["protein_pairs"]:
            failures.append("comparable-pair count")
    except (KeyError, TypeError, ValueError):
        failures.append("missing or invalid summary field")
    if set(summary) != {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "archive_counts",
        "partner_distribution",
        "comparable_pair_count",
        "per_protein",
    }:
        failures.append("summary field set")
    return failures


def check_summary(lab_dir: Path, cache_dir: Path, artifact_path: Path) -> list[str]:
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        return [f"summary cannot be read: {error}"]
    if not isinstance(artifact, dict):
        return ["summary must be an object"]
    failures = validate_summary(artifact)
    current = build_summary(lab_dir, cache_dir, computed_on=artifact.get("computed_on"))
    for key in ("archive_counts", "partner_distribution", "comparable_pair_count", "per_protein"):
        if artifact.get(key) != current[key]:
            failures.append(f"summary differs from archive: {key}")
    return failures


def export_summary(lab_dir: Path, cache_dir: Path, output: Path) -> dict[str, Any]:
    """Refuse a changed contract or failed census before writing any output."""
    summary = build_summary(lab_dir, cache_dir)
    failures = validate_summary(summary)
    if failures:
        raise ValueError("; ".join(failures))
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
