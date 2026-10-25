"""The real cached assay cohort is partitioned and propagated as declared."""

from __future__ import annotations

from pathlib import Path

import pytest
from aidd_commons.pkpd_translation_audit.analysis import (
    analyse,
    check_analysis,
    load_from_cache,
)
from aidd_commons.pkpd_translation_audit.protocol import HUMAN, RAT, expected_protocol

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / ".cache/az_clearance_system"


@pytest.mark.skipif(not CACHE.is_dir(), reason="the AZ clearance ChEMBL snapshot is not cached")
def test_real_paired_cohort_and_uncertainty_stages() -> None:
    protocol = expected_protocol()
    datasets = load_from_cache(CACHE, protocol["source"])
    result = analyse(datasets, protocol)
    human = {r.parent_molecule_chembl_id for r in datasets[HUMAN].records}
    rat = {r.parent_molecule_chembl_id for r in datasets[RAT].records}
    assert {r.parent_molecule_chembl_id for r in result.modelled} == human & rat
    assert result.cohort["modelled_parents"] == 106
    assert result.cohort["not_modelled_parents"] == 1014
    assert result.cohort["paired_with_at_least_threefold_difference"] == 37
    assert result.uncarried_reasons["human_hepatocyte_without_rat_hepatocyte"] == 182
    assert result.uncarried_reasons["rat_hepatocyte_without_human_hepatocyte"] == 486
    assert not check_analysis(result)
    assert all(
        row.concentration_0h_umol_l >= row.concentration_12h_umol_l >= row.concentration_24h_umol_l
        for row in result.modelled
    )
    assert all(
        all(
            a <= b + 1e-12
            for a, b in zip(
                row.uncertainty_stage_widths, row.uncertainty_stage_widths[1:], strict=False
            )
        )
        and row.uncertainty_stage_widths[-1] > row.uncertainty_stage_widths[0]
        for row in result.modelled
    )


@pytest.mark.skipif(not CACHE.is_dir(), reason="the AZ clearance ChEMBL snapshot is not cached")
def test_species_factor_leaves_out_the_target_parent() -> None:
    protocol = expected_protocol()
    datasets = load_from_cache(CACHE, protocol["source"])
    result = analyse(datasets, protocol)
    row = next(r for r in result.modelled if r.parent_molecule_chembl_id == "CHEMBL361546")
    assert row.observed_human_to_rat_ratio > 9
    assert row.translation_factor < 1
    assert row.human_hepatocyte_clearance == 134.9
    assert row.rat_hepatocyte_clearance == 14.79
