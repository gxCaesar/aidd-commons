"""Audit separate claims, evidence references and literal licence-scope limits."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .protocol import ACCESS_VALUES, DIMENSIONS, LIFECYCLE_VALUES, OPENNESS_VALUES

# This is a literal text rule, not an interpretation of legal effect.
SCOPE_LIMIT_WORDS = ("only", "not", "no separate terms", "does not")


class AuditError(ValueError):
    """The catalogue violates a declared structural or evidence invariant."""


def scope_limits_grant(scope: str) -> bool:
    return bool(re.search(r"\b(?:only|not|no separate terms|does not)\b", scope, re.IGNORECASE))


def audit_record(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    identifier = str(record.get("id", "<missing>"))
    entries = record.get("evidence")
    if not isinstance(entries, list):
        entries = []
        errors.append("evidence entries missing")
    evidence_entries: dict[str, dict[str, Any]] = {}
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append("evidence entry has no id")
            continue
        if item["id"] in evidence_entries:
            errors.append(f"duplicate evidence id: {item['id']}")
        evidence_entries[item["id"]] = {"url": item.get("url"), "label": item.get("label")}
    evidence_ids = set(evidence_entries)

    def claim(value: Any, location: str, allowed: tuple[str, ...]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("value") not in allowed:
            errors.append(f"{location} has no allowed claim value")
            return {"value": None, "evidence": []}
        references = value.get("evidence", [])
        if not isinstance(references, list):
            references = []
            errors.append(f"{location} evidence is not a list")
        if value["value"] != "unverified" and not references:
            errors.append(f"{location} has no evidence reference")
        for reference in references:
            if not isinstance(reference, str) or reference not in evidence_ids:
                errors.append(f"{location} names missing evidence: {reference}")
        return {"value": value["value"], "evidence": references}

    openness = record.get("openness")
    if not isinstance(openness, dict):
        openness = {}
    separate = set(openness) == set(DIMENSIONS)
    if not separate:
        errors.append("seven openness dimensions are not separate fields")
    dimensions = {
        name: claim(openness[name], f"openness.{name}", OPENNESS_VALUES)
        for name in DIMENSIONS
        if name in openness
    }
    status = claim(record.get("status"), "status", LIFECYCLE_VALUES)
    access = claim(record.get("access_level"), "access_level", ACCESS_VALUES)
    licenses: list[dict[str, Any]] = []
    raw_licenses = record.get("licenses")
    if not isinstance(raw_licenses, list):
        raw_licenses = []
        errors.append("licenses is not a list")
    for index, item in enumerate(raw_licenses):
        if not isinstance(item, dict):
            errors.append(f"licenses.{index} is not an object")
            continue
        name, scope, refs = item.get("name"), item.get("scope"), item.get("evidence")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"licenses.{index} has no name")
        if not isinstance(scope, str) or not scope.strip():
            errors.append(f"licenses.{index} has no scope")
        if not isinstance(refs, list) or not refs:
            errors.append(f"licenses.{index} has no evidence reference")
            refs = []
        for reference in refs:
            if not isinstance(reference, str) or reference not in evidence_ids:
                errors.append(f"licenses.{index} names missing evidence: {reference}")
        licenses.append(
            {
                "name": name,
                "scope": scope,
                "evidence": refs,
                "limits_grant": scope_limits_grant(scope) if isinstance(scope, str) else False,
            }
        )
    caveats = record.get("caveats")
    if not isinstance(caveats, list) or not all(isinstance(item, str) for item in caveats):
        errors.append("caveats is not a text list")
        caveats = []
    return {
        "id": identifier,
        "evidence_entries": evidence_entries,
        "dimensions": dimensions,
        "status": status,
        "access_level": access,
        "licenses": licenses,
        "caveats": caveats,
        "last_verified": record.get("last_verified"),
        "seven_fields_separate": separate,
        "all_claim_evidence_resolves": not any(
            "evidence" in error or "claim value" in error for error in errors
        ),
        "all_licenses_scoped": len(licenses) == len(raw_licenses)
        and all(bool(item.get("scope")) for item in licenses),
        "scope_limits_grant": any(item["limits_grant"] for item in licenses),
        "errors": errors,
    }


def analyze(catalogue: dict[str, dict[str, Any]], examined_ids: tuple[str, ...]) -> dict[str, Any]:
    records = [audit_record(catalogue[identifier]) for identifier in examined_ids]
    dimension_counts = Counter(
        claim["value"] for row in records for claim in row["dimensions"].values()
    )
    counts = {
        "available": dimension_counts["available"],
        "not_applicable": dimension_counts["not_applicable"],
        "unverified": dimension_counts["unverified"],
        "not_available": dimension_counts["not_available"],
        "records_with_license": sum(bool(row["licenses"]) for row in records),
        "records_without_verified_access": sum(
            row["access_level"]["value"] == "unverified" for row in records
        ),
        "records_with_scope_limit": sum(row["scope_limits_grant"] for row in records),
    }
    whole = {
        "records": len(catalogue),
        "records_with_seven_separate_dimensions": sum(
            isinstance(row.get("openness"), dict) and set(row["openness"]) == set(DIMENSIONS)
            for row in catalogue.values()
        ),
    }
    return {"records": records, "examined_counts": counts, "whole_catalogue": whole}


def check_invariants(result: dict[str, Any], examined_ids: tuple[str, ...]) -> list[str]:
    failures = [f"{row['id']}: {error}" for row in result["records"] for error in row["errors"]]
    if [row["id"] for row in result["records"]] != list(examined_ids):
        failures.append("record order differs from protocol")
    counts = result["examined_counts"]
    if sum(counts[key] for key in OPENNESS_VALUES) != len(examined_ids) * len(DIMENSIONS):
        failures.append("dimension counts do not cover every examined cell")
    whole = result["whole_catalogue"]
    if whole["records_with_seven_separate_dimensions"] != whole["records"]:
        failures.append("a catalogue record collapses or omits openness dimensions")
    return failures
