"""Three deposited EGFR structures, read as evidence rather than as answers."""

import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "labs/egfr_structures"
sys.path.insert(0, str(LAB))

import cif  # noqa: E402
import inspect_complex  # noqa: E402
import inspect_state  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return cif.manifest()


@pytest.fixture(scope="module")
def entries():
    return cif.load_all()


@pytest.fixture(scope="module")
def state(data, entries):
    return inspect_state.measure(entries, data)


@pytest.fixture(scope="module")
def complex_(data, entries):
    return inspect_complex.measure(entries, data)


def test_the_committed_structures_pass_every_state_check(data, state, capsys):
    assert inspect_state.check(data, state) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 16


def test_the_committed_structures_pass_every_complex_check(data, complex_, capsys):
    assert inspect_complex.check(data, complex_) == []
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert printed.count("PASS") == 15


def test_the_files_have_the_recorded_deposited_metadata(data):
    assert [record["id"] for record in data["entries"]] == ["1M17", "4HJO", "1XKK"]
    assert cif.mismatched_files(data) == []
    for record in data["entries"]:
        assert record["source_url"] == f"https://files.rcsb.org/download/{record['id']}.cif.gz"
    assert data["licence"]["name"].startswith("CC0")


@pytest.mark.parametrize(
    ("defect", "diagnostic"),
    [
        ("wrong-accession", "entry identifier"),
        ("truncated", "byte size"),
        ("wrong-revision", "revision"),
        ("missing", "regular file"),
        ("symlink", "regular file"),
    ],
)
def test_input_validation_reports_the_actual_structure_defect(data, tmp_path, defect, diagnostic):
    record = copy.deepcopy(data["entries"][0])
    path = tmp_path / record["file"]
    path.parent.mkdir(parents=True)
    shutil.copyfile(LAB / record["file"], path)
    text = path.read_text()
    if defect == "wrong-accession":
        path.write_text(text.replace("_entry.id   1M17", "_entry.id   1M18", 1))
    elif defect == "truncated":
        path.write_text(text[: len(text) // 2])
    elif defect == "wrong-revision":
        path.write_text(text.replace("2024-02-14", "2024-02-15", 1))
    elif defect == "missing":
        record["file"] = "structures/missing.cif"
    else:
        source = path.with_suffix(".original.cif")
        path.rename(source)
        path.symlink_to(source)
    failures = cif.mismatched_files({"entries": [record]}, tmp_path)
    assert len(failures) == 1
    assert "1M17" in failures[0]
    assert diagnostic in failures[0]


def test_reference_numbering_is_what_makes_residues_comparable(state):
    # The hinge methionine is 769 in two files and 793 in the third.
    authors = {entry_id: e["hinge_author_number"] for entry_id, e in state["entries"].items()}
    assert authors == {"1M17": 769, "4HJO": 769, "1XKK": 793}
    for entry in state["entries"].values():
        assert entry["landmarks"] == cif.LANDMARKS


def test_the_state_descriptor_separates_one_file_from_two(state):
    distances = {entry_id: e["lys_glu_distance"] for entry_id, e in state["entries"].items()}
    assert distances["1M17"] == pytest.approx(3.71, abs=0.01)
    assert distances["4HJO"] == pytest.approx(14.41, abs=0.01)
    assert distances["1XKK"] == pytest.approx(13.73, abs=0.01)


def test_the_site_is_a_definition_that_grows_with_its_cutoff(state):
    sizes = {
        entry_id: [len(sites[c]) for c in (4.0, 5.0, 6.0)]
        for entry_id, sites in state["sites"].items()
    }
    assert sizes == {"1M17": [15, 20, 25], "4HJO": [17, 20, 26], "1XKK": [23, 28, 37]}


def test_the_hinge_pair_is_the_only_polar_contact_every_complex_shares(complex_):
    for entry_id, found in complex_["interactions"].items():
        hinge = [p for p in found["polar"] if p["residue"] == "MET793" and p["protein_atom"] == "N"]
        assert len(hinge) == 1, entry_id
        assert hinge[0]["compatible"]


def test_runs_offline_and_labels_every_constructed_pose():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_complex.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    lines = [line.strip() for line in result.stdout.splitlines()]
    poses = [line for line in lines if line == "crystal pose" or line.startswith("constructed:")]
    assert len(poses) == 3
    assert poses[0] == "crystal pose"
    assert all(line.startswith("constructed:") for line in poses[1:])
    assert "The two constructed poses are not predictions." in result.stdout


def test_state_show_runs_offline_and_names_who_assigned_the_label():
    result = subprocess.run(
        [sys.executable, str(LAB / "inspect_state.py"), "show"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    assert "depositors' label" in result.stdout
    assert "pocket-prediction method was run" in result.stdout
    assert "cannot define an allosteric or transient site" in result.stdout


@pytest.mark.parametrize("module", [inspect_state, inspect_complex])
def test_a_file_that_is_not_the_recorded_entry_stops_every_check(data, state, complex_, module):
    """Known-bad: a replaced structure file must stop the run before any verdict."""
    broken = copy.deepcopy(data)
    broken["entries"][1]["latest_revision"]["revision_date"] = "2000-01-01"
    measured = state if module is inspect_state else complex_
    failures = module.check(broken, measured)
    assert len(failures) == 1
    assert "file metadata validation" in failures[0] and "4HJO" in failures[0]


def test_comparing_by_author_number_is_caught(data, entries, monkeypatch):
    """Known-bad: skipping the reference mapping puts the wrong residue at every landmark."""
    monkeypatch.setattr(
        cif.Entry,
        "to_reference",
        lambda self, chain, author_seq: author_seq,
    )
    measured = inspect_state.measure(entries, data)
    failures = inspect_state.check(data, measured)
    assert any("landmarks" in failure and "1M17" in failure for failure in failures), failures


def test_a_role_that_contradicts_the_ligand_bonding_is_caught(data, complex_):
    """Known-bad: calling the anilino nitrogen a ring nitrogen stops the interaction verdicts."""
    broken = copy.deepcopy(data)
    broken["ligand_roles"]["AQ4"]["N1"] = {"role": "acceptor", "kind": "quinazoline ring nitrogen"}
    entries = cif.load_all()
    failures = inspect_complex.check(broken, inspect_complex.measure(entries, broken))
    assert len(failures) == 1
    assert "N1 is declared a quinazoline ring nitrogen" in failures[0]


def test_protonating_the_hinge_nitrogen_changes_the_verdict_not_the_geometry(
    data, entries, complex_
):
    """Known-bad: the same 2.70 A pair is no hydrogen bond under another protonation."""
    broken = copy.deepcopy(data)
    broken["ligand_roles"]["AQ4"]["N2"]["role"] = "donor"
    measured = inspect_complex.measure(entries, broken)
    failures = inspect_complex.check(broken, measured)
    assert any("Met793 backbone nitrogen" in failure for failure in failures), failures
    before = [p for p in complex_["interactions"]["1M17"]["polar"] if p["ligand_atom"] == "N2"]
    after = [p for p in measured["interactions"]["1M17"]["polar"] if p["ligand_atom"] == "N2"]
    assert [p["distance"] for p in before] == [p["distance"] for p in after]
    assert before[0]["compatible"] and not after[0]["compatible"]


def test_fewer_than_three_site_cutoffs_is_rejected(data, entries):
    """Known-bad: a site reported at one cutoff looks like a property of the protein."""
    broken = copy.deepcopy(data)
    broken["declared_parameters"]["site_cutoffs_angstrom"] = [4.0, 5.0]
    failures = inspect_state.check(broken, inspect_state.measure(entries, broken))
    assert any("three or more cutoffs" in failure for failure in failures), failures
