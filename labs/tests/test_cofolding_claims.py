"""The claim inspector must hold on the committed extract and reject collapsed claims."""

import ast
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/cofolding_claims"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, LAB / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


claims = _load("inspect_claims")
exporter = _load("export_claim_records")


@pytest.fixture
def extract():
    return claims.load()


def test_the_committed_extract_passes_every_check(extract, capsys):
    assert claims.check(extract) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 10


def test_the_five_claim_classes_are_kept_apart(extract):
    family = claims.structure_family(extract)
    assert len(family) >= 18
    populated = {label for row in family for label in claims.classes_of(row)}
    # A registry that had collapsed the claims would not populate all five.
    assert populated == set(claims.CLAIM_CLASSES)


def test_no_co_folding_system_evidences_the_code_behind_its_accuracy_claim(extract):
    """The load-bearing observation: a co-folding number is not rechecked from source."""
    family = claims.structure_family(extract)
    cofolders = [row for row in family if "co-folding" in (row.get("tasks") or ())]
    assert cofolders
    assert all("evaluation_code" not in claims.evidenced(row) for row in cofolders)


def test_the_systems_that_publish_their_evaluation_code_are_named(extract):
    """The wider family has exceptions, and the inspector names them."""
    family = claims.structure_family(extract)
    published = sorted(row["id"] for row in family if "evaluation_code" in claims.evidenced(row))
    failures = claims.check(extract)
    assert not failures, failures
    # The list is named rather than counted, so that a record entering the
    # family with published evaluation code has to be added deliberately. The
    # benchmark entries expose scoring code; the assertions above cover only
    # records that themselves declare the co-folding task.
    assert published == [
        "benchmark-multipardigm-docking",
        "benchmark-plabench",
        "benchmark-plinder",
        "benchmark-posebench",
        "benchmark-protdbench",
        "model-diffdock",
        "model-rosettafold-all-atom",
    ]


def test_runs_offline_and_prints_the_three_confusions():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_claims.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "CLAIM CLASSES" in result.stdout
    assert "WHERE THE CLAIMS GET COLLAPSED" in result.stdout
    for marker in ("does not name the claim", "two claims at once", "an experimental measurement"):
        assert marker in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # A co-folding system whose evaluation code became evidenced would break the
        # finding, so the check must notice rather than keep printing the old sentence.
        (
            lambda rows: next(r for r in rows if "co-folding" in r["tasks"])["openness"].update(
                {"evaluation_code": "available"}
            ),
            "evaluation code",
        ),
        # A second dual-claim system must be surfaced, not folded into the first.
        (
            lambda rows: rows[1]["tasks"].extend(["co-folding", "affinity-prediction"]),
            "exactly one system claims both",
        ),
        # A measurement record inside the family would license a binding claim.
        (
            lambda rows: rows[0].update({"kind": "database"}),
            "no system in the family is a measurement",
        ),
        # A co-folding system that evidences both its training data and the code
        # behind its accuracy claim would let a reader attempt to recompute the
        # reported number, which is what this lab exists to prevent.
        (
            lambda rows: next(r for r in rows if "co-folding" in r["tasks"])["openness"].update(
                {"training_data": "available", "evaluation_code": "available"}
            ),
            "evidences both its training data and the code behind its accuracy claim",
        ),
        (lambda rows: rows[0].pop("last_verified"), "carries a review date"),
        # A record carried in by name rather than by task must not survive.
        (lambda rows: rows[0].update({"tasks": []}), "carried in by name"),
    ],
)
def test_a_collapsed_or_incomplete_extract_is_rejected(extract, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    broken = copy.deepcopy(extract)
    mutate(broken["records"])
    failures = claims.check(broken)
    assert any(expected in failure for failure in failures), failures


def test_a_regrouped_claim_map_is_rejected(extract):
    """The extract and the inspector must group by the same five classes."""
    broken = copy.deepcopy(extract)
    broken["claim_classes"]["co-folded complex"].append("molecular-docking")
    failures = claims.check(broken)
    assert any("same five claim classes" in failure for failure in failures), failures


def test_the_extract_selects_by_task_never_by_name():
    """Membership follows the declared task, so no record can be hand-picked in or out."""
    invented = [
        {"id": "z-outside", "kind": "model", "tasks": ["property-prediction"], "openness": {}},
        {"id": "a-in-family", "kind": "model", "tasks": ["co-folding"], "openness": {}},
    ]
    sliced = exporter.slice_registry(invented)
    assert [row["id"] for row in sliced["records"]] == ["a-in-family"]
    assert sliced["source_records"] == 2
    # Absent openness fields are recorded as unverified rather than dropped.
    assert set(sliced["records"][0]["openness"]) == set(exporter.OPENNESS_ORDER)
    assert set(sliced["records"][0]["openness"].values()) == {"unverified"}


@pytest.mark.skipif(not exporter.SOURCE.is_file(), reason="registry is a build artifact")
def test_the_committed_extract_still_matches_the_generated_registry():
    """A registry edit must not silently move a number the lesson quotes."""
    records = json.loads(exporter.SOURCE.read_text(encoding="utf-8"))
    assert exporter.slice_registry(records) == claims.load()


def test_the_inspector_reads_only_the_committed_extract():
    source = (LAB / "inspect_claims.py").read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported <= {"argparse", "json", "sys", "pathlib"}, imported
    assert claims.EXTRACT.is_file()
    assert claims.EXTRACT.suffix == ".json"
    # The extract travels with the lab. The build artifact it was sliced from is
    # named only by the exporter, so the inspector runs from a clean checkout.
    assert claims.EXTRACT.parent == LAB
    assert "resources.v1.json" not in source
    assert "site/public" not in source
