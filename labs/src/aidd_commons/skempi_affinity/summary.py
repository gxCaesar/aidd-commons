"""Build the compact public result and guard output creation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .analysis import AnalysisContractError, analyze, check_invariants
from .data import load_cached
from .protocol import PROTOCOL_ID, load_protocol


def build_summary(
    protocol_path: Path,
    cache_dir: Path,
    *,
    computed_on: str | None = None,
    software: dict[str, str] | None = None,
    results_dir: Path | None = None,
) -> dict[str, Any]:
    """Validate first, compute second, and only then create an optional run directory."""
    protocol = load_protocol(protocol_path)
    dataset = load_cached(cache_dir)
    result = analyze(dataset)
    failures = check_invariants(dataset, result)
    if failures:
        raise AnalysisContractError("; ".join(failures))
    classes = result["classes"]
    summary: dict[str, Any] = {
        "schema_version": "aidd-commons.skempi-affinity-summary.v1",
        "protocol_id": protocol["protocol_id"],
        "computed_on": computed_on or date.today().isoformat(),
        "software": software or {},
        "counts": {
            "rows": result["rows"],
            "complexes": result["complexes"],
            "complete_pairs": result["complete_pairs"],
            "fragmented_rows": result["fragmented_rows"],
            "eligible_ab_ag_rows": result["eligible_rows"],
            "field_counts": result["field_counts"],
            "classes": {
                name: {
                    key: value for key, value in item.items()
                    if key not in {"top_five_share", "top_five_complexes"}
                }
                for name, item in classes.items()
            },
        },
        "concentration_shares": {
            name: item["top_five_share"] for name, item in classes.items()
        },
        "named_complexes": classes["AB/AG"]["top_five_complexes"][:3],
        "row_split_diagnostic": result["row_split_diagnostic"],
        "complex_holdout": result["complex_holdout"],
    }
    if summary["protocol_id"] != PROTOCOL_ID:
        raise AnalysisContractError("summary protocol differs from frozen contract")
    if results_dir is not None:
        if results_dir.exists():
            raise FileExistsError("results directory already exists")
        results_dir.mkdir(parents=True)
        (results_dir / "run-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return summary
