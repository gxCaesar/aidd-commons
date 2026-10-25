"""The rMD17 contract inspector must agree with the committed artifacts and reject drift."""

import ast
import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/rmd17_system_state"

_spec = importlib.util.spec_from_file_location(
    "rmd17_inspect_contract", LAB / "inspect_contract.py"
)
rmd17 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(rmd17)


@pytest.fixture
def artifacts():
    return (
        rmd17.load("protocol.json"),
        rmd17.load("development-summary.json"),
        rmd17.load("locked-summary.json"),
    )


def test_committed_artifacts_pass_every_check(artifacts, capsys):
    assert rmd17.check(*artifacts) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 14


def test_contract_runs_without_network_or_arguments():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_contract.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "OBSERVABLE AND FEATURE BOUNDARY" in result.stdout
    assert "SAMPLING AND FRAME DEPENDENCE" in result.stdout
    assert "METRIC BOUNDARY" in result.stdout
    # Every reported error must be printed beside the range it is measured over.
    assert result.stdout.count("target range") >= 5
    # The stated limitations are part of the contract, not an appendix.
    assert result.stdout.count("limitation:") == 3


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        (("split", "partitions", "train"), 500, "partitions sum"),
        (("selection", "selected_alpha"), 10.0, "selection replays"),
        (("features", "by_system", "ethanol", "channel_count"), 4, "ethanol feature dimension"),
        (("software", "scikit_learn"), "1.4.0", "same python, numpy and scikit-learn"),
        (
            (
                "split",
                "ordering_diagnostics_by_system",
                "ethanol",
                "adjacent_original_index_gap",
                "minimum",
            ),
            1,
            "never consecutive",
        ),
    ],
)
def test_drift_in_the_development_summary_is_rejected(artifacts, path, value, expected):
    """Known-bad edits: each one must be caught by a named check."""
    protocol, development, locked = artifacts
    broken = copy.deepcopy(development)
    target = broken
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    failures = rmd17.check(protocol, broken, locked)
    assert any(expected in failure for failure in failures), failures


def test_a_prohibited_array_promoted_to_a_feature_is_rejected(artifacts):
    """The leakage boundary is the point of this contract; moving it must fail."""
    protocol, development, locked = artifacts
    broken = copy.deepcopy(protocol)
    broken["feature_and_target_boundaries"]["allowed_feature_arrays"].append("old_energies")
    failures = rmd17.check(broken, development, locked)
    assert any("disjoint" in failure for failure in failures)


def test_a_locked_result_without_its_target_range_is_rejected(artifacts):
    """An error reported without its denominator must not pass silently."""
    protocol, development, locked = artifacts
    broken = copy.deepcopy(locked)
    del broken["results"]["benzene"]["ridge"]["target_range"]
    failures = rmd17.check(protocol, development, broken)
    assert any("target range" in failure for failure in failures)


def test_the_inspector_reads_only_committed_lab_files():
    source = (LAB / "inspect_contract.py").read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported <= {"argparse", "json", "sys", "pathlib"}, imported
    for name in ("protocol.json", "development-summary.json", "locked-summary.json"):
        assert name in source
        assert (LAB / name).is_file()
