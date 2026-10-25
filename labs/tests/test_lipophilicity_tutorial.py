"""Literal protocol checks using constructed data; no real-data training."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

LAB = Path(__file__).parents[1] / "lipophilicity"


@pytest.fixture
def tutorial(monkeypatch):
    script = LAB / "tutorial.py"
    assert script.is_file(), "The notebook's inspectable teaching functions are missing"
    monkeypatch.syspath_prepend(str(LAB))
    spec = importlib.util.spec_from_file_location("lipo_tutorial", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame():
    return pd.DataFrame(
        {
            "CMPD_CHEMBLID": [f"ID{i}" for i in range(10)],
            "canonical": [f"structure{i}" for i in range(10)],
            "scaffold": [f"group{i}" for i in range(10)],
            "exp": np.arange(10, dtype=float),
        }
    )


def test_split_matches_literal_largest_first_reverse_index_tiebreak(tutorial):
    result = tutorial.scaffold_split(frame())
    assert result["train"].tolist() == [9, 8, 7, 6, 5, 4, 3, 2]
    assert result["validation"].tolist() == [1]
    assert result["test"].tolist() == [0]
    changed = frame()
    changed["exp"] = -1000
    assert {k: v.tolist() for k, v in tutorial.scaffold_split(changed).items()} == {
        k: v.tolist() for k, v in result.items()
    }


def test_grouped_split_keeps_empty_scaffolds_and_checks_overlap(tutorial):
    records = frame()
    records.loc[[0, 1], "scaffold"] = ""
    splits = tutorial.scaffold_split(records)
    assert all((0 in indices) == (1 in indices) for indices in splits.values())
    wrong = {"train": np.arange(8), "validation": np.array([8]), "test": np.array([9])}
    records.loc[9, "scaffold"] = records.loc[0, "scaffold"]
    with pytest.raises(ValueError, match="scaffold"):
        tutorial.validate_split(records, wrong)
    wrong["test"] = np.array([8])
    with pytest.raises(ValueError):
        tutorial.validate_split(records, wrong)


def test_load_preserves_fragments_and_refuses_structure_aliases(tutorial, tmp_path):
    path = tmp_path / "tiny.csv"
    path.write_text("CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1,CCO.O\nCHEMBL2,2,c1ccccc1\n")
    loaded = tutorial.load_frame(path)
    assert loaded["canonical"].tolist() == ["CCO.O", "c1ccccc1"]
    assert loaded["scaffold"].tolist() == ["", "c1ccccc1"]
    path.write_text("CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1,CCO\nCHEMBL2,2,OCC\n")
    with pytest.raises(ValueError, match="structure"):
        tutorial.load_frame(path)


def test_features_are_finite_label_free_and_morgan_ignores_chirality(tutorial):
    descriptors, bits, fingerprints = tutorial.molecular_features(["C[C@H](O)F", "C[C@@H](O)F"])
    assert descriptors.shape == (2, 8)
    assert bits.shape == (2, 2048)
    assert len(fingerprints) == 2
    assert np.isfinite(descriptors).all()
    assert set(np.unique(bits)) <= {0, 1}
    np.testing.assert_array_equal(bits[0], bits[1])
    with pytest.raises(ValueError):
        tutorial.molecular_features(["invalid"])


def test_scaling_is_train_only_and_ties_choose_larger_alpha(tutorial):
    model, scores = tutorial.fit_candidates(
        np.array([[0.0], [2.0]]),
        np.array([1.0, 1.0]),
        np.array([[100.0]]),
        np.array([1.0]),
        center=True,
    )
    assert model.named_steps["standardscaler"].mean_.tolist() == [1.0]
    assert model.named_steps["ridge"].alpha == 100
    assert scores["validation_rmse"].tolist() == [0, 0, 0, 0]
    assert model.predict([[200.0]]).tolist() == [1.0]


def test_metrics_have_literal_oracle_and_reject_broadcasting(tutorial):
    assert tutorial.score([1, 3], [2, 1]) == pytest.approx({"rmse": np.sqrt(2.5), "mae": 1.5})
    for y, pred in [([], []), ([1], [np.nan]), ([1, 2], [[1], [2]])]:
        with pytest.raises(ValueError):
            tutorial.score(y, pred)


def test_paired_cluster_interval_keeps_whole_groups_and_reports_unestimable(tutorial):
    # Two groups: A has 2 rows at error 0; B has one row at error 3.
    # Pairwise RMSE difference takes only 0, sqrt(3), 3, so 95% limits are 0 and 3.
    report = tutorial.paired_interval([0, 0, 0], [0, 0, 3], [0, 0, 0], ["A", "A", "B"])
    assert report["difference"] == pytest.approx(np.sqrt(3))
    assert report["ci95"] == [0.0, 3.0]
    assert report["groups"] == 2
    assert report["rows"] == 3
    assert report["resamples"] == 2000
    assert tutorial.paired_interval([0, 0], [1, 1], [0, 0], ["A", "A"])["ci95"] is None
    with pytest.raises(ValueError):
        tutorial.paired_interval([0, 0], [1, 1], [0, 0], ["A"])
