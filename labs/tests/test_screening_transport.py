"""A result repeating in two contexts must not be read as a result that transports."""

import copy
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/screening_transport"

_spec = importlib.util.spec_from_file_location("inspect_transport", LAB / "inspect_transport.py")
transport = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(transport)


@pytest.fixture(scope="module")
def loaded():
    return transport.load()


def test_the_committed_replay_passes_every_check(loaded, capsys):
    replay, chembl = loaded
    assert transport.check(replay, chembl) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 11


def test_resolution_is_derived_from_the_target_count(loaded):
    """The unit that makes two contexts comparable is one recovered target."""
    replay, _ = loaded
    rows = {row["assay"]: row for row in transport.contexts(replay)}
    assert rows["CHEMBL5736995"]["targets"] == 64
    assert rows["CHEMBL3705421"]["targets"] == 13
    for row in rows.values():
        assert row["resolution"] == 1 / row["targets"]
    ratio = rows["CHEMBL3705421"]["resolution"] / rows["CHEMBL5736995"]["resolution"]
    assert round(ratio, 2) == 4.92


def test_the_baseline_range_is_about_one_target_wide_in_both(loaded):
    """A range this narrow describes arithmetic, not population variability."""
    replay, _ = loaded
    for row in transport.contexts(replay):
        assert len(row["randoms"]) == 5
        assert row["spread_in_targets"] < 2


def test_the_most_dramatic_outcome_carries_the_least_evidence(loaded):
    """Recovering nothing sounds total; the margin is a fraction of one target."""
    replay, _ = loaded
    rows = {row["assay"]: row for row in transport.contexts(replay)}
    assert rows["CHEMBL3705421"]["designed"] == 0.0
    assert rows["CHEMBL3705421"]["gap_in_targets"] < 0.2
    # The context that lost by more is the one that did not score zero.
    assert rows["CHEMBL5736995"]["gap_in_targets"] > rows["CHEMBL3705421"]["gap_in_targets"]


def test_the_contexts_are_disjoint_chemistry(loaded):
    """A repeat over the same molecules would not be a repeat at all."""
    _, chembl = loaded
    shared = transport.independence(chembl)
    assert shared["parent_overlap"] == 0
    assert shared["primary_assay"] != shared["replication_assay"]


def test_runs_offline_and_states_what_it_cannot_address():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_transport.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "DID THE RESULT TRANSPORT, OR ONLY REPEAT?" in result.stdout
    assert "WHAT THIS CANNOT ADDRESS" in result.stdout
    assert "Off-targets" in result.stdout
    assert "Prospective follow-up" in result.stdout


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # Equalising the target counts hides that the two contexts measure differently.
        (
            lambda r, c: r["assays"]["CHEMBL3705421"]["budget"].update({"top_decile_size": 64}),
            "differ in measurement resolution",
        ),
        # Widening the seed spread past a target would license an error bar.
        (
            lambda r, c: r["assays"]["CHEMBL3705421"]["policies"].__setitem__(
                1, {"name": "random-0", "normalized_auc": 0.9}
            ),
            "under two recovered targets",
        ),
        # A designed policy that wins somewhere breaks the repeat.
        (
            lambda r, c: r["assays"]["CHEMBL5736995"]["policies"].__setitem__(
                0, {"name": "maxmin", "normalized_auc": 0.5}
            ),
            "lost in every context",
        ),
        # Overlapping parents would make the second context the same molecules again.
        (lambda r, c: c["data"].update({"parent_overlap": 40}), "parent compounds"),
        # Dropping a seed changes what the five instances are.
        (
            lambda r, c: r["assays"]["CHEMBL3705421"]["policies"].pop(),
            "five fixed random instances",
        ),
    ],
)
def test_a_softened_replay_is_rejected(loaded, mutate, expected):
    """Known-bad edits: each must be caught by a named check."""
    replay, chembl = loaded
    broken_replay = copy.deepcopy(replay)
    broken_chembl = copy.deepcopy(chembl)
    mutate(broken_replay, broken_chembl)
    failures = transport.check(broken_replay, broken_chembl)
    assert any(expected in failure for failure in failures), failures


def test_the_inspector_reads_only_committed_summaries():
    source = (LAB / "inspect_transport.py").read_text(encoding="utf-8")
    assert "import json" in source
    for name in ("requests", "urllib", "rdkit", "numpy", "sklearn"):
        assert f"import {name}" not in source
    assert transport.REPLAY.is_file() and transport.CHEMBL.is_file()
