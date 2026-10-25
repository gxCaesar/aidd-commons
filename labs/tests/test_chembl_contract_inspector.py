"""The contract inspector must agree with the committed artifacts and reject drift."""

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/chembl_egfr"
sys.path.insert(0, str(LAB))

from inspect_contract import check, load  # noqa: E402


@pytest.fixture
def artifacts():
    return (
        load("protocol.json"),
        load("development-summary.json"),
        load("locked-summary.json"),
        load("execution-amendment.json"),
    )


def test_committed_artifacts_pass_every_check(artifacts, capsys):
    assert check(*artifacts) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    # The unrewritten protocol state is reported rather than silently reconciled.
    assert "not_run" in printed and "completed" in printed


def test_contract_runs_without_network_or_arguments():
    """A reader must be able to inspect the contract before downloading anything."""
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_contract.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "SCREENING UNIT" in result.stdout
    assert "ENDPOINT DEFINITION" in result.stdout
    assert "ENTITY AND ADMISSION" in result.stdout
    # Each block must state what the rule excludes, not only what it admits.
    assert result.stdout.count("Excluded by this choice") == 2
    assert "CHEMBL5736995" in result.stdout and "CHEMBL3705421" in result.stdout


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        (("data", "primary", "exclusion_counts", "missing_structure"), 8, "admission arithmetic"),
        (("selection", "selected_alphas", "morgan_ridge"), 10.0, "selection replays"),
        (("protocol_version",), "chembl37-egfr-representation-v2", "declare protocol"),
        (("software", "rdkit"), "2024.03.1", "same python, numpy and rdkit"),
    ],
)
def test_drift_in_the_development_summary_is_rejected(artifacts, path, value, expected):
    """Known-bad edits: each one must be caught by a named check."""
    protocol, development, locked, amendment = artifacts
    broken = copy.deepcopy(development)
    target = broken
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    failures = check(protocol, broken, locked, amendment)
    assert any(expected in failure for failure in failures), failures


def test_a_reselected_alpha_in_the_locked_run_is_rejected(artifacts):
    """The amendment forbids reselection; the checker must notice if it happened."""
    protocol, development, locked, amendment = artifacts
    broken = copy.deepcopy(locked)
    broken["selected_alphas"]["descriptor_ridge"] = 100.0
    failures = check(protocol, development, broken, amendment)
    assert any("reused the development alphas" in failure for failure in failures)


def test_the_inspector_reads_only_committed_lab_files():
    """No network, no download and no third-party import in the teaching entry."""
    source = (LAB / "inspect_contract.py").read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    # Version strings such as "rdkit" may be compared as data; importing them may not.
    assert imported <= {"argparse", "json", "sys", "pathlib"}, imported
    referenced = {
        name
        for name in (
            "protocol.json",
            "development-summary.json",
            "locked-summary.json",
            "execution-amendment.json",
        )
        if name in source
    }
    assert len(referenced) == 4
    for name in referenced:
        assert (LAB / name).is_file()
        json.loads((LAB / name).read_text(encoding="utf-8"))
