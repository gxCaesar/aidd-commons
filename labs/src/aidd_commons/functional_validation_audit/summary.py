"""Build and check the small count-only artifact."""

from __future__ import annotations

import json
import platform
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import rdkit

from aidd_commons.assay_endpoint_controls.protocol import DECLARED_ASSAYS
from aidd_commons.decision_unit_scope.protocol import CHEMBL_RELEASE_DATE, ENDPOINT_TYPES

from .analysis import CLAIMS, TABLE_CHEMBL, TABLE_PUBCHEM, audit_tables
from .protocol import (
    KIND_BOUND,
    KIND_NONE,
    KINDS,
    LIMIT_STATEMENT,
    PROTOCOL_ID,
    RULE_STATEMENT,
    SUMMARY_SCHEMA_VERSION,
    UNMEASURABLE_ROUTES,
    load_protocol,
)
from .records import load_tables


def build_summary(
    lab_dir: Path, chembl_cache: Path, pubchem_cache: Path, *, computed_on: str | None = None
) -> dict[str, Any]:
    load_protocol(lab_dir / "protocol.json")
    tables = load_tables(chembl_cache, pubchem_cache)
    result = audit_tables(tables)
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": {"python": platform.python_version(), "rdkit": rdkit.__version__},
        "sources": {
            TABLE_CHEMBL: {"release": "ChEMBL_37", "release_date": CHEMBL_RELEASE_DATE},
            TABLE_PUBCHEM: {"archive": "PubChem BioAssay", "read_on": "2026-10-21"},
        },
        **result,
        "rule_statement": RULE_STATEMENT,
        "limit_statement": LIMIT_STATEMENT,
    }


def validate_summary(summary: Mapping[str, Any]) -> list[str]:
    """Reject inconsistent counts and any expansion of the claim boundary."""
    failures: list[str] = []
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        failures.append("summary schema version")
    if summary.get("protocol_id") != PROTOCOL_ID:
        failures.append("summary protocol id")
    if not summary.get("computed_on") or not summary.get("software"):
        failures.append("summary date or software")
    if summary.get("unmeasurable_routes") != UNMEASURABLE_ROUTES:
        failures.append("unmeasurable routes")
    if (
        summary.get("rule_statement") != RULE_STATEMENT
        or summary.get("limit_statement") != LIMIT_STATEMENT
    ):
        failures.append("claim rule statement")
    try:
        tables = summary["tables"]
        if set(tables) != {TABLE_CHEMBL, TABLE_PUBCHEM}:
            failures.append("table names")
        no_claim = 0
        for table in (TABLE_CHEMBL, TABLE_PUBCHEM):
            counts = tables[table]["kind_counts"]
            total = tables[table]["total_records"]
            if set(counts) != set(KINDS) or any(
                type(value) is not int or value < 0 for value in counts.values()
            ):
                failures.append(f"{table} kind counts")
            if type(total) is not int or total != sum(counts.values()):
                failures.append(f"{table} total")
            no_claim += counts[KIND_NONE]
        if no_claim != summary["records_licensing_no_claim"]:
            failures.append("records licensing no claim")
        chembl_types = summary["chembl_standard_type_counts"]
        if (
            set(chembl_types) != set(ENDPOINT_TYPES)
            or sum(chembl_types.values()) != tables[TABLE_CHEMBL]["total_records"]
        ):
            failures.append("ChEMBL standard-type counts")
        if summary["chembl_bound_measurements"] != tables[TABLE_CHEMBL]["kind_counts"][KIND_BOUND]:
            failures.append("ChEMBL bound count")
        assays = summary["pubchem_assays"]
        if set(assays) != {str(aid) for aid in DECLARED_ASSAYS}:
            failures.append("PubChem assay set")
        if (
            sum(item["total_records"] for item in assays.values())
            != tables[TABLE_PUBCHEM]["total_records"]
        ):
            failures.append("PubChem assay totals")
        for aid, item in assays.items():
            value_total = sum(item["endpoint_counts"].values())
            if value_total != (item["stated_qualifier_values"] + item["unstated_relation_values"]):
                failures.append(f"assay {aid} endpoint relations")
            if item["stated_qualifier_values"] != (item["equality_values"] + item["bound_values"]):
                failures.append(f"assay {aid} stated relations")
            if sum(item["qualifier_row_counts"].values()) != item["total_records"]:
                failures.append(f"assay {aid} qualifier rows")
        claim_counts = summary["licensed_claim_counts"]
        if set(claim_counts) != set(CLAIMS) or claim_counts["clinical_outcome"] != 0:
            failures.append("licensed claim counts")
        if (
            claim_counts["functional_response"]
            != tables[TABLE_PUBCHEM]["kind_counts"]["concentration_response_table"]
        ):
            failures.append("response claim count")
    except (KeyError, TypeError, ValueError) as error:
        failures.append(f"missing or invalid count: {error}")
    raw = json.dumps(summary)
    if '"activities"' in raw or '"canonical_smiles"' in raw or '"points"' in raw:
        failures.append("raw records in count artifact")
    if len(raw) > 20_000:
        failures.append("summary exceeds the count-only limit")
    return failures


def export_summary(
    lab_dir: Path, chembl_cache: Path, pubchem_cache: Path, output: Path
) -> dict[str, Any]:
    """Do all checks before touching the output path."""
    summary = build_summary(lab_dir, chembl_cache, pubchem_cache)
    failures = validate_summary(summary)
    if failures:
        raise ValueError("; ".join(failures))
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
