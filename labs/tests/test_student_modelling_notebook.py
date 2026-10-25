"""Execute the standalone student notebooks in fresh, isolated kernels."""

import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

LAB = Path(__file__).parents[1] / "student_modelling"
RUNNER = LAB / "run_lab.py"


def canonical_module():
    spec = importlib.util.spec_from_file_location("student_modelling_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def notebook(language="en"):
    name = "student_modelling_tutorial" + (".zh-CN" if language == "zh" else "") + ".ipynb"
    path = LAB / name
    assert path.is_file(), "The standalone student notebook is not implemented"
    return nbformat.read(path, as_version=4)


def execute_notebook(tmp_path, language, mutate_test_responses=False):
    book = notebook(language)
    if mutate_test_responses:
        for cell in book.cells:
            if "rows" in cell.metadata.get("tags", []):
                cell.source += (
                    "\nfor row in rows:\n    if row['split'] == 'test':\n"
                    "        row['response'] += 100\n"
                )
                break
        else:  # pragma: no cover - makes an authoring regression clear
            raise AssertionError("The editable row cell is missing")
    executed = NotebookClient(book, timeout=120, kernel_name="python3").execute(cwd=str(tmp_path))
    notebooks = list(tmp_path.glob("student-modelling-*"))
    assert len(notebooks) == 1
    report_path = notebooks[0] / "student_report.json"
    assert report_path.is_file()
    svg_path = notebooks[0] / "fitted_models.svg"
    assert svg_path.is_file()
    assert "Ridge response" in svg_path.read_text(encoding="utf-8")
    svg_root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    canvas_height = float(svg_root.attrib["height"])
    for label in svg_root.findall("{http://www.w3.org/2000/svg}text"):
        if "transform" not in label.attrib:
            assert float(label.attrib["y"]) + 3 <= canvas_height, "Plot label is clipped"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert any(
        "image/svg+xml" in output.get("data", {})
        for cell in executed.cells
        for output in cell.get("outputs", [])
    ), "The fitted line/probabilities were not rendered as an SVG"
    return report


def test_notebooks_are_clean_and_have_identical_executable_cells():
    english, chinese = notebook(), notebook("zh")
    for book in (english, chinese):
        nbformat.validate(book)
        assert all(not cell.get("outputs") for cell in book.cells)
        assert all(cell.get("execution_count") is None for cell in book.cells)
    assert [cell.source for cell in english.cells if cell.cell_type == "code"] == [
        cell.source for cell in chinese.cells if cell.cell_type == "code"
    ]


def test_notebooks_match_canonical_protocol_and_keep_test_labels_out_of_selection(
    tmp_path, monkeypatch
):
    expected = json.loads(json.dumps(canonical_module().run(canonical_module().teaching_rows())))
    monkeypatch.setenv("IPYTHONDIR", str(tmp_path / "ipython"))
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "matplotlib"))
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    english_dir, chinese_dir = tmp_path / "english", tmp_path / "chinese"
    english_dir.mkdir()
    chinese_dir.mkdir()
    observed = execute_notebook(english_dir, "en")
    mutated = execute_notebook(chinese_dir, "zh", mutate_test_responses=True)

    assert observed == expected
    assert observed["selection"]["regression_alpha"] == 0.0
    assert observed["selection"]["classification_alpha"] == 0.0
    assert observed["test_metrics"]["ridge"]["mae"] == 4.5
    assert observed["test_metrics"]["train_mean"]["mae"] == 3.5
    assert observed["test_metrics"]["logistic"]["log_loss"] == pytest.approx(5.359325802153142)
    assert observed["test_metrics"]["train_prevalence"]["log_loss"] == pytest.approx(
        0.6931471805599453
    )
    assert [row["prediction"] for row in observed["test_predictions"]] == [13.0, 15.0]
    assert mutated["selection"] == observed["selection"]
    assert mutated["validation_scores"] == observed["validation_scores"]
    assert mutated["models"] == observed["models"]
    assert [row["prediction"] for row in mutated["test_predictions"]] == [
        row["prediction"] for row in observed["test_predictions"]
    ]
    assert mutated["test_metrics"] != observed["test_metrics"]
