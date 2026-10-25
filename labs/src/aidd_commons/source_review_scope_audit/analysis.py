"""Count entry-level source bindings and resolve structured claim references."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from .protocol import EXAMINED_IDS, PART_FIELDS, calendar_date

DIMENSIONS = (
    "inference_code",
    "training_code",
    "weights",
    "architecture",
    "data_recipe",
    "training_data",
    "evaluation_code",
)
STATUSES = ("carried", "named-in-text", "absent")
DATE_IN_TEXT = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
VERSION_IN_TEXT = re.compile(
    r"\b(?:release|version|tag)\s+[A-Za-z0-9._-]+\b|\bv\d+(?:\.\d+)+\b|"
    r"\bpolicy dated \d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)
MATERIAL_IN_TEXT = re.compile(
    r"\b(?:readme|licen[cs]e|policy|terms page|documentation|paper|"
    r"supplement|appendix|table|section)\b",
    re.IGNORECASE,
)


class AuditError(ValueError):
    """The audit finds a broken source or summary invariant."""


def entry_parts(entry: dict[str, Any]) -> dict[str, str]:
    """A label or record-level date cannot supply an entry-level field."""
    url = entry.get("url")
    parsed = urlparse(url) if isinstance(url, str) else None
    surface = bool(parsed and parsed.scheme in ("http", "https") and parsed.netloc)
    raw_label = entry.get("label")
    label = raw_label if isinstance(raw_label, str) else ""
    source_text = f"{label} {url if isinstance(url, str) else ''}"
    version = entry.get("version")
    reviewed_scope = entry.get("reviewed_scope")
    return {
        "surface": "carried" if surface else ("named-in-text" if label.strip() else "absent"),
        "version": "carried"
        if isinstance(version, str) and version.strip()
        else ("named-in-text" if VERSION_IN_TEXT.search(source_text) else "absent"),
        "date": "carried"
        if calendar_date(entry.get("reviewed_on"))
        else ("named-in-text" if DATE_IN_TEXT.search(label) else "absent"),
        "scope": "carried"
        if isinstance(reviewed_scope, str) and reviewed_scope.strip()
        else ("named-in-text" if MATERIAL_IN_TEXT.search(label) else "absent"),
    }


def audit_record(record: dict[str, Any]) -> dict[str, Any]:
    identifier = str(record.get("id", "<missing>"))
    errors: list[str] = []
    raw_entries = record.get("evidence")
    if not isinstance(raw_entries, list):
        raw_entries = []
        errors.append("evidence is not a list")
    entries: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"]:
            errors.append(f"evidence.{index} has no id")
            continue
        evidence_id = entry["id"]
        if evidence_id in by_id:
            errors.append(f"duplicate evidence id: {evidence_id}")
            continue
        by_id[evidence_id] = entry
        if not isinstance(entry.get("label"), str) or not entry["label"].strip():
            errors.append(f"evidence.{evidence_id} has no label")
        supports = entry.get("supports")
        if not isinstance(supports, list) or any(not isinstance(item, str) for item in supports):
            errors.append(f"evidence.{evidence_id} has invalid supports")
        for field in ("version", "reviewed_scope"):
            if field in entry and (not isinstance(entry[field], str) or not entry[field].strip()):
                errors.append(f"evidence.{evidence_id} has invalid {field}")
        if "reviewed_on" in entry and not calendar_date(entry["reviewed_on"]):
            errors.append(f"evidence.{evidence_id} has invalid reviewed_on")
        parts = entry_parts(entry)
        if "url" in entry and parts["surface"] != "carried":
            errors.append(f"evidence.{evidence_id} has invalid url")
        entries.append(
            {
                "id": evidence_id,
                "url": entry.get("url"),
                "label": entry.get("label"),
                "supports": supports,
                "parts": parts,
            }
        )

    raw_openness = record.get("openness")
    if not isinstance(raw_openness, dict) or set(raw_openness) != set(DIMENSIONS):
        errors.append("seven openness claims are not separate")
        raw_openness = raw_openness if isinstance(raw_openness, dict) else {}
    raw_licenses = record.get("licenses")
    if not isinstance(raw_licenses, list):
        errors.append("licenses is not a list")
        raw_licenses = []
    raw_claims: list[tuple[str, Any]] = [
        ("status", record.get("status")),
        ("access_level", record.get("access_level")),
    ]
    raw_claims.extend((f"openness.{name}", raw_openness.get(name)) for name in DIMENSIONS)
    for index, license_claim in enumerate(raw_licenses):
        if not isinstance(license_claim, dict) or not all(
            isinstance(license_claim.get(field), str) and license_claim[field].strip()
            for field in ("name", "scope")
        ):
            errors.append(f"licenses.{index} has no name or scope")
        raw_claims.append((f"licenses.{index}", license_claim))

    claims: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    for path, value in raw_claims:
        if not isinstance(value, dict):
            errors.append(f"{path} is not a claim object")
            continue
        claim_value = value.get("value", value.get("name"))
        if not isinstance(claim_value, str) or not claim_value.strip():
            errors.append(f"{path} has no value")
        refs = value.get("evidence", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            errors.append(f"{path} has invalid evidence references")
            refs = []
        if claim_value != "unverified" and not refs:
            errors.append(f"{path} has no evidence reference")
        references: list[dict[str, Any]] = []
        for reference in refs:
            entry = by_id.get(reference)
            resolves = entry is not None
            carries_date = bool(entry and entry_parts(entry)["date"] == "carried")
            references.append({"id": reference, "resolves": resolves, "carries_date": carries_date})
            if not resolves:
                errors.append(f"{path} names missing evidence: {reference}")
                unresolved.append(
                    {"record_id": identifier, "claim": path, "evidence_id": reference}
                )
            elif entry is not None and entry_parts(entry)["surface"] != "carried":
                errors.append(f"{path} cites evidence without a URL: {reference}")
        claims.append({"path": path, "value": claim_value, "references": references})

    part_counts = {
        part: {status: sum(row["parts"][part] == status for row in entries) for status in STATUSES}
        for part in PART_FIELDS
    }
    special_counts = {
        "all_four": sum(
            all(state == "carried" for state in row["parts"].values()) for row in entries
        ),
        "date_surface_no_version": sum(
            row["parts"]["date"] == "carried"
            and row["parts"]["surface"] == "carried"
            and row["parts"]["version"] != "carried"
            for row in entries
        ),
        "name_only": sum(
            row["parts"]["surface"] == "named-in-text"
            and all(row["parts"][part] != "carried" for part in PART_FIELDS)
            for row in entries
        ),
    }
    claim_counts = {
        "claims": len(claims),
        "claims_with_reference": sum(bool(claim["references"]) for claim in claims),
        "claims_without_reference": sum(not claim["references"] for claim in claims),
        "claims_with_dated_reference": sum(
            any(ref["carries_date"] for ref in claim["references"]) for claim in claims
        ),
        "claims_with_unresolved_reference": sum(
            any(not ref["resolves"] for ref in claim["references"]) for claim in claims
        ),
    }
    return {
        "id": identifier,
        "entries": entries,
        "claims": claims,
        "caveats": record.get("caveats", []),
        "evidence_entries": len(entries),
        "part_counts": part_counts,
        "special_counts": special_counts,
        "claim_counts": claim_counts,
        "unresolved_claim_references": unresolved,
        "errors": errors,
    }


def analyze(
    catalogue: dict[str, dict[str, Any]],
    examined_ids: tuple[str, ...] = EXAMINED_IDS,
) -> dict[str, Any]:
    records = [audit_record(catalogue[identifier]) for identifier in examined_ids]
    totals = {
        "records": len(records),
        "evidence_entries": sum(row["evidence_entries"] for row in records),
        "parts": {
            part: {
                status: sum(row["part_counts"][part][status] for row in records)
                for status in STATUSES
            }
            for part in PART_FIELDS
        },
        "special": {
            key: sum(row["special_counts"][key] for row in records)
            for key in ("all_four", "date_surface_no_version", "name_only")
        },
        "claims": {
            key: sum(row["claim_counts"][key] for row in records)
            for key in (
                "claims",
                "claims_with_reference",
                "claims_without_reference",
                "claims_with_dated_reference",
                "claims_with_unresolved_reference",
            )
        },
    }
    return {
        "records": records,
        "totals": totals,
        "unresolved_claim_references": [
            item for row in records for item in row["unresolved_claim_references"]
        ],
    }


def check_invariants(result: dict[str, Any], examined_ids: tuple[str, ...]) -> list[str]:
    failures = [f"{row['id']}: {error}" for row in result["records"] for error in row["errors"]]
    if [row["id"] for row in result["records"]] != list(examined_ids):
        failures.append("record order differs from protocol")
    for row in result["records"]:
        for part in PART_FIELDS:
            if sum(row["part_counts"][part].values()) != row["evidence_entries"]:
                failures.append(f"{row['id']}: part count does not cover evidence entries: {part}")
        counts = row["claim_counts"]
        if counts["claims_with_reference"] + counts["claims_without_reference"] != counts["claims"]:
            failures.append(f"{row['id']}: claim counts do not cover claims")
    totals = result["totals"]
    if totals["evidence_entries"] != sum(row["evidence_entries"] for row in result["records"]):
        failures.append("total evidence count differs from per-record counts")
    return failures
