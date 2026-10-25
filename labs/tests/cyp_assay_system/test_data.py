from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from aidd_commons.cyp_assay_system.data import (
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
    fetch_target_activity_rows,
    load_cached_targets,
    normalise_activity_rows,
    validate_chembl_status,
)
from aidd_commons.cyp_assay_system.protocol import CHEMBL_STATUS_URL, TARGETS

PRIMARY, SECONDARY = TARGETS


def activity_row(
    activity_id: int,
    *,
    parent_id: str = "CHEMBL_FIXTURE_1",
    molecule_id: str | None = None,
    smiles: str | None = "c1ccccc1",
    pchembl: str | None = "8.00",
    standard_value: str = "10.0",
    assay_chembl_id: str = "CHEMBL_ASSAY_1",
    document_chembl_id: str = "CHEMBL_DOC_1",
) -> dict[str, object]:
    return {
        "activity_id": activity_id,
        "assay_chembl_id": assay_chembl_id,
        "document_chembl_id": document_chembl_id,
        "canonical_smiles": smiles,
        "data_validity_comment": None,
        "molecule_chembl_id": molecule_id if molecule_id is not None else parent_id,
        "parent_molecule_chembl_id": parent_id,
        "pchembl_value": pchembl,
        "potential_duplicate": 0,
        "standard_flag": 1,
        "standard_relation": "=",
        "standard_type": "IC50",
        "standard_units": "nM",
        "standard_value": standard_value,
    }


def test_admission_rule_filters_every_declared_reason_and_aggregates_by_median() -> None:
    rows = [
        activity_row(1, pchembl="7.00", standard_value="100.0"),
        activity_row(2, smiles="C1=CC=CC=C1", pchembl="9.00", standard_value="1.0"),
        activity_row(3, parent_id="CHEMBL_FIXTURE_2", smiles="C1CCCCC1"),
    ]
    mutations: tuple[tuple[str, object], ...] = (
        ("standard_type", "Ki"),
        ("standard_relation", ">"),
        ("standard_flag", 0),
        ("potential_duplicate", 1),
        ("data_validity_comment", "Outside typical range"),
        ("pchembl_value", None),
        ("canonical_smiles", None),
    )
    for offset, (field, value) in enumerate(mutations, start=10):
        invalid = activity_row(offset, parent_id=f"CHEMBL_FILTERED_{offset}")
        invalid[field] = value
        rows.append(invalid)
    child_row = activity_row(20, parent_id="CHEMBL_FIXTURE_3", molecule_id="CHEMBL_CHILD")
    rows.append(child_row)

    dataset = normalise_activity_rows(rows, PRIMARY)

    assert dataset.target_chembl_id == PRIMARY
    assert dataset.audit.input_rows == 11
    assert dataset.audit.retained_rows == 3
    assert dataset.audit.parent_count == 2
    assert dataset.audit.exclusion_counts == {
        "data_validity_comment": 1,
        "missing_label": 1,
        "missing_structure": 1,
        "non_exact_relation": 1,
        "non_standard_activity": 1,
        "not_parent_structure": 1,
        "potential_duplicate": 1,
        "wrong_endpoint": 1,
    }
    first = next(r for r in dataset.records if r.parent_molecule_chembl_id == "CHEMBL_FIXTURE_1")
    assert first.activity_ids == (1, 2)
    assert first.replicate_count == 2
    assert first.target_pchembl == pytest.approx(8.0)
    assert first.pchembl_range == pytest.approx(2.0)
    assert first.assay_chembl_ids == ("CHEMBL_ASSAY_1",)
    assert first.document_chembl_ids == ("CHEMBL_DOC_1",)


def test_admission_rule_rejects_undeclared_target() -> None:
    with pytest.raises(DataContractError, match="undeclared target"):
        normalise_activity_rows([activity_row(1)], "CHEMBL_NOT_A_TARGET")


def test_admission_rule_rejects_pchembl_inconsistent_with_standard_value() -> None:
    accepted = normalise_activity_rows(
        [activity_row(1, pchembl="7.011", standard_value="100.0")], PRIMARY
    )
    assert accepted.records[0].target_pchembl == pytest.approx(7.011)

    with pytest.raises(DataContractError, match="pChEMBL"):
        normalise_activity_rows([activity_row(1, pchembl="7.012", standard_value="100.0")], PRIMARY)
    with pytest.raises(DataContractError, match="pChEMBL"):
        normalise_activity_rows([activity_row(1, pchembl="8.00", standard_value="100.0")], PRIMARY)


