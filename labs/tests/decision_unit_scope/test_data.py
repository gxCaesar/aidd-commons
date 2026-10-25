"""The data contract: the admission rule, the entity rule and the cache guards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from aidd_commons.decision_unit_scope.data import (
    DataContractError,
    DataDownloadError,
    classify_row,
    download_and_cache_snapshot,
    fetch_parent_activity_rows,
    fragment_count,
    load_cached_cohort,
    normalise_activity_row,
    normalise_molecule,
    validate_chembl_status,
)
from aidd_commons.decision_unit_scope.protocol import (
    CHEMBL_STATUS_URL,
    COHORT_SEEDS,
    ENDPOINT_TYPES,
    EXCLUSION_PRIORITY,
    STANDARD_UNITS,
)

PARENT = "CHEMBL593"
SEED = "CHEMBL929"


def activity_row(
    activity_id: int,
    *,
    molecule_id: str = PARENT,
    parent_id: str = PARENT,
    smiles: str = "c1ccccc1",
    standard_type: str = "IC50",
    standard_relation: str = "=",
    standard_value: str = "40.0",
    standard_units: str = "nM",
    standard_flag: int = 1,
    potential_duplicate: int = 0,
    data_validity_comment: str | None = None,
    assay_chembl_id: str = "CHEMBL_ASSAY_1",
    document_chembl_id: str = "CHEMBL_DOC_1",
) -> dict[str, Any]:
    return {
        "activity_id": activity_id,
        "assay_chembl_id": assay_chembl_id,
        "document_chembl_id": document_chembl_id,
        "canonical_smiles": smiles,
        "data_validity_comment": data_validity_comment,
        "molecule_chembl_id": molecule_id,
        "parent_molecule_chembl_id": parent_id,
        "pchembl_value": "7.40",
        "potential_duplicate": potential_duplicate,
        "standard_flag": standard_flag,
        "standard_relation": standard_relation,
        "standard_type": standard_type,
        "standard_units": standard_units,
        "standard_value": standard_value,
    }


def test_the_admission_rule_reports_each_declared_exclusion_reason() -> None:
    mutations: tuple[tuple[str, dict[str, Any]], ...] = (
        ("outside_endpoint_family", {"standard_type": "Tissue Severity Score"}),
        ("non_nanomolar_units", {"standard_units": "uM"}),
        ("non_standard_activity", {"standard_flag": 0}),
        ("potential_duplicate", {"potential_duplicate": 1}),
        ("data_validity_comment", {"data_validity_comment": "Outside typical range"}),
        ("missing_value", {"standard_value": ""}),
        ("missing_structure", {"canonical_smiles": ""}),
        ("missing_relation", {"standard_relation": None}),
    )
    for reason, mutation in mutations:
        row = activity_row(1)
        row.update(mutation)
        assert classify_row(row) == reason, reason


def test_the_admission_rule_keeps_a_point_measurement_and_a_bound_apart() -> None:
    assert classify_row(activity_row(1)) == "point"
    assert classify_row(activity_row(2, standard_relation=">")) == "bound"
    assert classify_row(activity_row(3, standard_relation="<")) == "bound"
    assert classify_row(activity_row(4, standard_relation=">=")) == "bound"


def test_a_salt_row_is_admitted_rather_than_rejected() -> None:
    """The deliberate difference from labs/chembl_egfr, which treats it as an error."""
    row = activity_row(1, molecule_id=SEED, parent_id=PARENT, smiles="c1ccccc1.Cl")
    assert classify_row(row) == "point"
    normalised = normalise_activity_row(row)
    assert normalised.is_child_form is True
    assert normalised.parent_molecule_chembl_id == PARENT


def test_the_exclusion_reasons_partition_a_set_of_rows_exactly() -> None:
    rows = [activity_row(1), activity_row(2, standard_type="Activity")]
    rows.append(activity_row(3, standard_flag=0))
    verdicts = [classify_row(row) for row in rows]
    assert verdicts.count("point") == 1
    excluded = [verdict for verdict in verdicts if verdict not in ("point", "bound")]
    assert all(reason in EXCLUSION_PRIORITY for reason in excluded)
    assert len(excluded) == len(rows) - 1


def test_every_declared_endpoint_type_is_admitted_and_nothing_else_is() -> None:
    for standard_type in ENDPOINT_TYPES:
        assert classify_row(activity_row(1, standard_type=standard_type)) == "point"
    assert classify_row(activity_row(1, standard_type="ED50")) == "outside_endpoint_family"
    assert classify_row(activity_row(1, standard_type="Activity")) == "outside_endpoint_family"


def test_only_nanomolar_rows_are_admitted() -> None:
    assert classify_row(activity_row(1, standard_units=STANDARD_UNITS)) == "point"
    assert classify_row(activity_row(1, standard_units="uM")) == "non_nanomolar_units"
    assert classify_row(activity_row(1, standard_units="ug.mL-1")) == "non_nanomolar_units"


def test_a_molecule_resolves_to_its_parent_and_a_multi_component_structure_is_counted() -> None:
    payload = {
        "molecule_chembl_id": SEED,
        "pref_name": "DELAVIRDINE MESYLATE",
        "molecule_hierarchy": {"parent_chembl_id": PARENT},
        "molecule_structures": {"canonical_smiles": "c1ccccc1.CS(=O)(=O)O"},
    }
    record = normalise_molecule(payload, SEED, "DELAVIRDINE MESYLATE")
    assert record.parent_molecule_chembl_id == PARENT
    assert record.is_own_parent is False
    assert record.fragment_count == 2
    assert fragment_count("c1ccccc1") == 1


def test_a_molecule_that_names_another_parent_is_rejected() -> None:
    payload = {
        "molecule_chembl_id": SEED,
        "pref_name": "DELAVIRDINE MESYLATE",
        "molecule_hierarchy": {"parent_chembl_id": "CHEMBL_NOT_DECLARED"},
        "molecule_structures": {"canonical_smiles": "c1ccccc1"},
    }
    with pytest.raises(DataContractError, match="does not declare"):
        normalise_molecule(payload, SEED, "DELAVIRDINE MESYLATE")


def test_a_molecule_whose_name_does_not_match_the_protocol_is_rejected() -> None:
    payload = {
        "molecule_chembl_id": SEED,
        "pref_name": "SOMETHING ELSE",
        "molecule_hierarchy": {"parent_chembl_id": PARENT},
        "molecule_structures": {"canonical_smiles": "c1ccccc1"},
    }
    with pytest.raises(DataContractError, match="expected"):
        normalise_molecule(payload, SEED, "DELAVIRDINE MESYLATE")


def test_the_release_fields_must_match_the_frozen_ones() -> None:
    assert validate_chembl_status(
        {"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2026-05-01", "status": "UP"}
    ) == {"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2026-05-01"}
    with pytest.raises(DataContractError, match="chembl_release_date"):
        validate_chembl_status(
            {"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2027-01-01", "status": "UP"}
        )
    with pytest.raises(DataContractError, match="status"):
        validate_chembl_status(
            {
                "chembl_db_version": "ChEMBL_37",
                "chembl_release_date": "2026-05-01",
                "status": "DOWN",
            }
        )


def test_pagination_refuses_a_total_that_moves_between_pages() -> None:
    calls = 0

    def drifting_fetcher(_url: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {
            "activities": [activity_row(calls)],
            "page_meta": {
                "next": "/chembl/api/data/activity.json?offset=1",
                "total_count": 2 if calls == 1 else 3,
            },
        }

    with pytest.raises(DataDownloadError, match="changed during pagination"):
        fetch_parent_activity_rows(PARENT, drifting_fetcher)


def test_pagination_refuses_a_repeated_page_and_excess_rows() -> None:
    def looping_fetcher(url: str) -> dict[str, Any]:
        return {
            "activities": [activity_row(1)],
            "page_meta": {"next": url, "total_count": 2},
        }

    with pytest.raises(DataDownloadError, match="repeated a page"):
        fetch_parent_activity_rows(PARENT, looping_fetcher)

    def excess_fetcher(_url: str) -> dict[str, Any]:
        return {
            "activities": [activity_row(1), activity_row(2)],
            "page_meta": {"next": None, "total_count": 1},
        }

    with pytest.raises(DataDownloadError, match="exceeded its declared total"):
        fetch_parent_activity_rows(PARENT, excess_fetcher)


def _fake_fetcher(requested: list[str]) -> Any:
    declared_parent = {
        "CHEMBL929": "CHEMBL593",
        "CHEMBL1026": "CHEMBL588",
        "CHEMBL433": "CHEMBL109",
        "CHEMBL690": "CHEMBL1144",
        "CHEMBL109745": "CHEMBL275835",
    }
    names = dict(COHORT_SEEDS)

    def fetcher(url: str) -> dict[str, Any]:
        requested.append(url)
        if url == CHEMBL_STATUS_URL:
            return {
                "chembl_db_version": "ChEMBL_37",
                "chembl_release_date": "2026-05-01",
                "status": "UP",
            }
        if "/molecule/" in url:
            molecule_id = url.rsplit("/", 1)[-1].removesuffix(".json")
            return {
                "molecule_chembl_id": molecule_id,
                "pref_name": names[molecule_id],
                "molecule_hierarchy": {
                    "parent_chembl_id": declared_parent.get(molecule_id, molecule_id)
                },
                "molecule_structures": {"canonical_smiles": "c1ccccc1"},
            }
        if "/assay.json" in url:
            return {"assays": [], "page_meta": {"total_count": 0}}
        query = parse_qs(urlparse(url).query)
        parent = query["parent_molecule_chembl_id"][0]
        return {
            "activities": [activity_row(1, parent_id=parent)],
            "page_meta": {"next": None, "total_count": 1},
        }

    return fetcher


def _unfreeze(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let the fake snapshot be written before it has a frozen byte length."""
    from aidd_commons.decision_unit_scope import data as data_module

    monkeypatch.setattr(data_module, "ARTIFACT_BYTE_LENGTHS", {})


