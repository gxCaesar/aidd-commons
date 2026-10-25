"""Compare intrinsic clearance across three real assay systems for the same
real compounds.

Pure functions over already-validated `SystemDataset` records; nothing here
fetches, caches or refits anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .data import ParentClearanceRecord, SystemDataset
from .protocol import SYSTEMS

# (system A, system B, what varies between them, holding the other fixed)
SYSTEM_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("CHEMBL3301372", "CHEMBL3301371", "species (human vs. rat), matrix fixed at hepatocyte"),
    ("CHEMBL3301370", "CHEMBL3301372", "matrix (microsome vs. hepatocyte), species fixed at human"),
    ("CHEMBL3301370", "CHEMBL3301371", "species and matrix both differ"),
)


class AnalysisContractError(ValueError):
    """Raised when an analysis input does not meet its declared shape."""


@dataclass(frozen=True)
class OverlapRecord:
    parent_molecule_chembl_id: str
    primary_clearance: float
    secondary_clearance: float
    is_clean_single_pair: bool


def overlap_records(primary: SystemDataset, secondary: SystemDataset) -> tuple[OverlapRecord, ...]:
    """Every parent with an admitted record against both assays, in stable
    sorted order. A record is a 'clean single pair' when each side has exactly
    one admitted activity for that parent, so neither value is itself a
    within-assay median."""
    by_primary: dict[str, ParentClearanceRecord] = {
        r.parent_molecule_chembl_id: r for r in primary.records
    }
    by_secondary: dict[str, ParentClearanceRecord] = {
        r.parent_molecule_chembl_id: r for r in secondary.records
    }
    shared_parents = sorted(set(by_primary) & set(by_secondary))
    records = []
    for parent_id in shared_parents:
        left = by_primary[parent_id]
        right = by_secondary[parent_id]
        records.append(
            OverlapRecord(
                parent_molecule_chembl_id=parent_id,
                primary_clearance=left.intrinsic_clearance,
                secondary_clearance=right.intrinsic_clearance,
                is_clean_single_pair=left.replicate_count == 1 and right.replicate_count == 1,
            )
        )
    return tuple(records)


def _to_arrays(records: tuple[OverlapRecord, ...]) -> tuple[NDArray[Any], NDArray[Any]]:
    if not records:
        raise AnalysisContractError("at least one overlap record is required")
    x = np.array([r.primary_clearance for r in records], dtype=np.float64)
    y = np.array([r.secondary_clearance for r in records], dtype=np.float64)
    return x, y


@dataclass(frozen=True)
class CorrelationSummary:
    count: int
    pearson_r: float
    spearman_rho: float
    spearman_p_value: float


def correlation_summary(records: tuple[OverlapRecord, ...]) -> CorrelationSummary:
    """Pearson and Spearman correlation between the two systems' intrinsic
    clearance values, over exactly the given records."""
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
    primary_clearance: float
    secondary_clearance: float
    log_ratio: float


def most_divergent(
    records: tuple[OverlapRecord, ...], *, count: int, favouring: str
) -> tuple[DivergentExample, ...]:
    """The `count` records with the most extreme log10(primary/secondary)
    clearance ratio. `favouring='primary'` ranks descending (primary much
    higher); `favouring='secondary'` ranks ascending (secondary much higher).
    Exact ties break on the smaller parent ID, for a fully deterministic
    order."""
    if favouring not in ("primary", "secondary"):
        raise AnalysisContractError("favouring must be 'primary' or 'secondary'")
    if count < 1:
        raise AnalysisContractError("count must be at least 1")
    reverse = favouring == "primary"

    def log_ratio(record: OverlapRecord) -> float:
        return float(np.log10(record.primary_clearance / record.secondary_clearance))

    ordered = sorted(
        records,
        key=lambda r: (log_ratio(r), r.parent_molecule_chembl_id),
        reverse=reverse,
    )
    return tuple(
        DivergentExample(
            parent_molecule_chembl_id=r.parent_molecule_chembl_id,
            primary_clearance=r.primary_clearance,
            secondary_clearance=r.secondary_clearance,
            log_ratio=log_ratio(r),
        )
        for r in ordered[:count]
    )


def system_label(assay_chembl_id: str) -> str:
    return SYSTEMS[assay_chembl_id][0]
