"""Independent-unit and metric oracles on constructed records."""

import pytest
from aidd_commons.skempi_affinity.analysis import (
    AnalysisContractError,
    complex_split,
    evaluate,
    row_split_leakage,
)
from aidd_commons.skempi_affinity.data import Record


def record(index, complex_id, wt, mutant, group="g"):
    return Record(index, complex_id, "AB/AG", group, mutant, wt, 29)


def test_complex_split_keeps_replicates_together():
    rows = tuple(record(i, f"complex-{i // 5}", 1e-8, 2e-8) for i in range(50))
    split = complex_split(rows)
    assert len({r.complex_id for r in split.test}) == 2
    assert not {r.complex_id for r in split.test} & {r.complex_id for r in split.train}
    assert row_split_leakage(rows)["leaked_test_rows"] > 0


def test_observed_mutant_and_group_baseline_have_hand_checkable_mae():
    from aidd_commons.skempi_affinity.analysis import Split

    split = Split(
        (record(0, "train-a", 1e-8, 1e-8), record(1, "train-b", 1e-6, 1e-6)),
        (record(2, "test", 1e-7, 1e-8),),
    )
    outcome = evaluate(split)
    assert outcome["group_only"]["row_mae_log10_m"] == pytest.approx(0)
    assert outcome["observed_mutant"]["row_mae_log10_m"] == pytest.approx(1)
    assert outcome["test_complexes"] == 1


def test_overlap_is_rejected_before_scoring():
    from aidd_commons.skempi_affinity.analysis import Split

    with pytest.raises(AnalysisContractError, match="both partitions"):
        evaluate(Split((record(0, "same", 1e-8, 2e-8),),
                       (record(1, "same", 1e-8, 2e-8),)))
