"""Build the small, committed public summary from the cached, validated data.

The summary carries counts, distributions, the reference audit, the
concentration-response check and a fixed number of named examples with their
raw per-concentration values. It carries no bulk compound list and no raw
archived row beyond those named examples.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .analysis import (
    AssayProfile,
    MixSummary,
    assay_profile,
    readout_mix,
    relation_mix,
    score_summary,
    split_counts,
    split_stability,
)
from .data import AssayDataset, load_cached_assays
from .protocol import (
    CURVE_TOLERANCE_POINTS,
    DECLARED_ASSAYS,
    EQUATION_SCALE_BAND_POINTS,
    PROTOCOL_ID,
    SPLIT_RULE,
    SPLIT_SEED,
    SUMMARY_SCHEMA_VERSION,
)


def _mix(summary: MixSummary) -> dict[str, Any]:
    return {
        "counts": dict(summary.counts),
        "total": summary.total,
        "fractions": {
            key: round(summary.counts.get(key, 0) / summary.total, 6) if summary.total else 0.0
            for key in summary.counts
        },
    }


def _profile(profile: AssayProfile) -> dict[str, Any]:
    audit = profile.reference_audit
    check = profile.curve_check
    return {
        "name": profile.name,
        "endpoint": {"label": profile.endpoint_label, "unit": profile.endpoint_unit},
        "direction": profile.direction,
        "audit": {
            "input_rows": profile.input_rows,
            "retained_rows": profile.retained_rows,
            "admitted_compounds": profile.admitted_compounds,
            "exclusion_counts": dict(profile.exclusion_counts),
        },
        "outcome_mix": _mix(profile.outcome_mix),
        "relation_mix": _mix(profile.relation_mix),
        "readout_mix": _mix(profile.readout_mix),
        "confidence_score": asdict(profile.score),
        "reference_audit": {
            "declared_regime": audit.declared_regime,
            "control_keywords_in_protocol": list(audit.control_keywords),
            "ambiguous_words_in_protocol": list(audit.ambiguous_words),
            "equation_scale_verdict": audit.equation_scale_verdict,
            "fraction_inside_equation_range": audit.fraction_inside_equation_range,
            "archived_values_above_hundred": audit.archived_values_above_hundred,
            "archived_values_below_zero": audit.archived_values_below_zero,
            "reference_keywords_in_protocol": list(audit.reference_keywords),
            "references_declared": audit.references_declared,
            "normalisation_equation": audit.normalisation_equation,
            "archived_equation_text": audit.archived_equation_text,
            "equation_value_at_positive_control": audit.equation_value_at_positive_control,
            "equation_value_at_negative_control": audit.equation_value_at_negative_control,
            "equation_matches_archived_scale": audit.equation_matches_archived_scale,
            "archived_scale_low_percentile_5": audit.archived_scale_low,
            "archived_scale_high_percentile_95": audit.archived_scale_high,
            "archived_response_min": audit.archived_response_min,
            "archived_response_max": audit.archived_response_max,
            "scale_band_points": EQUATION_SCALE_BAND_POINTS,
        },
        "replicate_structure": {
            "archived_declaration": profile.replicate_declaration,
            "recorded_column": profile.determination_column,
            "recorded_kind": profile.determination_kind,
            "counts": _mix(profile.replicate_counts),
        },
        "curve_check": {
            "mode": check.mode,
            "fit_mode": profile.hill_fit_mode,
            "tolerance_points": check.tolerance_points,
            "development": asdict(check.development),
            "held_out": asdict(check.heldout),
        },
        "licensed_claims": list(profile.licensed_claims),
        "unlicensed_claims": list(profile.unlicensed_claims),
        "examples": [dict(example) for example in profile.examples],
    }


def build_summary(
    datasets: dict[int, AssayDataset],
    *,
    computed_on: str,
    software: dict[str, str],
) -> dict[str, Any]:
    """The committed summary for the declared assay set."""
    profiles = {
        aid: assay_profile(datasets[aid], seed=SPLIT_SEED) for aid in DECLARED_ASSAYS
    }
    all_rows = [row for dataset in datasets.values() for row in dataset.rows]
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_id": PROTOCOL_ID,
        "computed_on": computed_on,
        "software": software,
        "source": {
            "database": "PubChem BioAssay",
            "access": "FTP ranged container zips, one member per assay",
            "declared_assays": len(DECLARED_ASSAYS),
            "cached_bytes": sum(
                dataset.spec.source_data.record_bytes
                + dataset.spec.source_description.record_bytes
                for dataset in datasets.values()
            ),
        },
        "split": {
            "rule": SPLIT_RULE,
            "seed": SPLIT_SEED,
            "grouping_unit": "PubChem compound identifier, across the whole declared set",
            "counts": split_counts(datasets, seed=SPLIT_SEED),
        },
        "readout_mix": _mix(readout_mix(datasets)),
        "relation_mix": _mix(relation_mix(datasets)),
        "confidence_score": asdict(score_summary(all_rows)),
        "curve_tolerance_points": CURVE_TOLERANCE_POINTS,
        "assays": {str(aid): _profile(profiles[aid]) for aid in DECLARED_ASSAYS},
        "split_stability": split_stability(datasets, seed=SPLIT_SEED),
    }


def build_summary_from_cache(
    cache_dir: Path, *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    datasets = load_cached_assays(cache_dir)
    return build_summary(datasets, computed_on=computed_on, software=software)
