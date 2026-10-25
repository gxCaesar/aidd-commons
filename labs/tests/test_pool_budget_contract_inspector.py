"""The pool-budget inspector must recompute the reported numbers and reject drift."""

import ast
import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/pool_budget"

_spec = importlib.util.spec_from_file_location(
    "pool_budget_inspect_contract", LAB / "inspect_contract.py"
)
pool_budget = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(pool_budget)


@pytest.fixture
def artifacts():
    return pool_budget.load("real-protocol.json"), pool_budget.load("real-summary.json")


def test_committed_artifacts_pass_every_check(artifacts, capsys):
    assert pool_budget.check(*artifacts) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    # Both assays, six policies each, plus the shared protocol check.
    assert printed.count("PASS") == 53


def test_recovery_auc_is_a_trapezoid_not_a_mean():
    """The reported AUC must be reproducible from the raw checkpoint series."""
    recovery = [0.0, 0.0, 0.0625, 0.078125, 0.125]
    assert pool_budget.recovery_auc(recovery) == pytest.approx(0.05078125)
    # A mean over the same points would give a different number, which is why the
    # checker recomputes rather than trusting the recorded value.
    assert sum(recovery) / len(recovery) != pytest.approx(0.05078125)


def test_contract_runs_without_network_or_arguments():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_contract.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "POLICY ACCESS AND WHAT A SEED IS" in result.stdout
    assert "FIT, LOCK, THEN SCORE" in result.stdout
    assert "COMPLETED CAMPAIGN" in result.stdout
    # The negative result is stated for both assays rather than summarised away.
    assert result.stdout.count("That result is retained, not reframed.") == 2


@pytest.mark.parametrize(
    ("assay", "path", "value", "expected"),
    [
        ("CHEMBL5736995", ("budget", "batch_size"), 32, "batch size is floor"),
        ("CHEMBL5736995", ("budget", "top_decile_size"), 63, "target count is ceil"),
        ("CHEMBL5736995", ("budget", "actual_budget_fraction"), 0.2, "budget fraction equals"),
        (
            "CHEMBL3705421",
            ("partitions", "initial", "parents"),
            13,
            "partitions sum to the 170 parents",
        ),
    ],
)
def test_budget_drift_is_rejected(artifacts, assay, path, value, expected):
    """Known-bad edits: each one must be caught by a named check."""
    protocol, summary = artifacts
    broken = copy.deepcopy(summary)
    target = broken["assays"][assay]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    failures = pool_budget.check(protocol, broken)
    assert any(expected in failure for failure in failures), failures


def test_a_restated_auc_that_does_not_match_its_series_is_rejected(artifacts):
    """The headline number cannot drift away from the series it summarises."""
    protocol, summary = artifacts
    broken = copy.deepcopy(summary)
    policy = next(
        item for item in broken["assays"]["CHEMBL5736995"]["policies"] if item["name"] == "maxmin"
    )
    policy["normalized_auc"] = 0.2
    failures = pool_budget.check(protocol, broken)
    assert any("recovery AUC recomputes" in failure for failure in failures)


def test_a_decreasing_recovery_series_is_rejected(artifacts):
    """Selection is without replacement, so recovery can never fall."""
    protocol, summary = artifacts
    broken = copy.deepcopy(summary)
    policy = broken["assays"]["CHEMBL5736995"]["policies"][0]
    policy["recovery"] = [0.0, 0.5, 0.25, 0.3, 0.4]
    failures = pool_budget.check(protocol, broken)
    assert any("never decreases" in failure for failure in failures)


def test_a_dropped_seed_is_rejected(artifacts):
    """All five declared seeds must be reported, not a favourable subset."""
    protocol, summary = artifacts
    broken = copy.deepcopy(summary)
    assay = broken["assays"]["CHEMBL5736995"]
    assay["policies"] = [item for item in assay["policies"] if item["name"] != "random-3"]
    failures = pool_budget.check(protocol, broken)
    assert any("declared seeds" in failure for failure in failures)


def test_the_inspector_reads_only_committed_lab_files():
    source = (LAB / "inspect_contract.py").read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported <= {"argparse", "json", "math", "sys", "pathlib"}, imported
    for name in ("real-protocol.json", "real-summary.json"):
        assert name in source
        assert (LAB / name).is_file()
