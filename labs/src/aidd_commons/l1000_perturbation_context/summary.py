"""Build the small, committed public summary from the cached, validated data.

No raw expression vectors, instance-level rows or bulk compound lists are
included; only counts, audits, the matched-versus-null distribution summary,
the rank-sum comparison, and a fixed number of named examples.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .analysis import (
    compare_matched_to_null,
    matched_pairs,
    most_divergent,
    null_pairs,
    summarize,
)
from .data import CellLineDataset, DataAudit, load_cached_cell_lines
from .protocol import CELL_LINE_A, CELL_LINE_B, FIXED_DOSE, FIXED_TIME, PROTOCOL_ID

DIVERGENT_EXAMPLE_COUNT = 3


def _audit_dict(audit: DataAudit) -> dict[str, Any]:
    return {
        "input_rows": audit.input_rows,
        "retained_rows": audit.retained_rows,
        "admitted_entity_count": audit.admitted_entity_count,
        "duplicate_entity_count": audit.duplicate_entity_count,
        "exclusion_counts": dict(audit.exclusion_counts),
    }


def build_summary(
    datasets: dict[str, CellLineDataset], *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    a, b = datasets[CELL_LINE_A], datasets[CELL_LINE_B]
    matched = matched_pairs(a, b)
    null = null_pairs(a, b)

    return {
        "schema_version": "aidd-commons.l1000-perturbation-context-summary.v1",
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on,
        "software": software,
        "fixed_condition": {"time": FIXED_TIME, "dose": FIXED_DOSE},
        "cell_lines": {
            CELL_LINE_A: _audit_dict(a.audit),
            CELL_LINE_B: _audit_dict(b.audit),
        },
        "shared_compound_count": len(matched),
        "matched": asdict(summarize(matched)),
        "null_mismatched": asdict(summarize(null)),
        "rank_sum_comparison": asdict(compare_matched_to_null(matched, null)),
        "examples": {
            "most_reproducible": [
                {"pert_id": p.pert_id, "pert_iname": p.pert_iname, "spearman_rho": p.spearman_rho}
                for p in most_divergent(
                    matched, count=DIVERGENT_EXAMPLE_COUNT, favouring="reproducible"
                )
            ],
            "most_divergent": [
                {"pert_id": p.pert_id, "pert_iname": p.pert_iname, "spearman_rho": p.spearman_rho}
                for p in most_divergent(
                    matched, count=DIVERGENT_EXAMPLE_COUNT, favouring="divergent"
                )
            ],
        },
    }


def build_summary_from_cache(
    cache_dir: Path, *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    datasets = load_cached_cell_lines(cache_dir)
    return build_summary(datasets, computed_on=computed_on, software=software)
