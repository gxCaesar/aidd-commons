from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_inspector_cli_writes_deterministic_json(tmp_path: Path) -> None:
    repository_root = Path(__file__).parents[3]
    input_path = tmp_path / "molecules.csv"
    output_path = tmp_path / "report.json"
    repeated_output_path = tmp_path / "report-repeat.json"
    input_path.write_text(
        "id,smiles,teaching_point\n"
        'ethanol,CCO,"small neutral molecule"\n'
        'pyridine,n1ccccc1,"aromatic heterocycle"\n',
        encoding="utf8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repository_root / "labs" / "molecule_representations" / "run_lab.py"),
            "inspect",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Representation report written" in result.stdout
    report = json.loads(output_path.read_text(encoding="utf8"))
    assert [molecule["source_id"] for molecule in report["molecules"]] == [
        "ethanol",
        "pyridine",
    ]

    repeated = subprocess.run(
        [
            sys.executable,
            str(repository_root / "labs" / "molecule_representations" / "run_lab.py"),
            "inspect",
            "--input",
            str(input_path),
            "--output",
            str(repeated_output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert repeated.returncode == 0, repeated.stderr
    assert output_path.read_text(encoding="utf8") == repeated_output_path.read_text(
        encoding="utf8"
    )


def test_inspector_cli_exposes_only_label_free_inspection() -> None:
    repository_root = Path(__file__).parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(repository_root / "labs" / "molecule_representations" / "run_lab.py"),
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "inspect" in result.stdout
    assert "train" not in result.stdout.lower()
    assert "evaluate" not in result.stdout.lower()
