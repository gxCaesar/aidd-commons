"""Write a compact projection only after live chain checks pass."""

from __future__ import annotations

import json
import platform
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .analysis import AuditError, analyze, check_invariants, load_records
from .protocol import load_protocol

SCHEMA_VERSION = "aidd-commons.claim-chain-audit-summary.v1"
PACKAGE_VERSION_FALLBACK = "0.2.0rc1"


def software_versions() -> dict[str, str]:
    try:
        package_version = version("aidd-commons")
    except PackageNotFoundError:
        package_version = PACKAGE_VERSION_FALLBACK
    return {
        "python": platform.python_version(),
        "pyyaml": yaml.__version__,
        "aidd_commons": package_version,
    }


def build_summary(
    root: Path,
    protocol_path: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    result = analyze(load_records(root, protocol), protocol, root)
    failures = check_invariants(result, protocol)
    if failures:
        raise AuditError("; ".join(failures))
    chains = [
        {
            "id": chain["id"],
            "link_count": chain["link_count"],
            "link_state_counts": chain["link_state_counts"],
            "weakest_link": chain["weakest_link"],
            "below_strongest_count": chain["below_strongest_count"],
            "comparison_counts": chain["comparison_counts"],
            "disagreement_count": (
                chain["comparison_counts"]["reading_shallower"]
                + chain["comparison_counts"]["reading_deeper"]
            ),
            "supported_claim": chain["supported_claim"],
            "claim_scope": chain["claim_scope"],
        }
        for chain in result["chains"]
    ]
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software if software is not None else software_versions(),
        "counted_unit": protocol["counted_unit"],
        "chains": chains,
        "total_disagreement_links": sum(chain["disagreement_count"] for chain in chains),
        "boundary_statement": result["boundary_statement"],
        "enforced_rules": {
            name: protocol["rules"][name]
            for name in ("link_resolution", "unresolved_breaks_chain", "no_biological_conclusion")
        },
    }
    if output is not None:
        output.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return summary
