from __future__ import annotations

import pytest
from aidd_commons.az_clearance_system.analysis import (
    AnalysisContractError,
    correlation_summary,
    most_divergent,
    overlap_records,
)
from aidd_commons.az_clearance_system.data import DataAudit, ParentClearanceRecord, SystemDataset

EMPTY_AUDIT = DataAudit(
    input_rows=0,
    retained_rows=0,
    parent_count=0,
    duplicate_parent_count=0,
    median_duplicate_range=None,
    maximum_duplicate_range=None,
    exclusion_counts={},
)


def record(
    parent_id: str,
    assay_id: str,
    clearance: float,
    *,
    replicate_count: int = 1,
) -> ParentClearanceRecord:
    return ParentClearanceRecord(
        assay_chembl_id=assay_id,
        parent_molecule_chembl_id=parent_id,
        canonical_smiles="c1ccccc1",
        intrinsic_clearance=clearance,
        standard_units="mL.min-1.g-1",
        activity_ids=(1,),
        replicate_count=replicate_count,
        value_range=0.0,
    )


def dataset(assay_id: str, records: tuple[ParentClearanceRecord, ...]) -> SystemDataset:
    return SystemDataset(assay_chembl_id=assay_id, records=records, audit=EMPTY_AUDIT)


def test_overlap_is_exactly_the_shared_parent_set_and_flags_clean_pairs() -> None:
    primary = dataset(
        "T_A",
        (
            record("P1", "T_A", 20.0),
            record("P2", "T_A", 15.0, replicate_count=2),
            record("P3", "T_A", 5.0),
        ),
    )
    secondary = dataset(
        "T_B",
        (
            record("P1", "T_B", 10.0),
            record("P2", "T_B", 8.0),
            record("P4", "T_B", 3.0),
        ),
    )

    overlap = overlap_records(primary, secondary)
    ids = {r.parent_molecule_chembl_id for r in overlap}
    assert ids == {"P1", "P2"}

    by_id = {r.parent_molecule_chembl_id: r for r in overlap}
    assert by_id["P1"].is_clean_single_pair is True
    # P2's primary side has replicate_count=2, so it cannot be a clean single pair.
    assert by_id["P2"].is_clean_single_pair is False


def test_correlation_summary_requires_at_least_three_records() -> None:
    primary = dataset("T_A", (record("P1", "T_A", 20.0), record("P2", "T_A", 15.0)))
    secondary = dataset("T_B", (record("P1", "T_B", 10.0), record("P2", "T_B", 8.0)))
    overlap = overlap_records(primary, secondary)
    with pytest.raises(AnalysisContractError, match="fewer than 3"):
        correlation_summary(overlap)


def test_correlation_summary_recovers_a_known_perfect_relationship() -> None:
    primary = dataset("T_A", tuple(record(f"P{i}", "T_A", float(i)) for i in range(1, 6)))
    secondary = dataset("T_B", tuple(record(f"P{i}", "T_B", float(i) * 2.0) for i in range(1, 6)))
    overlap = overlap_records(primary, secondary)
    summary = correlation_summary(overlap)
    assert summary.count == 5
    assert summary.pearson_r == pytest.approx(1.0)
    assert summary.spearman_rho == pytest.approx(1.0)


def test_correlation_summary_rejects_an_empty_record_set() -> None:
    with pytest.raises(AnalysisContractError, match="at least one"):
        correlation_summary(())


def test_most_divergent_orders_by_log_ratio_deterministically_both_directions() -> None:
    primary = dataset(
        "T_A",
        (
            record("P1", "T_A", 100.0),
            record("P2", "T_A", 10.0),
            record("P3", "T_A", 10.0),
            record("P4", "T_A", 1.0),
        ),
    )
    secondary = dataset(
        "T_B",
        (
            record("P1", "T_B", 10.0),
            record("P2", "T_B", 10.0),
            record("P3", "T_B", 1.0),
            record("P4", "T_B", 100.0),
        ),
    )
    overlap = overlap_records(primary, secondary)

    primary_selective = most_divergent(overlap, count=2, favouring="primary")
    assert [r.parent_molecule_chembl_id for r in primary_selective] == ["P3", "P1"]
    assert primary_selective[0].log_ratio == pytest.approx(1.0)

    secondary_selective = most_divergent(overlap, count=2, favouring="secondary")
    assert [r.parent_molecule_chembl_id for r in secondary_selective] == ["P4", "P2"]


def test_most_divergent_rejects_bad_arguments() -> None:
    primary = dataset("T_A", (record("P1", "T_A", 10.0),))
    secondary = dataset("T_B", (record("P1", "T_B", 5.0),))
    overlap = overlap_records(primary, secondary)
    with pytest.raises(AnalysisContractError, match="favouring"):
        most_divergent(overlap, count=1, favouring="both")
    with pytest.raises(AnalysisContractError, match="count must be at least 1"):
        most_divergent(overlap, count=0, favouring="primary")
