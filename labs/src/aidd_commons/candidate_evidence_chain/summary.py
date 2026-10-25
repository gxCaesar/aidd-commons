"""Build and audit the compact candidate-chain summary."""

from __future__ import annotations

import json
import platform
from collections import Counter
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy
import rdkit

from aidd_commons.multi_endpoint_integration.summary import build_summary as build_integration

from .analysis import audit_chains, make_chains
from .protocol import (
    BOUNDARY_STATEMENT,
    EXAMPLE_PARENTS,
    LINKS,
    PACKAGE_VERSION_FALLBACK,
    PROTOCOL_ID,
    STATES,
    SUMMARY_SCHEMA_VERSION,
    expected_contract,
    load_protocol_document,
)


class SummaryContractError(ValueError):
    """The summary violates the chain rule or differs from cached evidence."""


def software_versions() -> dict[str, str]:
    try:
        package_version = version("aidd-commons-labs")
    except PackageNotFoundError:
        package_version = PACKAGE_VERSION_FALLBACK
    return {
        "aidd_commons_labs": package_version,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "rdkit": rdkit.__version__,
    }


def build_summary(cache_root: Path, *, computed_on: str | None = None) -> dict[str, Any]:
    """Read owning caches through the validated multi-endpoint integration."""
    integration = build_integration(cache_root, computed_on=computed_on)
    chains = make_chains(integration["profiles"])
    first = Counter(chain["first_non_measured"] or "none" for chain in chains)
    states_by_link = {
        name: dict(Counter(chain["links"][index]["state"] for chain in chains))
        for index, name in enumerate(LINKS)
    }
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on or date.today().isoformat(),
        "software": software_versions(),
        "links": list(LINKS),
        "chains": chains,
        "states_by_link": states_by_link,
        "first_non_measured_distribution": dict(first),
        "claim_count": sum(chain["supports_claim"] for chain in chains),
        "boundary_statement": BOUNDARY_STATEMENT,
        "rules": expected_contract()["rules"],
    }
    audit_summary(summary)
    return summary


def audit_summary(summary: dict[str, Any]) -> None:
    """Check state accounting and the no-gap claim gate without a cache read."""
    required = {
        "schema_version",
        "protocol_id",
        "computed_on",
        "software",
        "links",
        "chains",
        "states_by_link",
        "first_non_measured_distribution",
        "claim_count",
        "boundary_statement",
        "rules",
    }
    if set(summary) != required:
        raise SummaryContractError("summary fields differ from contract")
    if summary["schema_version"] != SUMMARY_SCHEMA_VERSION or summary["protocol_id"] != PROTOCOL_ID:
        raise SummaryContractError("summary version differs")
    try:
        date.fromisoformat(summary["computed_on"])
    except (TypeError, ValueError) as error:
        raise SummaryContractError("invalid computation date") from error
    if (
        summary["links"] != list(LINKS)
        or summary["rules"] != expected_contract()["rules"]
        or summary["boundary_statement"] != BOUNDARY_STATEMENT
    ):
        raise SummaryContractError("link, rule or boundary differs")
    if not isinstance(summary["software"], dict) or not all(
        isinstance(value, str) and value for value in summary["software"].values()
    ):
        raise SummaryContractError("software versions are invalid")
    chains = summary["chains"]
    if [chain["parent_chembl_id"] for chain in chains] != list(EXAMPLE_PARENTS):
        raise SummaryContractError("declared compound units differ")
    try:
        audit_chains(chains)
    except (KeyError, TypeError, ValueError) as error:
        raise SummaryContractError(str(error)) from error
    state_counts = {
        name: dict(Counter(chain["links"][index]["state"] for chain in chains))
        for index, name in enumerate(LINKS)
    }
    first = dict(Counter(chain["first_non_measured"] or "none" for chain in chains))
    if (
        summary["states_by_link"] != state_counts
        or summary["first_non_measured_distribution"] != first
    ):
        raise SummaryContractError("state or first-stop distribution differs")
    if summary["claim_count"] != sum(chain["supports_claim"] for chain in chains):
        raise SummaryContractError("claim count differs")
    if any(
        sum(chain["counts"].values()) != len(LINKS) or set(chain["counts"]) != set(STATES)
        for chain in chains
    ):
        raise SummaryContractError("per-chain link states do not partition the chain")


def check_summary(committed: dict[str, Any], computed: dict[str, Any]) -> None:
    audit_summary(committed)
    audit_summary(computed)
    for field, value in computed.items():
        if field not in {"computed_on", "software"} and committed[field] != value:
            raise SummaryContractError(f"committed {field} differs from cached computation")


def export_summary(
    lab_dir: Path,
    cache_root: Path,
    output_path: Path,
    *,
    candidate: dict[str, Any] | None = None,
) -> None:
    """Write only after frozen protocol and cached candidate checks pass."""
    load_protocol_document(lab_dir / "protocol.json")
    computed = build_summary(cache_root)
    selected = computed if candidate is None else candidate
    check_summary(selected, computed)
    output_path.write_text(
        json.dumps(selected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
