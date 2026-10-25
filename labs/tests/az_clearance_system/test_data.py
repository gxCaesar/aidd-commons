from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from aidd_commons.az_clearance_system.data import (
    DataContractError,
    DataDownloadError,
    download_and_cache_snapshot,
    fetch_assay_activity_rows,
    load_cached_systems,
    normalise_activity_rows,
    validate_chembl_status,
)
from aidd_commons.az_clearance_system.protocol import CHEMBL_STATUS_URL, DOCUMENT_CHEMBL_ID, SYSTEMS

ASSAY_A, ASSAY_B, ASSAY_C = sorted(SYSTEMS)


def activity_row(
    activity_id: int,
    *,
    parent_id: str = "CHEMBL_FIXTURE_1",
    molecule_id: str | None = None,
    smiles: str | None = "c1ccccc1",
    standard_relation: str | None = None,
    standard_value: str = "12.5",
    value: str | None = None,
    standard_units: str = "mL.min-1.g-1",
    assay_chembl_id: str = ASSAY_A,
) -> dict[str, object]:
    return {
        "activity_id": activity_id,
        "assay_chembl_id": assay_chembl_id,
        "document_chembl_id": DOCUMENT_CHEMBL_ID,
        "canonical_smiles": smiles,
        "data_validity_comment": None,
        "molecule_chembl_id": molecule_id if molecule_id is not None else parent_id,
        "parent_molecule_chembl_id": parent_id,
        "potential_duplicate": 0,
        "standard_flag": 1,
        "standard_relation": standard_relation,
        "standard_type": "CL",
        "standard_units": standard_units,
        "standard_value": standard_value,
        "value": value if value is not None else standard_value,
        "units": standard_units,
    }


def test_admission_rule_admits_exact_values_and_excludes_censored_ones() -> None:
    rows = [
        activity_row(1, standard_value="12.5"),
        activity_row(2, parent_id="CHEMBL_FIXTURE_2", standard_value="30.0"),
    ]
    mutations: tuple[tuple[str, object], ...] = (
        ("standard_type", "IC50"),
        ("standard_flag", 0),
        ("potential_duplicate", 1),
        ("data_validity_comment", "Outside typical range"),
        ("standard_value", None),
        ("canonical_smiles", None),
    )
    for offset, (field, value) in enumerate(mutations, start=10):
        invalid = activity_row(offset, parent_id=f"CHEMBL_FILTERED_{offset}")
        invalid[field] = value
        rows.append(invalid)
    censored = activity_row(20, parent_id="CHEMBL_FIXTURE_3", standard_relation="<")
    rows.append(censored)
    child_row = activity_row(21, parent_id="CHEMBL_FIXTURE_4", molecule_id="CHEMBL_CHILD")
    rows.append(child_row)

    dataset = normalise_activity_rows(rows, ASSAY_A)

    assert dataset.assay_chembl_id == ASSAY_A
    assert dataset.audit.input_rows == 10
    assert dataset.audit.retained_rows == 2
    assert dataset.audit.parent_count == 2
    assert dataset.audit.exclusion_counts == {
        "censored_value": 1,
        "data_validity_comment": 1,
        "missing_label": 1,
        "missing_structure": 1,
        "non_standard_activity": 1,
        "not_parent_structure": 1,
        "potential_duplicate": 1,
        "wrong_endpoint": 1,
    }
    first = next(r for r in dataset.records if r.parent_molecule_chembl_id == "CHEMBL_FIXTURE_1")
    assert first.intrinsic_clearance == pytest.approx(12.5)
    assert first.replicate_count == 1
    assert first.standard_units == "mL.min-1.g-1"


def test_admission_rule_rejects_undeclared_assay() -> None:
    with pytest.raises(DataContractError, match="undeclared assay"):
        normalise_activity_rows([activity_row(1)], "CHEMBL_NOT_AN_ASSAY")


def test_admission_rule_rejects_value_inconsistent_with_standard_value() -> None:
    accepted = normalise_activity_rows(
        [activity_row(1, standard_value="12.5", value="12.5")], ASSAY_A
    )
    assert accepted.records[0].intrinsic_clearance == pytest.approx(12.5)

    with pytest.raises(DataContractError, match="does not agree with the raw value"):
        normalise_activity_rows([activity_row(1, standard_value="12.5", value="99.0")], ASSAY_A)


def test_admission_rule_rejects_duplicate_activity_ids() -> None:
    with pytest.raises(DataContractError, match="duplicate activity ID"):
        normalise_activity_rows([activity_row(1), activity_row(1)], ASSAY_A)


def test_admission_rule_rejects_one_parent_with_two_structures() -> None:
    with pytest.raises(DataContractError, match="multiple canonical structures"):
        normalise_activity_rows([activity_row(1), activity_row(2, smiles="C1CCCCC1")], ASSAY_A)


def test_admission_rule_rejects_one_parent_with_two_units() -> None:
    with pytest.raises(DataContractError, match="more than one unit"):
        normalise_activity_rows(
            [
                activity_row(1, standard_units="mL.min-1.g-1"),
                activity_row(2, standard_units="uL.min-1.(10^6cells)-1"),
            ],
            ASSAY_A,
        )


def test_median_aggregation_over_repeated_admitted_activities() -> None:
    dataset = normalise_activity_rows(
        [
            activity_row(1, standard_value="10.0", value="10.0"),
            activity_row(2, standard_value="30.0", value="30.0"),
        ],
        ASSAY_A,
    )
    record = dataset.records[0]
    assert record.replicate_count == 2
    assert record.intrinsic_clearance == pytest.approx(20.0)
    assert record.value_range == pytest.approx(20.0)
    assert dataset.audit.duplicate_parent_count == 1


def test_chembl_status_must_match_the_frozen_release() -> None:
    assert validate_chembl_status(
        {"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2026-05-01", "status": "UP"}
    ) == {"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2026-05-01"}
    with pytest.raises(DataContractError, match="chembl_release_date"):
        validate_chembl_status(
            {"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2027-01-01", "status": "UP"}
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
        fetch_assay_activity_rows(ASSAY_A, drifting_fetcher)


def test_download_snapshot_follows_pagination_and_reloads_a_validated_cache(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "az-cache"
    rows_by_assay: dict[str, list[dict[str, object]]] = {}
    for assay_offset, assay_id in enumerate((ASSAY_A, ASSAY_B, ASSAY_C), start=1):
        parent_id = f"CHEMBL_PARENT_{assay_offset}"
        rows_by_assay[assay_id] = [
            activity_row(
                assay_offset * 100 + row_offset,
                parent_id=parent_id,
                standard_value=str(10.0 + row_offset),
                value=str(10.0 + row_offset),
                assay_chembl_id=assay_id,
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
        assay_id = query["assay_chembl_id"][0]
        offset = int(query.get("offset", ["0"])[0])
        next_page = None
        if offset == 0:
            next_page = f"/chembl/api/data/activity.json?assay_chembl_id={assay_id}&offset=1"
        return {
            "activities": [rows_by_assay[assay_id][offset]],
            "page_meta": {"next": next_page, "total_count": 2},
        }

    paths = download_and_cache_snapshot(cache_dir, fetch_json=fake_fetcher)
    assert len(paths) == 4
    assert len([url for url in requested_urls if "activity.json" in url]) == 6

    datasets = load_cached_systems(cache_dir)
    for assay_id in SYSTEMS:
        assert datasets[assay_id].audit.input_rows == 2
        assert datasets[assay_id].audit.parent_count == 1
