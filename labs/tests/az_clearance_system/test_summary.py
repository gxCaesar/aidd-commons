from __future__ import annotations

from aidd_commons.az_clearance_system.data import DataAudit, ParentClearanceRecord, SystemDataset
from aidd_commons.az_clearance_system.protocol import SYSTEMS
from aidd_commons.az_clearance_system.summary import build_summary

ASSAY_A, ASSAY_B, ASSAY_C = sorted(SYSTEMS)

EMPTY_AUDIT = DataAudit(
    input_rows=10,
    retained_rows=8,
    parent_count=4,
    duplicate_parent_count=1,
    median_duplicate_range=0.2,
    maximum_duplicate_range=0.2,
    exclusion_counts={"censored_value": 2},
)


def record(assay_id: str, parent_id: str, clearance: float) -> ParentClearanceRecord:
    return ParentClearanceRecord(
        assay_chembl_id=assay_id,
        parent_molecule_chembl_id=parent_id,
        canonical_smiles="c1ccccc1",
        intrinsic_clearance=clearance,
        standard_units="mL.min-1.g-1",
        activity_ids=(1,),
        replicate_count=1,
        value_range=0.0,
    )


def test_build_summary_reports_all_three_pairs_with_bounded_divergent_examples() -> None:
    parents = [f"P{i}" for i in range(1, 8)]
    datasets = {
        assay_id: SystemDataset(
            assay_chembl_id=assay_id,
            records=tuple(record(assay_id, p, float(i + 1)) for i, p in enumerate(parents)),
            audit=EMPTY_AUDIT,
        )
        for assay_id in (ASSAY_A, ASSAY_B, ASSAY_C)
    }

    summary = build_summary(datasets, computed_on="2026-09-12", software={"python": "3.11.15"})

    assert summary["protocol_id"] == "chembl37-az-clearance-system-v1"
    assert set(summary["systems"]) == {ASSAY_A, ASSAY_B, ASSAY_C}
    assert len(summary["pairs"]) == 3
    for pair in summary["pairs"].values():
        assert pair["overlap_count"] == 7
        assert pair["clean_pair_count"] == 7
        assert pair["correlation"]["count"] == 7
        assert len(pair["divergent_examples"]["primary_selective"]) == 3
        assert len(pair["divergent_examples"]["secondary_selective"]) == 3
