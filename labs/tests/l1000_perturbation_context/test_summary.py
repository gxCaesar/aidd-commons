from __future__ import annotations

import numpy as np
from aidd_commons.l1000_perturbation_context.data import CellLineDataset, DataAudit, SignatureRecord
from aidd_commons.l1000_perturbation_context.protocol import CELL_LINE_A, CELL_LINE_B
from aidd_commons.l1000_perturbation_context.summary import DIVERGENT_EXAMPLE_COUNT, build_summary

AUDIT = DataAudit(
    input_rows=10,
    retained_rows=8,
    admitted_entity_count=4,
    duplicate_entity_count=1,
    exclusion_counts={"wrong_dose": 2},
)


def signature(pert_id: str, cell_id: str, profile: list[float]) -> SignatureRecord:
    return SignatureRecord(
        pert_id=pert_id,
        pert_iname=pert_id,
        cell_id=cell_id,
        canonical_smiles="c1ccccc1",
        replicate_count=1,
        differential_profile=np.array(profile, dtype=np.float64),
    )


def test_build_summary_reports_matched_null_and_bounded_examples() -> None:
    ids = [f"P{i}" for i in range(1, 8)]
    a = CellLineDataset(
        cell_id=CELL_LINE_A,
        signatures={p: signature(p, CELL_LINE_A, [float(i), 1.0, 2.0]) for i, p in enumerate(ids)},
        audit=AUDIT,
    )
    b = CellLineDataset(
        cell_id=CELL_LINE_B,
        signatures={p: signature(p, CELL_LINE_B, [float(i), 1.0, 2.0]) for i, p in enumerate(ids)},
        audit=AUDIT,
    )
    summary = build_summary({CELL_LINE_A: a, CELL_LINE_B: b}, computed_on="2026-09-12", software={})

    assert summary["protocol_id"] == "lincs-l1000-perturbation-context-v1"
    assert summary["shared_compound_count"] == 7
    assert summary["matched"]["count"] == 7
    assert summary["null_mismatched"]["count"] == 7
    assert summary["rank_sum_comparison"]["matched_count"] == 7
    assert len(summary["examples"]["most_reproducible"]) == DIVERGENT_EXAMPLE_COUNT
    assert len(summary["examples"]["most_divergent"]) == DIVERGENT_EXAMPLE_COUNT
