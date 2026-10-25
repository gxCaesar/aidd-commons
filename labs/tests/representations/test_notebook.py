from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import nbformat
import pytest
from aidd_commons.representations.inspection import (
    MoleculeInput,
    RepresentationConfig,
    build_report,
    render_report,
)
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

REPOSITORY_ROOT = Path(__file__).parents[3]
CANONICAL_CORE_PATH = (
    REPOSITORY_ROOT / "labs" / "src" / "aidd_commons" / "representations" / "inspection.py"
)
NOTEBOOK_NAMES = (
    "representation_inspector.ipynb",
    "representation_inspector.zh-CN.ipynb",
)
EXAMPLES = (
    ("pyridine-kekule", "C1=CC=CN=C1", "Equivalent graph written with explicit alternating bonds"),
    ("pyridine-aromatic", "n1ccccc1", "Equivalent graph written with aromatic atoms"),
    ("alanine-one", "N[C@@H](C)C(=O)O", "One defined tetrahedral stereoisomer"),
    ("alanine-two", "N[C@H](C)C(=O)O", "The opposite defined tetrahedral stereoisomer"),
    (
        "alanine-unspecified",
        "NC(C)C(=O)O",
        "Connectivity retained but tetrahedral stereochemistry unspecified",
    ),
    ("acetic-acid", "CC(=O)O", "Neutral protonation state"),
    ("sodium-acetate", "CC(=O)[O-].[Na+]", "Disconnected salt with two components"),
)


def _kernel_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Register an ephemeral kernel that uses the test interpreter, not a user kernel."""

    kernel_name = "aidd-representations-notebook-test"
    kernel_directory = tmp_path / "jupyter" / "kernels" / kernel_name
    kernel_directory.mkdir(parents=True)
    (kernel_directory / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "AIDD representations notebook test",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("JUPYTER_PATH", str(tmp_path / "jupyter"))
    monkeypatch.setenv("IPYTHONDIR", str(tmp_path / "ipython"))
    return kernel_name


def _execute(notebook: nbformat.NotebookNode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    return NotebookClient(
        notebook,
        timeout=120,
        kernel_name=_kernel_name(tmp_path, monkeypatch),
    ).execute(cwd=str(tmp_path))


def _stream_text(notebook: nbformat.NotebookNode) -> str:
    return "".join(
        output.get("text", "")
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.output_type == "stream"
    )


def _reported_payload(notebook: nbformat.NotebookNode) -> dict[str, object]:
    output = _stream_text(notebook)
    marker = "REPORT_JSON="
    assert marker in output, "the notebook did not emit its JSON report"
    return json.loads(output.split(marker, maxsplit=1)[1].splitlines()[0])


def _retained_report_payload(notebook: nbformat.NotebookNode, tmp_path: Path) -> dict[str, object]:
    output = _stream_text(notebook)
    marker = "REPORT_PATH="
    assert marker in output, "the notebook did not print the retained JSON report path"
    report_path = Path(output.split(marker, maxsplit=1)[1].splitlines()[0])

    assert report_path.name == "representation-report.json"
    assert report_path.parent.name.startswith("aidd-representation-inspector-")
    assert report_path.parent.parent.resolve() == tmp_path.resolve()
    assert report_path.exists(), (
        "the notebook removed the JSON report before students could download it"
    )
    html = "".join(
        output.get("data", {}).get("text/html", "")
        for cell in notebook.cells
        for output in cell.get("outputs", [])
    )
    download_links = re.findall(r"href=['\"]([^'\"]+)['\"]", html)
    assert report_path.relative_to(tmp_path).as_posix() in download_links, (
        "the report link must use the notebook-relative path, not an OS absolute path"
    )
    return json.loads(report_path.read_text(encoding="utf-8"))


def _expected_payload(examples: tuple[tuple[str, str, str], ...]) -> dict[str, object]:
    return json.loads(
        render_report(
            build_report(
                tuple(MoleculeInput(*example) for example in examples),
                config=RepresentationConfig(
                    morgan_radius=2,
                    morgan_bits=2048,
                    include_chirality=True,
                ),
            )
        )
    )


def test_notebook_editions_share_identical_executable_cells() -> None:
    """Catches a bilingual edit that changes runnable behavior in only one edition."""

    notebooks = [
        nbformat.read(REPOSITORY_ROOT / "labs" / "molecule_representations" / name, as_version=4)
        for name in NOTEBOOK_NAMES
    ]
    code_cells = [
        [cell.source for cell in notebook.cells if cell.cell_type == "code"]
        for notebook in notebooks
    ]
    assert code_cells[0] == code_cells[1]
    assert CANONICAL_CORE_PATH.read_text(encoding="utf-8").rstrip() in code_cells[0]


@pytest.mark.parametrize("notebook_name", NOTEBOOK_NAMES)
def test_notebook_is_clean_and_executes_the_inline_examples(
    notebook_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches a missing/non-runnable notebook or a changed inline inspection result."""

    notebook_path = REPOSITORY_ROOT / "labs" / "molecule_representations" / notebook_name
    assert notebook_path.exists(), f"missing reader notebook: {notebook_name}"
    source_text = notebook_path.read_text(encoding="utf-8")
    notebook = nbformat.reads(source_text, as_version=4)
    assert all(cell.get("execution_count") is None for cell in notebook.cells)
    assert all(not cell.get("outputs", []) for cell in notebook.cells)

    executed = _execute(notebook, tmp_path, monkeypatch)
    expected = _expected_payload(EXAMPLES)

    assert len(EXAMPLES) == 7
    assert _reported_payload(executed) == expected
    retained_payload = _retained_report_payload(executed, tmp_path)
    assert retained_payload == expected
    assert len(retained_payload["molecules"]) == 7
    assert any(
        "image/svg+xml" in output.get("data", {})
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.output_type in {"display_data", "execute_result"}
    )
    assert any(
        "<table" in output.get("data", {}).get("text/html", "")
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.output_type in {"display_data", "execute_result"}
    )
    assert notebook_path.read_text(encoding="utf-8") == source_text


