from __future__ import annotations

from aidd_commons.cyp_assay_system.data import DataAudit, ParentActivityRecord, TargetDataset
from aidd_commons.cyp_assay_system.protocol import TARGETS
from aidd_commons.cyp_assay_system.summary import DIVERGENT_EXAMPLE_COUNT, build_summary

PRIMARY, SECONDARY = TARGETS

EMPTY_AUDIT = DataAudit(
    input_rows=10,
    retained_rows=8,
    parent_count=4,
    duplicate_parent_count=1,
    median_duplicate_range=0.2,
    maximum_duplicate_range=0.2,
    exclusion_counts={"wrong_endpoint": 2},
)


def record(target_id: str, parent_id: str, pchembl: float) -> ParentActivityRecord:
    return ParentActivityRecord(
        target_chembl_id=target_id,
        parent_molecule_chembl_id=parent_id,
        canonical_smiles="c1ccccc1",
        target_pchembl=pchembl,
        activity_ids=(1,),
        assay_chembl_ids=("ASSAY_1",),
        document_chembl_ids=("DOC_1",),
        replicate_count=1,
        pchembl_range=0.0,
    )


def test_build_summary_reports_counts_correlation_and_bounded_divergent_examples() -> None:
    primary_records = tuple(record(PRIMARY, f"P{i}", float(i)) for i in range(1, 8))
    secondary_records = tuple(record(SECONDARY, f"P{i}", float(9 - i)) for i in range(1, 8))
    datasets = {
        PRIMARY: TargetDataset(
            target_chembl_id=PRIMARY, records=primary_records, audit=EMPTY_AUDIT
        ),
        SECONDARY: TargetDataset(
            target_chembl_id=SECONDARY, records=secondary_records, audit=EMPTY_AUDIT
        ),
    }

    summary = build_summary(datasets, computed_on="2026-09-12", software={"python": "3.11.15"})

    assert summary["protocol_id"] == "chembl37-cyp-assay-system-v1"
    assert summary["targets"][PRIMARY]["admitted_parents"] == 7
    assert summary["overlap"]["full_count"] == 7
    assert summary["overlap"]["clean_pair_count"] == 7
    assert summary["correlation"]["full"]["count"] == 7
    assert summary["correlation"]["full"]["spearman_rho"] == -1.0
    assert len(summary["divergent_examples"]["primary_selective"]) == DIVERGENT_EXAMPLE_COUNT
    assert len(summary["divergent_examples"]["secondary_selective"]) == DIVERGENT_EXAMPLE_COUNT
    # Perfectly anti-correlated data: the most primary-selective example is the
    # complement of the most secondary-selective example.
    top_primary = summary["divergent_examples"]["primary_selective"][0]
    top_secondary = summary["divergent_examples"]["secondary_selective"][0]
    assert top_primary["parent_molecule_chembl_id"] != top_secondary["parent_molecule_chembl_id"]
