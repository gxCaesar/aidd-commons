"""Data-intake checks; these tests never fit a model or assign a split."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "lipophilicity" / "inspect_data.py"


def inspector():
    assert SCRIPT.is_file(), "The read-only lipophilicity inspector is not implemented"
    spec = importlib.util.spec_from_file_location("lipophilicity_intake", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_counts_structural_aliases_without_deduplicating_or_merging_labels(tmp_path):
    module = inspector()
    source = tmp_path / "example.csv"
    source.write_text(
        "CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1.0,CCO\nCHEMBL2,2.0,OCC\nCHEMBL3,3.0,c1ccccc1\n"
    )
    report = module.inspect(source)
    assert report["rows"] == 3
    assert report["unique_ids"] == 3
    assert report["unique_canonical_isomeric_smiles"] == 2
    assert report["repeated_structure_groups"] == 1
    assert report["repeated_structure_extra_rows"] == 1
    assert report["structure_groups_with_different_labels"] == 1
    assert report["nonempty_scaffold_groups"] == 1
    assert report["acyclic_rows"] == 2
    assert report["target_range"] == [1.0, 3.0]
    assert len(source.read_text().splitlines()) == 4


@pytest.mark.parametrize(
    "body",
    [
        "id,exp,smiles\nCHEMBL1,1,CC\n",
        "CMPD_CHEMBLID,exp,smiles\n",
        "CMPD_CHEMBLID,exp,smiles\nCHEMBL1,nan,CC\n",
        "CMPD_CHEMBLID,exp,smiles\nCHEMBL1,inf,CC\n",
        "CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1,not-a-molecule\n",
        "CMPD_CHEMBLID,exp,smiles\n,1,CC\n",
        "CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1,\n",
        "CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1,CC\nCHEMBL1,2,CCC\n",
        "CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1,CC,unexpected\n",
    ],
)
def test_malformed_inputs_fail_without_silent_exclusions(tmp_path, body):
    module = inspector()
    source = tmp_path / "bad.csv"
    source.write_text(body)
    with pytest.raises(ValueError):
        module.inspect(source)


def test_cli_outputs_json_without_writing_or_training(tmp_path):
    inspector()
    source = tmp_path / "example.csv"
    source.write_text("CMPD_CHEMBLID,exp,smiles\nCHEMBL1,1.5,CCO\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(source)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["rows"] == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == ["example.csv"]