@pytest.mark.parametrize("notebook_name", NOTEBOOK_NAMES)
def test_notebook_accepts_a_valid_added_example(
    notebook_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A student-added valid input produces an additional inspected record."""

    notebook_path = REPOSITORY_ROOT / "labs" / "molecule_representations" / notebook_name
    notebook = nbformat.read(notebook_path, as_version=4)
    extra_example = ("ethanol-extra", "CCO", "Student-added valid molecule")
    marker = "\n)\nCONFIG = RepresentationConfig("
    addition = (
        '\n    MoleculeInput("ethanol-extra", "CCO", "Student-added valid molecule"),'
        "\n)\nCONFIG = RepresentationConfig("
    )
    for cell in notebook.cells:
        if cell.cell_type == "code" and "EXAMPLES = (" in cell.source:
            assert marker in cell.source
            cell.source = cell.source.replace(marker, addition, 1)
            break
    else:
        pytest.fail("inline examples cell was not found for the valid-input mutation")

    executed = _execute(notebook, tmp_path, monkeypatch)
    expected = _expected_payload(EXAMPLES + (extra_example,))
    retained_payload = _retained_report_payload(executed, tmp_path)

    assert retained_payload == expected
    assert len(retained_payload["molecules"]) == 8
    assert retained_payload["molecules"][-1]["source_id"] == "ethanol-extra"


@pytest.mark.parametrize("notebook_name", NOTEBOOK_NAMES)
def test_notebook_bad_smiles_fails_closed(
    notebook_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches a notebook that silently drops malformed molecules from its worked example."""

    notebook_path = REPOSITORY_ROOT / "labs" / "molecule_representations" / notebook_name
    notebook = nbformat.read(notebook_path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code" and '"C1=CC=CN=C1"' in cell.source:
            cell.source = cell.source.replace('"C1=CC=CN=C1"', '"not-a-smiles"', 1)
            break
    else:
        pytest.fail("inline pyridine example was not found for the malformed-input mutation")

    with pytest.raises(CellExecutionError, match="RepresentationInputError.*invalid or zero-atom"):
        _execute(notebook, tmp_path, monkeypatch)
