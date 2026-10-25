from __future__ import annotations

from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient


def test_freesolv_results_notebook_is_clean_and_executes_without_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root = Path(__file__).parents[3]
    notebook_path = repository_root / "labs" / "freesolv" / "freesolv_honest_baselines.ipynb"
    source_text = notebook_path.read_text(encoding="utf-8")
    notebook = nbformat.reads(source_text, as_version=4)
    code_sources = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")

    assert "/Users/" not in source_text
    assert "evaluate_test" not in code_sources
    assert "run_lab.py" not in code_sources
    assert "reviewed-results.json" in code_sources
    assert "results/metrics.json" not in code_sources
    assert all(cell.get("execution_count") is None for cell in notebook.cells)
    assert all(not cell.get("outputs", []) for cell in notebook.cells)

    monkeypatch.setenv("IPYTHONDIR", str(tmp_path / "ipython"))
    executed = NotebookClient(notebook, timeout=60, kernel_name="python3").execute(
        cwd=str(repository_root)
    )
    executed_path = tmp_path / "freesolv_honest_baselines.executed.ipynb"
    nbformat.write(executed, executed_path)
    executed_text = executed_path.read_text(encoding="utf-8")
    rendered_output = "\n".join(
        output.get("text", "")
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
    )

    assert executed_path.exists()
    assert "/Users/" not in executed_text
    assert rendered_output.index("Scaffold-primary results") < rendered_output.index(
        "Random-split contrast"
    )
    assert "marginal coverage, not conditional calibration" in rendered_output
    assert notebook_path.read_text(encoding="utf-8") == source_text
