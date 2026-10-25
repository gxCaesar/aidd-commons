"""Build the small, committed public summary from the cached, validated data.

No raw activity rows or bulk compound lists are included; only counts, the two
correlation summaries, and a fixed number of named divergent examples.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .analysis import correlation_summary, most_divergent, overlap_records
from .data import DataAudit, TargetDataset, load_cached_targets
from .protocol import PROTOCOL_ID, TARGETS

DIVERGENT_EXAMPLE_COUNT = 3


def _audit_dict(audit: DataAudit) -> dict[str, Any]:
    return {
        "input_rows": audit.input_rows,
        "retained_rows": audit.retained_rows,
        "parent_count": audit.parent_count,
        "duplicate_parent_count": audit.duplicate_parent_count,
        "median_duplicate_range": audit.median_duplicate_range,
        "maximum_duplicate_range": audit.maximum_duplicate_range,
        "exclusion_counts": dict(audit.exclusion_counts),
    }


def build_summary(
    datasets: dict[str, TargetDataset], *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    primary, secondary = TARGETS  # dict preserves declaration order: CHEMBL340, CHEMBL289
    primary_ds, secondary_ds = datasets[primary], datasets[secondary]
    overlap = overlap_records(primary_ds, secondary_ds)
    clean = tuple(r for r in overlap if r.is_clean_single_pair)
    shares_document = tuple(r for r in overlap if r.shares_a_document)

    return {
        "schema_version": "aidd-commons.cyp-assay-system-summary.v1",
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on,
        "software": software,
        "targets": {
            target_id: {
                "name": TARGETS[target_id],
                "admitted_parents": len(datasets[target_id].records),
                "audit": _audit_dict(datasets[target_id].audit),
            }
            for target_id in TARGETS
        },
        "overlap": {
            "full_count": len(overlap),
            "shares_document_count": len(shares_document),
            "clean_pair_count": len(clean),
        },
        "correlation": {
            "full": asdict(correlation_summary(overlap)),
            "clean_pairs_only": asdict(correlation_summary(clean)),
        },
        "divergent_examples": {
            "primary_selective": [
                asdict(example)
                for example in most_divergent(
                    clean, count=DIVERGENT_EXAMPLE_COUNT, favouring="primary"
                )
            ],
            "secondary_selective": [
                asdict(example)
                for example in most_divergent(
                    clean, count=DIVERGENT_EXAMPLE_COUNT, favouring="secondary"
                )
            ],
        },
    }


def build_summary_from_cache(
    cache_dir: Path, *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    datasets = load_cached_targets(cache_dir)
    return build_summary(datasets, computed_on=computed_on, software=software)