def _freeze_fake_lengths(cache_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat the fake cache as if it were the frozen release."""
    from aidd_commons.decision_unit_scope import data as data_module

    lengths = {
        path.name: path.stat().st_size for path in sorted(cache_dir.glob("*.json"))
    }
    monkeypatch.setattr(data_module, "ARTIFACT_BYTE_LENGTHS", lengths)


def test_the_download_fetches_every_declared_artefact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _unfreeze(monkeypatch)
    requested: list[str] = []
    cache_dir = tmp_path / "cache"
    report = download_and_cache_snapshot(cache_dir, fetch_json=_fake_fetcher(requested))
    assert len(report.paths) == 13
    assert report.fetched == tuple(path.name for path in report.paths)
    assert report.reused == ()
    assert (cache_dir / "status.json").is_file()
    assert (cache_dir / "molecules.json").is_file()
    assert (cache_dir / f"activities-{PARENT}.json").is_file()
    assert (cache_dir / "assays.json").is_file()
    assert report.total_bytes == sum(path.stat().st_size for path in report.paths)


def test_a_cached_artefact_is_not_fetched_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _unfreeze(monkeypatch)
    requested: list[str] = []
    cache_dir = tmp_path / "cache"
    download_and_cache_snapshot(cache_dir, fetch_json=_fake_fetcher(requested))
    _freeze_fake_lengths(cache_dir, monkeypatch)
    first_round = len(requested)

    def status_only_fetcher(url: str) -> dict[str, Any]:
        if url == CHEMBL_STATUS_URL:
            return {
                "chembl_db_version": "ChEMBL_37",
                "chembl_release_date": "2026-05-01",
                "status": "UP",
            }
        raise AssertionError(f"a valid cache must not be fetched again: {url}")

    report = download_and_cache_snapshot(cache_dir, fetch_json=status_only_fetcher)
    assert len(requested) == first_round
    assert report.fetched == ("status.json",)
    assert len(report.reused) == 12


def test_a_corrupted_cached_artefact_is_refused_by_the_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _unfreeze(monkeypatch)
    requested: list[str] = []
    cache_dir = tmp_path / "cache"
    download_and_cache_snapshot(cache_dir, fetch_json=_fake_fetcher(requested))
    _freeze_fake_lengths(cache_dir, monkeypatch)
    path = cache_dir / f"activities-{PARENT}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["activities"].append(activity_row(2))
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DataContractError, match="frozen protocol declares"):
        load_cached_cohort(cache_dir)
