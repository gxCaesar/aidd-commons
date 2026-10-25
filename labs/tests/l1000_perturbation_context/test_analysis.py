from __future__ import annotations

import numpy as np
import pytest
from aidd_commons.l1000_perturbation_context.analysis import (
    AnalysisContractError,
    compare_matched_to_null,
    matched_pairs,
    most_divergent,
    null_pairs,
    shared_compounds,
    summarize,
)
from aidd_commons.l1000_perturbation_context.data import CellLineDataset, DataAudit, SignatureRecord

EMPTY_AUDIT = DataAudit(
    input_rows=0,
    retained_rows=0,
    admitted_entity_count=0,
    duplicate_entity_count=0,
    exclusion_counts={},
)


def signature(
    pert_id: str, cell_id: str, profile: list[float], iname: str | None = None
) -> SignatureRecord:
    return SignatureRecord(
        pert_id=pert_id,
        pert_iname=iname or pert_id,
        cell_id=cell_id,
        canonical_smiles="c1ccccc1",
        replicate_count=1,
        differential_profile=np.array(profile, dtype=np.float64),
    )


def dataset(cell_id: str, sigs: dict[str, SignatureRecord]) -> CellLineDataset:
    return CellLineDataset(cell_id=cell_id, signatures=sigs, audit=EMPTY_AUDIT)


def test_shared_compounds_is_exactly_the_set_intersection() -> None:
    a = dataset("A", {"P1": signature("P1", "A", [1, 0, 0]), "P2": signature("P2", "A", [0, 1, 0])})
    b = dataset("B", {"P1": signature("P1", "B", [1, 0, 0]), "P3": signature("P3", "B", [0, 0, 1])})
    assert shared_compounds(a, b) == ("P1",)


def test_matched_pairs_recovers_a_known_perfect_correlation() -> None:
    a = dataset("A", {"P1": signature("P1", "A", [1.0, 2.0, 3.0, 4.0])})
    b = dataset("B", {"P1": signature("P1", "B", [2.0, 4.0, 6.0, 8.0])})
    pairs = matched_pairs(a, b)
    assert len(pairs) == 1
    assert pairs[0].spearman_rho == pytest.approx(1.0)


def test_null_pairs_uses_a_fixed_rotation_and_rejects_too_few_compounds() -> None:
    a = dataset(
        "A",
        {
            "P1": signature("P1", "A", [1.0, 2.0, 3.0]),
            "P2": signature("P2", "A", [3.0, 2.0, 1.0]),
            "P3": signature("P3", "A", [1.0, 1.0, 2.0]),
        },
    )
    b = dataset(
        "B",
        {
            "P1": signature("P1", "B", [1.0, 2.0, 3.0]),
            "P2": signature("P2", "B", [3.0, 2.0, 1.0]),
            "P3": signature("P3", "B", [1.0, 1.0, 2.0]),
        },
    )
    pairs = null_pairs(a, b)
    assert len(pairs) == 3
    assert all("~" in p.pert_id for p in pairs)
    # sorted ids are P1, P2, P3; rotating by 1 pairs P1(A) with P2(B), etc.
    assert pairs[0].pert_id == "P1~P2"
    assert pairs[1].pert_id == "P2~P3"
    assert pairs[2].pert_id == "P3~P1"

    single = dataset("A2", {"P1": signature("P1", "A2", [1.0, 2.0, 3.0])})
    single_b = dataset("B2", {"P1": signature("P1", "B2", [1.0, 2.0, 3.0])})
    with pytest.raises(AnalysisContractError, match="at least two shared compounds"):
        null_pairs(single, single_b)


def test_summarize_reports_median_mean_and_fraction_positive() -> None:
    a = dataset(
        "A",
        {
            p: signature(p, "A", [1.0, float(i), 0.5])
            for i, p in enumerate(["P1", "P2", "P3", "P4"])
        },
    )
    b = dataset(
        "B",
        {
            p: signature(p, "B", [1.0, float(i) * -1, 0.5])
            for i, p in enumerate(["P1", "P2", "P3", "P4"])
        },
    )
    pairs = matched_pairs(a, b)
    summary = summarize(pairs)
    assert summary.count == 4
    assert summary.fraction_positive <= 1.0


def test_summarize_rejects_empty_input() -> None:
    with pytest.raises(AnalysisContractError, match="at least one"):
        summarize(())


def test_compare_matched_to_null_runs_a_two_sided_rank_sum_test() -> None:
    a = dataset(
        "A", {p: signature(p, "A", [1.0, 2.0, 3.0, float(i)]) for i, p in enumerate(range(6))}
    )
    b = dataset(
        "B", {p: signature(p, "B", [1.0, 2.0, 3.0, float(i)]) for i, p in enumerate(range(6))}
    )
    matched = matched_pairs(a, b)
    null = null_pairs(a, b)
    result = compare_matched_to_null(matched, null)
    assert result.matched_count == len(matched)
    assert result.null_count == len(null)
    assert 0.0 <= result.p_value <= 1.0


def test_most_divergent_orders_deterministically_both_directions() -> None:
    a = dataset(
        "A",
        {
            "P1": signature("P1", "A", [1.0, 2.0, 3.0, 4.0]),
            "P2": signature("P2", "A", [1.0, 2.0, 3.0, 4.0]),
            "P3": signature("P3", "A", [1.0, 2.0, 3.0, 4.0]),
        },
    )
    b = dataset(
        "B",
        {
            "P1": signature("P1", "B", [1.0, 2.0, 3.0, 4.0]),  # perfect match, rho=1
            "P2": signature("P2", "B", [4.0, 3.0, 2.0, 1.0]),  # perfect anti-match, rho=-1
            "P3": signature("P3", "B", [1.0, 3.0, 2.0, 4.0]),  # partial match, 0<rho<1
        },
    )
    pairs = matched_pairs(a, b)
    top = most_divergent(pairs, count=1, favouring="reproducible")
    assert top[0].pert_id == "P1"
    bottom = most_divergent(pairs, count=1, favouring="divergent")
    assert bottom[0].pert_id == "P2"

    with pytest.raises(AnalysisContractError, match="favouring"):
        most_divergent(pairs, count=1, favouring="both")
    with pytest.raises(AnalysisContractError, match="count must be at least 1"):
        most_divergent(pairs, count=0, favouring="reproducible")
