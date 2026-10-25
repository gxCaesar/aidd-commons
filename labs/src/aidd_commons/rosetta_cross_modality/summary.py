"""Project the cached, validated data into the small committed summary.

The committed summary carries counts, the variance attribution of plate and
batch, the frozen evaluation set, and a fixed number of named examples. It
carries no raw well rows, no per-perturbation profiles and no bulk lists of
perturbation identifiers. The full computed result, including the agreement
value of every individual perturbation, is written beside it as a run
artefact and is not part of the committed record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .analysis import (
    SplitResult,
    batch_blocked_folds,
    evaluate,
    neighbourhood_concordance,
    permute_within_group,
    plate_blocked_folds,
    random_folds,
    size_matched_partition_folds,
    size_matched_random_folds,
    variance_shares,
)
from .data import Dataset, Fetcher, download_and_cache_snapshot, load_cached_dataset
from .protocol import Contract

SURVIVAL_DEFINITION = (
    "survival_ratio = (blocked_feature_r - null_feature_r) / "
    "(apparent_feature_r - null_feature_r); the share of the above-null "
    "cross-modal agreement that remains when the batch or plate structure is "
    "held out of the training side"
)

# The fields of the computed summary that are committed. The per-perturbation
# agreement values and the run artefact's own bookkeeping stay out of the
# committed record.
COMMITTED_FIELDS = (
    "schema_version",
    "protocol_id",
    "computed_on",
    "software",
    "source",
    "features",
    "counts",
    "variance_attribution",
    "evaluations",
    "survival",
    "model_free_check",
    "examples",
)


def _matrices(dataset: Dataset) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    x = np.array([p.transcriptome for p in dataset.perturbations], dtype=np.float64)
    y = np.array([p.imaging for p in dataset.perturbations], dtype=np.float64)
    return x, y


def _split_result(result: SplitResult) -> dict[str, Any]:
    return {
        "folds": result.folds,
        "tested_perturbations": result.tested_perturbations,
        "perturbation_r": result.perturbation_r,
        "feature_r": result.feature_r,
        "train_sizes": list(result.train_sizes),
        "test_sizes": list(result.test_sizes),
        "alphas": list(result.alphas),
    }


def build_summary(
    dataset: Dataset, contract: Contract, *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    """Run the frozen evaluation set over the assembled entities."""
    x, y = _matrices(dataset)
    perturbations = dataset.perturbations
    seed = contract.seed
    alphas = contract.ridge_alphas
    inner_folds = contract.inner_folds

    batches = tuple(perturbation.batch for perturbation in perturbations)
    batch_names = tuple(sorted({batch for batch in batches if batch is not None}))
    imaging_membership = tuple(frozenset(p.imaging_plates) for p in perturbations)
    transcriptome_membership = tuple(frozenset(p.transcriptome_plates) for p in perturbations)
    imaging_plates = tuple(sorted({plate for p in perturbations for plate in p.imaging_plates}))
    transcriptome_plates = tuple(
        sorted({plate for p in perturbations for plate in p.transcriptome_plates})
    )

    everything = np.arange(len(perturbations), dtype=np.int64)
    apparent_folds = random_folds(len(perturbations), contract.outer_folds, seed)
    apparent = evaluate(
        "apparent", x, y, apparent_folds, alphas, inner_folds, seed
    )

    permuted_y = permute_within_group(y, batches, seed)
    null = evaluate(
        "null_within_batch_permuted", x, permuted_y, apparent_folds, alphas, inner_folds, seed
    )

    batch_folds = batch_blocked_folds(batches, batch_names)
    batch_blocked = evaluate(
        "batch_blocked", x, y, batch_folds, alphas, inner_folds, seed
    )
    batch_sizes = tuple((fold.train.size, fold.test.size) for fold in batch_folds)
    batch_pool = np.array(
        [index for index, batch in enumerate(batches) if batch is not None], dtype=np.int64
    )
    batch_size_matched = evaluate(
        "size_matched_random_batch",
        x,
        y,
        size_matched_partition_folds(batch_pool, batch_sizes, seed),
        alphas,
        inner_folds,
        seed,
    )

    imaging_folds = plate_blocked_folds(imaging_membership, imaging_plates)
    imaging_blocked = evaluate(
        "plate_blocked_imaging", x, y, imaging_folds, alphas, inner_folds, seed
    )
    imaging_sizes = tuple((fold.train.size, fold.test.size) for fold in imaging_folds)
    imaging_size_matched = evaluate(
        "size_matched_random_imaging_plate",
        x,
        y,
        size_matched_random_folds(everything, imaging_sizes, seed),
        alphas,
        inner_folds,
        seed,
    )

    transcriptome_folds = plate_blocked_folds(transcriptome_membership, transcriptome_plates)
    transcriptome_blocked = evaluate(
        "plate_blocked_transcriptome", x, y, transcriptome_folds, alphas, inner_folds, seed
    )
    transcriptome_sizes = tuple((fold.train.size, fold.test.size) for fold in transcriptome_folds)
    transcriptome_size_matched = evaluate(
        "size_matched_random_transcriptome_plate",
        x,
        y,
        size_matched_random_folds(everything, transcriptome_sizes, seed),
        alphas,
        inner_folds,
        seed,
    )

    concordance = neighbourhood_concordance(x, y)
    concordance_null = neighbourhood_concordance(x, permuted_y)

    well_values = _well_values(dataset)
    attribution = {
        "transcriptome_plate": variance_shares(
            well_values["transcriptome"], well_values["transcriptome_plate"]
        ),
        "imaging_plate": variance_shares(
            well_values["imaging"], well_values["imaging_plate"]
        ),
        "imaging_batch": variance_shares(
            well_values["imaging"], well_values["imaging_batch"]
        ),
    }

    examples = _examples(perturbations, apparent.per_perturbation_r, contract.example_count)

    return {
        "schema_version": "aidd-commons.rosetta-cross-modality-summary.v1",
        "protocol_id": contract.protocol_id,
        "computed_on": computed_on,
        "software": software,
        "source": {
            "study_id": contract.study_id,
            "batch_id": contract.batch_id,
            "cell_line": contract.cell_line,
            "files": {
                source.key: {
                    "byte_length": source.byte_length,
                    "s3_etag": source.s3_etag,
                }
                for source in contract.files
            },
        },
        "features": {
            "transcriptome": len(dataset.transcriptome_features),
            "imaging": len(dataset.imaging_features),
        },
        "counts": {
            "transcriptome": {
                "input_rows": dataset.audit.transcriptome_input_rows,
                "control_rows": dataset.audit.transcriptome_control_rows,
                "treated_rows": dataset.audit.transcriptome_treated_rows,
                "distinct_wells": dataset.audit.transcriptome_distinct_wells,
                "perturbations": dataset.audit.transcriptome_perturbations,
                "plates": dataset.audit.transcriptome_plates,
            },
            "imaging": {
                "input_rows": dataset.audit.imaging_input_rows,
                "control_rows": dataset.audit.imaging_control_rows,
                "treated_rows": dataset.audit.imaging_treated_rows,
                "distinct_wells": dataset.audit.imaging_distinct_wells,
                "perturbations": dataset.audit.imaging_perturbations,
                "plates": dataset.audit.imaging_plates,
                "batches": dataset.audit.imaging_batches,
            },
            "admitted_perturbations": dataset.audit.admitted_perturbations,
            "batch_pure_perturbations": dataset.audit.batch_pure_perturbations,
            "batch_mixed_perturbations": dataset.audit.batch_mixed_perturbations,
            "exclusion_counts": dataset.audit.exclusion_counts,
        },
        "variance_attribution": attribution,
        "evaluations": {
            "apparent": _split_result(apparent),
            "null_within_batch_permuted": _split_result(null),
            "batch_blocked": _split_result(batch_blocked),
            "size_matched_random_batch": _split_result(batch_size_matched),
            "plate_blocked_imaging": _split_result(imaging_blocked),
            "size_matched_random_imaging_plate": _split_result(imaging_size_matched),
            "plate_blocked_transcriptome": _split_result(transcriptome_blocked),
            "size_matched_random_transcriptome_plate": _split_result(
                transcriptome_size_matched
            ),
        },
        "survival": {
            "definition": SURVIVAL_DEFINITION,
            "batch_blocked_feature_r_survival": _survival(
                batch_blocked.feature_r, null.feature_r, apparent.feature_r
            ),
            "plate_blocked_imaging_feature_r_survival": _survival(
                imaging_blocked.feature_r, null.feature_r, apparent.feature_r
            ),
            "plate_blocked_transcriptome_feature_r_survival": _survival(
                transcriptome_blocked.feature_r, null.feature_r, apparent.feature_r
            ),
            "batch_blocked_minus_size_matched_random_feature_r": (
                batch_blocked.feature_r - batch_size_matched.feature_r
            ),
            "plate_blocked_imaging_minus_size_matched_random_feature_r": (
                imaging_blocked.feature_r - imaging_size_matched.feature_r
            ),
            "plate_blocked_transcriptome_minus_size_matched_random_feature_r": (
                transcriptome_blocked.feature_r - transcriptome_size_matched.feature_r
            ),
        },
        "model_free_check": {
            "neighbourhood_concordance": concordance,
            "neighbourhood_concordance_permuted_null": concordance_null,
        },
        "examples": examples,
        "per_perturbation_agreement": {
            "perturbation": [perturbation.name for perturbation in perturbations],
            "allele": [perturbation.allele for perturbation in perturbations],
            "apparent_r": [float(value) for value in apparent.per_perturbation_r],
        },
    }


def _survival(blocked: float, null: float, apparent: float) -> float:
    denominator = apparent - null
    if denominator <= 0:
        raise ValueError("the apparent agreement does not exceed the null")
    return (blocked - null) / denominator


def _examples(
    perturbations: tuple[Any, ...], per_perturbation_r: NDArray[np.float64], count: int
) -> dict[str, Any]:
    """The named perturbations at each end of the apparent agreement."""

    def entry(index: int) -> dict[str, Any]:
        perturbation = perturbations[index]
        return {
            "perturbation": perturbation.name,
            "allele": perturbation.allele,
            "gene_symbol": perturbation.gene_symbol,
            "transcriptome_replicates": perturbation.transcriptome_replicates,
            "imaging_replicates": perturbation.imaging_replicates,
            "perturbation_r": float(per_perturbation_r[index]),
        }

    order = sorted(
        range(len(perturbations)),
        key=lambda index: (per_perturbation_r[index], perturbations[index].name),
    )
    highest = [entry(index) for index in order[::-1][:count]]
    lowest = [entry(index) for index in order[:count]]
    return {"most_agreeable": highest, "least_agreeable": lowest}


def _well_values(dataset: Dataset) -> dict[str, Any]:
    """Per-well feature values and their plate and batch labels.

    Every well of a readout takes part, treated and control alike, because
    the plate and batch structure is a property of the measurement rather
    than of the treatment.
    """
    transcriptome_wells = dataset.transcriptome_wells
    imaging_wells = dataset.imaging_wells
    return {
        "transcriptome": np.array([w.values for w in transcriptome_wells], dtype=np.float64),
        "transcriptome_plate": tuple(w.plate for w in transcriptome_wells),
        "imaging": np.array([w.values for w in imaging_wells], dtype=np.float64),
        "imaging_plate": tuple(w.plate for w in imaging_wells),
        "imaging_batch": tuple(dataset.imaging_batch_of_plate[w.plate] for w in imaging_wells),
    }


def project_summary(computed: dict[str, Any]) -> dict[str, Any]:
    """The small committed projection of the computed summary."""
    return {field: computed[field] for field in COMMITTED_FIELDS}


def build_summary_from_cache(
    cache_dir: Path, contract: Contract, *, computed_on: str, software: dict[str, str]
) -> dict[str, Any]:
    dataset = load_cached_dataset(cache_dir, contract)
    return build_summary(dataset, contract, computed_on=computed_on, software=software)


def export_summary(
    contract: Contract,
    cache_dir: Path,
    output_dir: Path,
    committed_path: Path,
    *,
    computed_on: str,
    software: dict[str, str],
) -> dict[str, Any]:
    """Compute the frozen evaluation set and write both artefacts.

    `output_dir` receives the full computed result, including the agreement
    value of every individual perturbation; that is the run artefact and it
    is not part of the committed record. `committed_path` receives the small
    projection, which carries no per-perturbation values and no raw rows.

    Nothing is written until the whole computation has succeeded, so a
    rejected contract leaves no artefact behind.
    """
    computed = build_summary_from_cache(
        cache_dir, contract, computed_on=computed_on, software=software
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "computed-summary.json").write_text(
        json.dumps(computed, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    committed_path.write_text(
        json.dumps(project_summary(computed), allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return computed


def run_lab(
    contract: Contract,
    cache_dir: Path,
    output_dir: Path,
    committed_path: Path,
    *,
    computed_on: str,
    software: dict[str, str],
    fetch: Fetcher | None = None,
) -> dict[str, Any]:
    """The whole pipeline: fetch what is missing, read the cache, compute.

    This is the entry point the lab's own scripts call and the one the
    known-bad-edit test drives. A contract it cannot honour stops it before
    any artefact is written.
    """
    download_and_cache_snapshot(cache_dir, contract, fetch=fetch)
    return export_summary(
        contract,
        cache_dir,
        output_dir,
        committed_path,
        computed_on=computed_on,
        software=software,
    )
