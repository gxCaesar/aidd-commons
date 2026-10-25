"""The dossier inspector must hold on the committed artifacts and reject deletions."""

import ast
import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/counterevidence"

_spec = importlib.util.spec_from_file_location("inspect_dossier", LAB / "inspect_dossier.py")
dossier = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(dossier)


@pytest.fixture
def records():
    return dossier.load()


def test_the_committed_artifacts_pass_every_check(records, capsys):
    assert dossier.check(records) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 13


def test_the_transfer_failure_is_recomputed_not_asserted(records):
    """The lesson's sharpest number must come from the committed metrics."""
    rows = dossier.transfer_failure(records)
    primary, replication = rows["primary_test"], rows["assay_replication"]
    assert primary["best"] == "morgan_ridge"
    assert replication["worst"] == "morgan_ridge"
    # Best on one comparison, and several times the baseline error on the other.
    assert primary["mae"]["morgan_ridge"] < primary["mae"]["train_mean"]
    assert replication["mae"]["morgan_ridge"] > 3 * replication["mae"]["train_mean"]
    assert replication["spearman"]["morgan_ridge"] < 0 < primary["spearman"]["morgan_ridge"]


def test_the_refused_metric_is_null_rather_than_zero(records):
    """A constant prediction has no rank correlation, and zero would invent one."""
    undefined = dossier.undefined_metrics(records)
    assert len(undefined) == 3
    assert {status for _, _, status in undefined} == {"undefined_constant_prediction"}
    for comparison in records["chembl-locked"]["results"].values():
        assert comparison["metrics"]["train_mean"]["spearman"] is None


def test_the_exposure_is_disclosed_by_both_labs(records):
    """A one-sided disclosure would leave the second lab looking independent."""
    assert dossier.two_sided(records, "T15 accessed labels shared with T05") == [
        "chembl-locked",
        "pool-budget-real",
    ]


def test_the_designed_policy_lost_in_both_replays(records):
    lost = dossier.lost_policies(records)
    assert set(lost) == {"CHEMBL5736995", "CHEMBL3705421"}
    assert lost["CHEMBL3705421"]["designed"] == 0.0
    for block in lost.values():
        assert block["designed"] < min(block["randoms"].values())


def test_runs_offline_and_prints_the_three_deletions():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_dossier.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "PRESERVED COUNTEREVIDENCE" in result.stdout
    assert "WHAT A CLEAN SUMMARY WOULD HAVE DELETED" in result.stdout
    for marker in ("winner that fails on transfer", "both sides", "refused rather than filled in"):
        assert marker in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Deleting the sentence that keeps the two comparisons apart.
        (
            lambda r: r["chembl-locked"]["interpretation"].remove(
                "Primary evaluation and assay replication are separate comparisons;"
                " success on one does not erase failure on the other."
            ),
            "one comparison does not erase the other",
        ),
        # Filling the refused correlation with a number the baseline cannot support.
        (
            lambda r: r["chembl-locked"]["results"]["primary_test"]["metrics"]["train_mean"].update(
                {"spearman": 0.0, "spearman_status": "defined"}
            ),
            "refused as undefined",
        ),
        # Keeping the status but storing a number arithmetic could consume.
        (
            lambda r: r["chembl-locked"]["results"]["primary_test"]["metrics"]["train_mean"].update(
                {"spearman": 0.0}
            ),
            "stored as null",
        ),
        # Dropping the exposure from the lab that caused it leaves the other looking independent.
        (
            lambda r: r["pool-budget-real"]["interpretation"].__setitem__(
                3, "The T05 and T11 evaluations completed without retuning."
            ),
            "disclosed on both sides",
        ),
        # Promoting a not-run evaluation to a result that was never produced.
        (
            lambda r: r["rmd17-development"]["locked_evaluations"].update(
                {"benzene": "completed", "uracil": "completed"}
            ),
            "recorded as not run",
        ),
        # Quietly dropping the losing policy from the replay.
        (
            lambda r: r["pool-budget-real"]["assays"]["CHEMBL3705421"].__setitem__(
                "policies",
                [
                    row
                    for row in r["pool-budget-real"]["assays"]["CHEMBL3705421"]["policies"]
                    if row["name"] != "maxmin"
                ]
                + [{"name": "maxmin", "normalized_auc": 0.5}],
            ),
            "recovering nothing at all",
        ),
        # Emptying a whole disclosure block.
        (lambda r: r["freesolv"].update({"caveats": []}), "carry at least one disclosure line"),
        # Softening a refusal into a claim about what was found.
        (
            lambda r: r["rmd17-locked"]["interpretation"].__setitem__(
                2, "Confidence intervals were computed and were narrow."
            ),
            "refuse them outright",
        ),
    ],
)
def test_a_cleaned_dossier_is_rejected(records, mutate, expected):
    """Known-bad edits: each deletion or softening must be caught by a named check."""
    broken = copy.deepcopy(records)
    mutate(broken)
    failures = dossier.check(broken)
    assert any(expected in failure for failure in failures), failures


def test_the_inspector_reads_only_committed_artifacts():
    source = (LAB / "inspect_dossier.py").read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported <= {"argparse", "json", "sys", "pathlib"}, imported
    for relative in dossier.ARTIFACTS.values():
        assert (ROOT / relative).is_file()
        assert relative.startswith("labs/")
