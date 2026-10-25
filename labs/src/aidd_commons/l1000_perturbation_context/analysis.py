"""Compare real LINCS L1000 differential signatures across two cell lines.

Pure functions over already-validated `CellLineDataset` records; nothing here
fetches, caches or refits anything. Each comparison is between two 978-gene
differential-expression vectors for the same real compound, not between two
scalars, since a molecular profile is what this topic's own description
names.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import mannwhitneyu, spearmanr

from .data import CellLineDataset
from .protocol import NULL_ROTATION


class AnalysisContractError(ValueError):
    """Raised when an analysis input does not meet its declared shape."""


@dataclass(frozen=True)
class CompoundSignaturePair:
    pert_id: str
    pert_iname: str
    spearman_rho: float


def shared_compounds(a: CellLineDataset, b: CellLineDataset) -> tuple[str, ...]:
    return tuple(sorted(set(a.signatures) & set(b.signatures)))


def matched_pairs(a: CellLineDataset, b: CellLineDataset) -> tuple[CompoundSignaturePair, ...]:
    """The real, compound-matched cross-cell-line comparison: for every
    shared compound, the Spearman correlation between its two real
    differential expression profiles."""
    pairs = []
    for pert_id in shared_compounds(a, b):
        sig_a, sig_b = a.signatures[pert_id], b.signatures[pert_id]
        rho, _ = spearmanr(sig_a.differential_profile, sig_b.differential_profile)
        pairs.append(
            CompoundSignaturePair(
                pert_id=pert_id, pert_iname=sig_a.pert_iname, spearman_rho=float(rho)
            )
        )
    return tuple(pairs)


def null_pairs(a: CellLineDataset, b: CellLineDataset) -> tuple[CompoundSignaturePair, ...]:
    """A deterministic mismatched-compound background: pair each compound's
    cell-A profile with a different, fixed compound's cell-B profile, formed
    by rotating the sorted shared-compound list by `NULL_ROTATION`. No
    random state is used. This is one illustrative mismatch, not a resampled
    null distribution."""
    ids = list(shared_compounds(a, b))
    if len(ids) < 2:
        raise AnalysisContractError("at least two shared compounds are required for a null pairing")
    rotated = ids[NULL_ROTATION:] + ids[:NULL_ROTATION]
    pairs = []
    for pert_id_a, pert_id_b in zip(ids, rotated, strict=True):
        sig_a, sig_b = a.signatures[pert_id_a], b.signatures[pert_id_b]
        rho, _ = spearmanr(sig_a.differential_profile, sig_b.differential_profile)
        pairs.append(
            CompoundSignaturePair(
                pert_id=f"{pert_id_a}~{pert_id_b}",
                pert_iname=f"{sig_a.pert_iname}~{sig_b.pert_iname}",
                spearman_rho=float(rho),
            )
        )
    return tuple(pairs)


@dataclass(frozen=True)
class DistributionSummary:
    count: int
    median: float
    mean: float
    fraction_positive: float


def summarize(pairs: tuple[CompoundSignaturePair, ...]) -> DistributionSummary:
    if not pairs:
        raise AnalysisContractError("at least one pair is required")
    rhos = np.array([p.spearman_rho for p in pairs], dtype=np.float64)
    return DistributionSummary(
        count=len(pairs),
        median=float(np.median(rhos)),
        mean=float(np.mean(rhos)),
        fraction_positive=float(np.mean(rhos > 0)),
    )


@dataclass(frozen=True)
class RankSumComparison:
    matched_count: int
    null_count: int
    u_statistic: float
    p_value: float


def compare_matched_to_null(
    matched: tuple[CompoundSignaturePair, ...], null: tuple[CompoundSignaturePair, ...]
) -> RankSumComparison:
    """A two-sided Mann-Whitney U test between the matched and null rho
    distributions: are matched-compound correlations really drawn from a
    different distribution than the mismatched background, not merely a
    higher point estimate."""
    matched_rhos = [p.spearman_rho for p in matched]
    null_rhos = [p.spearman_rho for p in null]
    statistic, p_value = mannwhitneyu(matched_rhos, null_rhos, alternative="two-sided")
    return RankSumComparison(
        matched_count=len(matched_rhos),
        null_count=len(null_rhos),
        u_statistic=float(statistic),
        p_value=float(p_value),
    )


def most_divergent(
    pairs: tuple[CompoundSignaturePair, ...], *, count: int, favouring: str
) -> tuple[CompoundSignaturePair, ...]:
    """The `count` compounds with the most extreme cross-cell-line Spearman
    rho. `favouring='reproducible'` ranks descending (highest rho);
    `favouring='divergent'` ranks ascending (lowest, most negative rho).
    Exact ties break on the smaller pert_id, for a fully deterministic
    order."""
    if favouring not in ("reproducible", "divergent"):
        raise AnalysisContractError("favouring must be 'reproducible' or 'divergent'")
    if count < 1:
        raise AnalysisContractError("count must be at least 1")
    reverse = favouring == "reproducible"
    ordered = sorted(pairs, key=lambda p: (p.spearman_rho, p.pert_id), reverse=reverse)
    return tuple(ordered[:count])
