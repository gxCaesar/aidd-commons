from __future__ import annotations

import pytest
from aidd_commons.cyp_assay_system.analysis import (
    AnalysisContractError,
    correlation_summary,
    most_divergent,
    overlap_records,
)
from aidd_commons.cyp_assay_system.data import DataAudit, ParentActivityRecord, TargetDataset

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
    target_id: str,
    pchembl: float,
    *,
    document_ids: tuple[str, ...] = ("DOC_1",),
    assay_ids: tuple[str, ...] = ("ASSAY_1",),
    replicate_count: int = 1,
) -> ParentActivityRecord:
    return ParentActivityRecord(
        target_chembl_id=target_id,
        parent_molecule_chembl_id=parent_id,
        canonical_smiles="c1ccccc1",
        target_pchembl=pchembl,
        activity_ids=(1,),
        assay_chembl_ids=assay_ids,
        document_chembl_ids=document_ids,
        replicate_count=replicate_count,
        pchembl_range=0.0,
    )


def dataset(target_id: str, records: tuple[ParentActivityRecord, ...]) -> TargetDataset:
    return TargetDataset(target_chembl_id=target_id, records=records, audit=EMPTY_AUDIT)


def test_overlap_is_exactly_the_shared_parent_set_and_flags_clean_pairs() -> None:
    primary = dataset(
        "T_PRIMARY",
        (
            record("P1", "T_PRIMARY", 7.0, document_ids=("DOC_A",)),
            record("P2", "T_PRIMARY", 6.0, document_ids=("DOC_B",), replicate_count=2),
            record("P3", "T_PRIMARY", 5.0, document_ids=("DOC_C",)),
        ),
    )
    secondary = dataset(
        "T_SECONDARY",
        (
            record("P1", "T_SECONDARY", 4.5, document_ids=("DOC_A",)),
            record("P2", "T_SECONDARY", 4.0, document_ids=("DOC_B",)),
            record("P4", "T_SECONDARY", 3.0, document_ids=("DOC_D",)),
        ),
    )

    overlap = overlap_records(primary, secondary)
    ids = {r.parent_molecule_chembl_id for r in overlap}
    assert ids == {"P1", "P2"}

    by_id = {r.parent_molecule_chembl_id: r for r in overlap}
    assert by_id["P1"].shares_a_document is True
    assert by_id["P1"].is_clean_single_pair is True
    # P2's primary side has replicate_count=2, so it cannot be a clean single pair
    # even though the two sides share a document.
    assert by_id["P2"].shares_a_document is True
    assert by_id["P2"].is_clean_single_pair is False


def test_overlap_marks_pairs_from_different_documents_as_not_clean() -> None:
    primary = dataset("T_PRIMARY", (record("P1", "T_PRIMARY", 7.0, document_ids=("DOC_A",)),))
    secondary = dataset(
        "T_SECONDARY", (record("P1", "T_SECONDARY", 4.5, document_ids=("DOC_OTHER",)),)
    )
    overlap = overlap_records(primary, secondary)
    assert len(overlap) == 1
    assert overlap[0].shares_a_document is False
    assert overlap[0].is_clean_single_pair is False


def test_correlation_summary_requires_at_least_three_records() -> None:
    primary = dataset(
        "T_PRIMARY",
        (record("P1", "T_PRIMARY", 7.0), record("P2", "T_PRIMARY", 6.0)),
    )
    secondary = dataset(
        "T_SECONDARY",
        (record("P1", "T_SECONDARY", 4.5), record("P2", "T_SECONDARY", 4.0)),
    )
    overlap = overlap_records(primary, secondary)
    with pytest.raises(AnalysisContractError, match="fewer than 3"):
        correlation_summary(overlap)


def test_correlation_summary_recovers_a_known_perfect_relationship() -> None:
    primary = dataset(
        "T_PRIMARY",
        tuple(record(f"P{i}", "T_PRIMARY", float(i)) for i in range(1, 6)),
    )
    secondary = dataset(
        "T_SECONDARY",
        tuple(record(f"P{i}", "T_SECONDARY", float(i) * 2.0) for i in range(1, 6)),
    )
    overlap = overlap_records(primary, secondary)
    summary = correlation_summary(overlap)
    assert summary.count == 5
    assert summary.pearson_r == pytest.approx(1.0)
    assert summary.spearman_rho == pytest.approx(1.0)


def test_correlation_summary_rejects_an_empty_record_set() -> None:
    with pytest.raises(AnalysisContractError, match="at least one"):
        correlation_summary(())


def test_most_divergent_orders_deterministically_in_both_directions() -> None:
    primary = dataset(
        "T_PRIMARY",
        (
            record("P1", "T_PRIMARY", 7.0),
            record("P2", "T_PRIMARY", 5.0),
            record("P3", "T_PRIMARY", 5.0),
            record("P4", "T_PRIMARY", 3.0),
        ),
    )
    secondary = dataset(
        "T_SECONDARY",
        (
            record("P1", "T_SECONDARY", 4.0),
            record("P2", "T_SECONDARY", 5.0),
            record("P3", "T_SECONDARY", 4.0),
            record("P4", "T_SECONDARY", 7.0),
        ),
    )
    overlap = overlap_records(primary, secondary)

    primary_selective = most_divergent(overlap, count=2, favouring="primary")
    assert [r.parent_molecule_chembl_id for r in primary_selective] == ["P1", "P3"]
    assert primary_selective[0].difference == pytest.approx(3.0)

    secondary_selective = most_divergent(overlap, count=2, favouring="secondary")
    assert [r.parent_molecule_chembl_id for r in secondary_selective] == ["P4", "P2"]


def test_most_divergent_rejects_bad_arguments() -> None:
    primary = dataset("T_PRIMARY", (record("P1", "T_PRIMARY", 7.0),))
    secondary = dataset("T_SECONDARY", (record("P1", "T_SECONDARY", 4.0),))
    overlap = overlap_records(primary, secondary)
    with pytest.raises(AnalysisContractError, match="favouring"):
        most_divergent(overlap, count=1, favouring="both")
    with pytest.raises(AnalysisContractError, match="count must be at least 1"):
        most_divergent(overlap, count=0, favouring="primary")