def test_admission_rule_rejects_duplicate_activity_ids() -> None:
    with pytest.raises(DataContractError, match="duplicate activity ID"):
        normalise_activity_rows([activity_row(1), activity_row(1)], PRIMARY)


def test_admission_rule_rejects_one_parent_with_two_structures() -> None:
    with pytest.raises(DataContractError, match="multiple canonical structures"):
        normalise_activity_rows([activity_row(1), activity_row(2, smiles="C1CCCCC1")], PRIMARY)


def test_chembl_status_must_match_the_frozen_release() -> None:
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


def test_activity_pagination_rejects_a_total_that_changes_between_pages() -> None:
    calls = 0

    def drifting_fetcher(_url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        row = activity_row(calls)
        if calls == 1:
            return {
                "activities": [row],
                "page_meta": {"next": "/chembl/api/data/activity.json?offset=1", "total_count": 2},
            }
        return {"activities": [row], "page_meta": {"next": None, "total_count": 3}}

    with pytest.raises(DataDownloadError, match="changed during pagination"):
        fetch_target_activity_rows(PRIMARY, drifting_fetcher)


def test_activity_pagination_rejects_repeated_pages_and_excess_rows() -> None:
    first_url: str | None = None

    def looping_fetcher(url: str) -> dict[str, object]:
        nonlocal first_url
        first_url = first_url or url
        return {"activities": [activity_row(1)], "page_meta": {"next": first_url, "total_count": 2}}

    with pytest.raises(DataDownloadError, match="repeated a page"):
        fetch_target_activity_rows(PRIMARY, looping_fetcher)

    def excess_fetcher(_url: str) -> dict[str, object]:
        return {
            "activities": [activity_row(1), activity_row(2)],
            "page_meta": {"next": None, "total_count": 1},
        }

    with pytest.raises(DataDownloadError, match="exceeded its declared total"):
        fetch_target_activity_rows(PRIMARY, excess_fetcher)


def test_download_snapshot_follows_pagination_and_reloads_a_validated_cache(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "cyp-cache"
    rows_by_target: dict[str, list[dict[str, object]]] = {}
    for target_offset, target_id in enumerate(sorted(TARGETS), start=1):
        parent_id = f"CHEMBL_PARENT_{target_offset}"
        rows_by_target[target_id] = [
            activity_row(
                target_offset * 100 + row_offset,
                parent_id=parent_id,
                pchembl=str(7.0 + row_offset),
                standard_value=str(10 ** (2 - row_offset)),
            )
            for row_offset in range(2)
        ]

    requested_urls: list[str] = []

    def fake_fetcher(url: str) -> dict[str, object]:
        requested_urls.append(url)
        if url == CHEMBL_STATUS_URL:
            return {
                "chembl_db_version": "ChEMBL_37",
                "chembl_release_date": "2026-05-01",
                "status": "UP",
            }
        query = parse_qs(urlparse(url).query)
        target_id = query["target_chembl_id"][0]
        offset = int(query.get("offset", ["0"])[0])
        next_page = None
        if offset == 0:
            next_page = f"/chembl/api/data/activity.json?target_chembl_id={target_id}&offset=1"
        return {
            "activities": [rows_by_target[target_id][offset]],
            "page_meta": {"next": next_page, "total_count": 2},
        }

    paths = download_and_cache_snapshot(cache_dir, fetch_json=fake_fetcher)
    assert len(paths) == 3
    assert len([url for url in requested_urls if "activity.json" in url]) == 4

    datasets = load_cached_targets(cache_dir)
    for target_id in TARGETS:
        assert datasets[target_id].audit.input_rows == 2
        assert datasets[target_id].audit.parent_count == 1


def test_load_cached_targets_rejects_a_release_that_no_longer_matches(tmp_path: Path) -> None:
    cache_dir = tmp_path / "stale-cache"

    def fake_fetcher(url: str) -> dict[str, object]:
        if url == CHEMBL_STATUS_URL:
            return {
                "chembl_db_version": "ChEMBL_37",
                "chembl_release_date": "2026-05-01",
                "status": "UP",
            }
        return {"activities": [], "page_meta": {"next": None, "total_count": 0}}

    download_and_cache_snapshot(cache_dir, fetch_json=fake_fetcher)
    status_path = cache_dir / "status.json"
    status_path.write_text(
        status_path.read_text(encoding="utf-8").replace("2026-05-01", "2027-01-01"),
        encoding="utf-8",
    )
    with pytest.raises(DataContractError, match="chembl_release_date"):
        load_cached_targets(cache_dir)
