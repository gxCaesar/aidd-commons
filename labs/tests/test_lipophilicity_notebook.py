"""Execute exact teaching cells in clean kernels on explicitly invented labels."""

import json
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
from nbclient import NotebookClient

LAB = Path(__file__).parents[1] / "lipophilicity"


def notebook(language="en"):
    filename = "lipophilicity_tutorial" + (".zh-CN" if language == "zh" else "") + ".ipynb"
    path = LAB / filename
    assert path.is_file(), "Standalone teaching notebook is not implemented"
    return nbformat.read(path, as_version=4)


def test_notebooks_have_identical_executable_cells_and_clean_portable_outputs():
    en, zh = notebook(), notebook("zh")
    for book in [en, zh]:
        nbformat.validate(book)
        assert all(not cell.get("outputs") for cell in book.cells)
        assert all(cell.get("execution_count") is None for cell in book.cells)
    assert [cell.source for cell in en.cells if cell.cell_type == "code"] == [
        cell.source for cell in zh.cells if cell.cell_type == "code"
    ]


def execute_fixture(tmp_path, language, mutation=False):
    book = notebook(language)
    # Distinct ring systems: 20 records with invented labels, not assay observations.
    smiles = [
        "c1ccccc1",
        "c1ccncc1",
        "c1ccoc1",
        "c1ccsc1",
        "c1cc[nH]c1",
        "C1CC1",
        "C1CCC1",
        "C1CCCC1",
        "C1CCCCC1",
        "C1CCCCCC1",
        "C1CO1",
        "C1CN1",
        "C1CS1",
        "C1COC1",
        "C1CNC1",
        "C1CCOC1",
        "C1CCNC1",
        "C1CCSC1",
        "C1COCCN1",
        "c1nccnc1",
    ]
    data = pd.DataFrame(
        {
            "CMPD_CHEMBLID": [f"CHEMBL{i + 1}" for i in range(20)],
            "exp": np.arange(20) % 5 / 2,
            "smiles": smiles,
        }
    )
    if mutation:
        data.loc[:1, "exp"] += 10  # Singleton scaffold ordering puts first rows in test.
    path = tmp_path / "constructed.csv"
    data.to_csv(path, index=False)
    output = tmp_path / "student-output"
    output.mkdir()
    for cell in book.cells:
        if "parameters" in cell.metadata.get("tags", []):
            cell.source = (
                f"DATA_PATH = Path({str(path)!r})\n"
                "DATA_KIND = 'constructed-test-fixture-not-assay-results'\n"
                "DATA_URL = ''\n"
                f"OUTPUT_DIR = Path({str(output)!r})\n"
            )
    executed = NotebookClient(book, timeout=120, kernel_name="python3").execute(cwd=str(tmp_path))
    nbformat.write(executed, tmp_path / "executed.ipynb")
    result = json.loads((output / "summary.json").read_text())
    assert result["data_kind"] == "constructed-test-fixture-not-assay-results"
    assert result["counts"] == {"train": 16, "validation": 2, "test": 2}
    assert all(np.isfinite(row["rmse"]) for row in result["test_metrics"].values())
    assert (output / "prediction-errors.png").stat().st_size > 0
    assert (output / "split-membership.csv").is_file()
    assert (output / "test-predictions.csv").is_file()
    assert any(
        "image/svg+xml" in out.get("data", {})
        for cell in executed.cells
        for out in cell.get("outputs", [])
    ), "Molecule drawing was not actually rendered"
    return result, pd.read_csv(output / "test-predictions.csv")


def test_english_and_chinese_run_and_test_labels_cannot_change_selection(tmp_path, monkeypatch):
    notebook()  # Missing artifact should fail before starting any kernel.
    monkeypatch.setenv("IPYTHONDIR", str(tmp_path / "ipython"))
    original_dir, changed_dir = tmp_path / "english", tmp_path / "chinese"
    original_dir.mkdir()
    changed_dir.mkdir()
    original, predictions = execute_fixture(original_dir, "en")
    changed, changed_predictions = execute_fixture(changed_dir, "zh", mutation=True)
    assert original["selected_alpha"] == changed["selected_alpha"]
    assert original["validation_scores"] == changed["validation_scores"]
    for name in ["train_mean", "descriptors", "morgan"]:
        np.testing.assert_allclose(predictions[name], changed_predictions[name])
    assert original["test_metrics"] != changed["test_metrics"]
