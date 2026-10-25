from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from aidd_commons.l1000_perturbation_context.data import (
    DataContractError,
    load_cached_cell_lines,
)


def test_admission_rule_excludes_every_declared_reason(synthetic_cache: Path) -> None:
    datasets = load_cached_cell_lines(synthetic_cache)
    mcf7 = datasets["MCF7"]

    # MCF7 trt_cp rows: CMPD1 x2, CMPD4 x1, CMPD2(wrong dose) x1,
    # CMPD2(wrong time) x1, CMPD5(no plate vehicle control) x1 = 6 input rows
    assert mcf7.audit.input_rows == 6
    assert mcf7.audit.exclusion_counts == {
        "no_plate_vehicle_control": 1,
        "wrong_dose": 1,
        "wrong_time": 1,
    }
    # retained: CMPD1 x2 + CMPD4 x1 = 3
    assert mcf7.audit.retained_rows == 3
    assert mcf7.audit.admitted_entity_count == 2
    assert mcf7.audit.duplicate_entity_count == 1
    assert set(mcf7.signatures) == {"CMPD1", "CMPD4"}
    assert mcf7.signatures["CMPD1"].replicate_count == 2


def test_admission_rule_excludes_invalid_structure(synthetic_cache: Path) -> None:
    datasets = load_cached_cell_lines(synthetic_cache)
    pc3 = datasets["PC3"]
    # PC3 trt_cp rows: CMPD1, CMPD4, CMPD3(restricted structure) = 3 input rows
    assert pc3.audit.input_rows == 3
    assert pc3.audit.exclusion_counts == {"missing_structure": 1}
    assert pc3.audit.retained_rows == 2
    assert set(pc3.signatures) == {"CMPD1", "CMPD4"}


def test_differential_profile_subtracts_the_plate_matched_vehicle_baseline(
    synthetic_cache: Path,
) -> None:
    datasets = load_cached_cell_lines(synthetic_cache)
    mcf7 = datasets["MCF7"]
    # Vehicle wells were fixed at [5.0, 5.0, 5.0]; CMPD1's treated wells were
    # set to 5.0 + [1.0, 0.5, -0.5], so the differential recovers that offset
    # exactly regardless of the vehicle wells' own raw level.
    np.testing.assert_allclose(
        mcf7.signatures["CMPD1"].differential_profile, [1.0, 0.5, -0.5], atol=1e-6
    )


def test_load_cached_cell_lines_rejects_a_wrong_cached_size(synthetic_cache: Path) -> None:
    filename = "GSE70138_Broad_LINCS_pert_info_2017-03-06.txt.gz"
    (synthetic_cache / filename).write_bytes((synthetic_cache / filename).read_bytes() + b"\x00")
    with pytest.raises(DataContractError, match="does not match protocol"):
        load_cached_cell_lines(synthetic_cache)


def test_load_cached_cell_lines_rejects_a_missing_file(
    synthetic_cache: Path, tmp_path: Path
) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(DataContractError, match="is not present"):
        load_cached_cell_lines(empty_dir)
