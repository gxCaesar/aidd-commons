"""Build the small, committed public summary from the cached, validated data.

No raw activity rows or bulk compound lists are included; only counts, the
three pairwise correlation summaries, and a fixed number of named divergent
examples per pair.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .analysis import SYSTEM_PAIRS, correlation_summary, most_divergent, overlap_records
from .data import DataAudit, SystemDataset, load_cached_systems
from .protocol import PROTOCOL_ID, SYSTEMS

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


def _pair_key(primary_id: str, secondary_id: str) -> str:
    return f"{primary_id}_vs_{secondary_id}"


def build_summary(
    datasets: dict[str, SystemDataset], *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    for primary_id, secondary_id, varies in SYSTEM_PAIRS:
        overlap = overlap_records(datasets[primary_id], datasets[secondary_id])
        clean = tuple(r for r in overlap if r.is_clean_single_pair)
        pairs[_pair_key(primary_id, secondary_id)] = {
            "primary_system": primary_id,
            "secondary_system": secondary_id,
            "varies": varies,
            "overlap_count": len(overlap),
            "clean_pair_count": len(clean),
            "correlation": asdict(correlation_summary(overlap)),
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

    return {
        "schema_version": "aidd-commons.az-clearance-system-summary.v1",
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on,
        "software": software,
        "systems": {
            assay_id: {
                "name": SYSTEMS[assay_id][0],
                "species": SYSTEMS[assay_id][1],
                "matrix": SYSTEMS[assay_id][2],
                "admitted_parents": len(datasets[assay_id].records),
                "audit": _audit_dict(datasets[assay_id].audit),
            }
            for assay_id in SYSTEMS
        },
        "pairs": pairs,
    }


def build_summary_from_cache(
    cache_dir: Path, *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    datasets = load_cached_systems(cache_dir)
    return build_summary(datasets, computed_on=computed_on, software=software)
