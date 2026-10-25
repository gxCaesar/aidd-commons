"""Compare CYP3A4 and CYP2D6 potency for parents measured against both.

Pure functions over already-validated `TargetDataset` records; nothing here
fetches, caches or refits anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .data import ParentActivityRecord, TargetDataset


class AnalysisContractError(ValueError):
    """Raised when an analysis input does not meet its declared shape."""


@dataclass(frozen=True)
class OverlapRecord:
    parent_molecule_chembl_id: str
    primary_pchembl: float
    secondary_pchembl: float
    shares_a_document: bool
    is_clean_single_pair: bool


def overlap_records(primary: TargetDataset, secondary: TargetDataset) -> tuple[OverlapRecord, ...]:
    """Every parent with an admitted record against both targets, in stable
    sorted order. A record is a 'clean single pair' when each side has exactly
    one contributing activity and both come from the same document, which
    avoids any cross-study median for that parent."""
    by_primary: dict[str, ParentActivityRecord] = {
        r.parent_molecule_chembl_id: r for r in primary.records
    }
    by_secondary: dict[str, ParentActivityRecord] = {
        r.parent_molecule_chembl_id: r for r in secondary.records
    }
    shared_parents = sorted(set(by_primary) & set(by_secondary))
    records = []
    for parent_id in shared_parents:
        left = by_primary[parent_id]
        right = by_secondary[parent_id]
        shares_document = bool(set(left.document_chembl_ids) & set(right.document_chembl_ids))
        clean = left.replicate_count == 1 and right.replicate_count == 1 and shares_document
        records.append(
            OverlapRecord(
                parent_molecule_chembl_id=parent_id,
                primary_pchembl=left.target_pchembl,
                secondary_pchembl=right.target_pchembl,
                shares_a_document=shares_document,
                is_clean_single_pair=clean,
            )
        )
    return tuple(records)


def _to_arrays(records: tuple[OverlapRecord, ...]) -> tuple[NDArray[Any], NDArray[Any]]:
    if not records:
        raise AnalysisContractError("at least one overlap record is required")
    x = np.array([r.primary_pchembl for r in records], dtype=np.float64)
    y = np.array([r.secondary_pchembl for r in records], dtype=np.float64)
    return x, y


@dataclass(frozen=True)
class CorrelationSummary:
    count: int
    pearson_r: float
    spearman_rho: float
    spearman_p_value: float


def correlation_summary(records: tuple[OverlapRecord, ...]) -> CorrelationSummary:
    """Pearson and Spearman correlation between the two targets' pChEMBL values,
    over exactly the given records (the caller decides full overlap vs. the
    clean same-document subset; this function does not filter)."""
    from scipy.stats import spearmanr

    x, y = _to_arrays(records)
    if len(records) < 3:
        raise AnalysisContractError("fewer than 3 records is too few to correlate")
    pearson = float(np.corrcoef(x, y)[0, 1])
    rho, p_value = spearmanr(x, y)
    return CorrelationSummary(
        count=len(records),
        pearson_r=pearson,
        spearman_rho=float(rho),
        spearman_p_value=float(p_value),
    )


@dataclass(frozen=True)
class DivergentExample:
    parent_molecule_chembl_id: str
    primary_pchembl: float
    secondary_pchembl: float
    difference: float


def most_divergent(
    records: tuple[OverlapRecord, ...], *, count: int, favouring: str
) -> tuple[DivergentExample, ...]:
    """The `count` records with the most extreme (primary - secondary) pChEMBL
    difference. `favouring='primary'` ranks descending (primary much higher);
    `favouring='secondary'` ranks ascending (secondary much higher). Exact ties
    break on the smaller parent ID, for a fully deterministic order."""
    if favouring not in ("primary", "secondary"):
        raise AnalysisContractError("favouring must be 'primary' or 'secondary'")
    if count < 1:
        raise AnalysisContractError("count must be at least 1")
    reverse = favouring == "primary"
    ordered = sorted(
        records,
        key=lambda r: (r.primary_pchembl - r.secondary_pchembl, r.parent_molecule_chembl_id),
        reverse=reverse,
    )
    return tuple(
        DivergentExample(
            parent_molecule_chembl_id=r.parent_molecule_chembl_id,
            primary_pchembl=r.primary_pchembl,
            secondary_pchembl=r.secondary_pchembl,
            difference=r.primary_pchembl - r.secondary_pchembl,
        )
        for r in ordered[:count]
    )
