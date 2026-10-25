from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from aidd_commons.chembl_egfr.data import (
    DataContractError,
    DataDownloadError,
    _fetch_activity_rows,
    assert_parent_disjoint,
    download_frozen_snapshot,
    normalise_activity_rows,
    validate_assay_metadata,
    validate_chembl_status,
)
from aidd_commons.chembl_egfr.protocol import (
    ASSAY_CONTRACTS,
    CHEMBL_STATUS_URL,
    EXPECTED_PARENT_COUNTS,
    EXPECTED_QUERY_ROWS,
    EXPECTED_RETAINED_ROWS,
    EXTERNAL_ASSAY_ID,
    PRIMARY_ASSAY_ID,
)


def activity_row(
    activity_id: int,
    *,
    parent_id: str = "CHEMBL_FIXTURE_1",
    smiles: str | None = "c1ccccc1",
    pchembl: str | None = "8.00",
    standard_value: str = "10.0",
) -> dict[str, object]:
    return {
        "activity_id": activity_id,
        "assay_chembl_id": "CHEMBL5736995",
        "canonical_smiles": smiles,
        "data_validity_comment": None,
        "molecule_chembl_id": parent_id,
        "parent_molecule_chembl_id": parent_id,
        "pchembl_value": pchembl,
        "potential_duplicate": 0,
        "standard_flag": 1,
        "standard_relation": "=",
        "standard_type": "IC50",
        "standard_units": "nM",
        "standard_value": standard_value,
    }


def assay_metadata(assay_id: str) -> dict[str, object]:
    contract = ASSAY_CONTRACTS[assay_id]
    return {
        "assay_chembl_id": contract.assay_chembl_id,
        "assay_organism": contract.organism,
        "assay_tax_id": contract.tax_id,
        "assay_type": contract.assay_type,
        "bao_format": contract.bao_format,
        "confidence_score": contract.confidence_score,
        "document_chembl_id": contract.document_chembl_id,
        "relationship_type": contract.relationship_type,
        "target_chembl_id": contract.target_chembl_id,
        "variant_sequence": contract.variant_sequence,
    }


def test_activity_contract_filters_rows_and_aggregates_parent_labels_by_median() -> None:
    rows = [
        activity_row(1, pchembl="7.00", standard_value="100.0"),
        activity_row(
            2,
            smiles="C1=CC=CC=C1",
            pchembl="9.00",
            standard_value="1.0",
        ),
        activity_row(
            3,
            parent_id="CHEMBL_FIXTURE_2",
            smiles="C1CCCCC1",
            pchembl="8.00",
            standard_value="10.0",
        ),
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

    dataset = normalise_activity_rows(rows, assay_chembl_id="CHEMBL5736995")

    assert dataset.audit.input_rows == 10
    assert dataset.audit.retained_rows == 3
    assert dataset.audit.parent_count == 2
    assert dataset.audit.exclusion_counts == {
        "data_validity_comment": 1,
        "missing_label": 1,
        "missing_structure": 1,
        "non_exact_relation": 1,
        "non_standard_activity": 1,
        "potential_duplicate": 1,
        "wrong_endpoint": 1,
    }
    first = dataset.records[0]
    assert first.parent_molecule_chembl_id == "CHEMBL_FIXTURE_1"
    assert first.activity_ids == (1, 2)
    assert first.replicate_count == 2
    assert first.target_pchembl == pytest.approx(8.0)
    assert first.pchembl_range == pytest.approx(2.0)
    assert first.canonical_smiles == "c1ccccc1"


def test_activity_contract_rejects_inconsistent_label_identity_and_source_ids() -> None:
    accepted_rounding = activity_row(0, pchembl="7.011", standard_value="100.0")
    assert normalise_activity_rows([accepted_rounding], assay_chembl_id="CHEMBL5736995").records[
        0
    ].target_pchembl == pytest.approx(7.011)

    rejected_rounding = activity_row(1, pchembl="7.012", standard_value="100.0")
    with pytest.raises(DataContractError, match="pChEMBL.*standard_value"):
        normalise_activity_rows([rejected_rounding], assay_chembl_id="CHEMBL5736995")

    inconsistent_label = activity_row(1, pchembl="8.00", standard_value="100.0")
    with pytest.raises(DataContractError, match="pChEMBL.*standard_value"):
        normalise_activity_rows([inconsistent_label], assay_chembl_id="CHEMBL5736995")

    child = activity_row(2)
    child["molecule_chembl_id"] = "CHEMBL_CHILD"
    with pytest.raises(DataContractError, match="parent molecule structure"):
        normalise_activity_rows([child], assay_chembl_id="CHEMBL5736995")

    with pytest.raises(DataContractError, match="duplicate activity ID"):
        normalise_activity_rows(
            [activity_row(3), activity_row(3)],
            assay_chembl_id="CHEMBL5736995",
        )


def test_activity_contract_rejects_multiple_structures_for_one_parent() -> None:
    with pytest.raises(DataContractError, match="multiple canonical structures"):
        normalise_activity_rows(
            [activity_row(1), activity_row(2, smiles="C1CCCCC1")],
            assay_chembl_id="CHEMBL5736995",
        )


def test_release_and_assay_metadata_are_checked_at_the_source_boundary() -> None:
    assert validate_chembl_status(
        {
            "chembl_db_version": "ChEMBL_37",
            "chembl_release_date": "2026-05-01",
            "status": "UP",
        }
    ) == {"chembl_db_version": "ChEMBL_37", "chembl_release_date": "2026-05-01"}

    primary = ASSAY_CONTRACTS["CHEMBL5736995"]
    metadata = {
        "assay_chembl_id": primary.assay_chembl_id,
        "assay_organism": primary.organism,
        "assay_tax_id": primary.tax_id,
        "assay_type": primary.assay_type,
        "bao_format": primary.bao_format,
        "confidence_score": primary.confidence_score,
        "document_chembl_id": primary.document_chembl_id,
        "relationship_type": primary.relationship_type,
        "target_chembl_id": primary.target_chembl_id,
        "variant_sequence": None,
    }
    assert validate_assay_metadata(metadata, primary)["assay_chembl_id"] == primary.assay_chembl_id

    wrong = deepcopy(metadata)
    wrong["target_chembl_id"] = "CHEMBL_WRONG"
    with pytest.raises(DataContractError, match="target_chembl_id"):
        validate_assay_metadata(wrong, primary)

    with pytest.raises(DataContractError, match="release"):
        validate_chembl_status(
            {
                "chembl_db_version": "ChEMBL_38",
                "chembl_release_date": "2027-01-01",
                "status": "UP",
            }
        )


def test_primary_and_replication_parent_sets_must_be_disjoint() -> None:
    primary = normalise_activity_rows([activity_row(1)], "CHEMBL5736995")
    external_row = activity_row(2)
    external_row["assay_chembl_id"] = "CHEMBL3705421"
    external = normalise_activity_rows([external_row], "CHEMBL3705421")

    with pytest.raises(DataContractError, match="parent-molecule overlap"):
        assert_parent_disjoint(primary, external)


def test_download_snapshot_follows_pagination_and_reloads_validated_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_dir = tmp_path / "chembl-cache"
    rows_by_assay: dict[str, list[dict[str, object]]] = {}
    for assay_offset, assay_id in enumerate((PRIMARY_ASSAY_ID, EXTERNAL_ASSAY_ID), start=1):
        parent_id = f"CHEMBL_PARENT_{assay_offset}"
        assay_rows = [
            activity_row(
                assay_offset * 100 + row_offset,
                parent_id=parent_id,
                pchembl=str(7.0 + row_offset),
                standard_value=str(10 ** (2 - row_offset)),
            )
            for row_offset in range(2)
        ]
        for row in assay_rows:
            row["assay_chembl_id"] = assay_id
        rows_by_assay[assay_id] = assay_rows
        monkeypatch.setitem(EXPECTED_QUERY_ROWS, assay_id, 2)
        monkeypatch.setitem(EXPECTED_RETAINED_ROWS, assay_id, 2)
        monkeypatch.setitem(EXPECTED_PARENT_COUNTS, assay_id, 1)

    requested_urls: list[str] = []

    def fake_fetcher(url: str) -> dict[str, object]:
        requested_urls.append(url)
        if url == CHEMBL_STATUS_URL:
            return {
                "chembl_db_version": "ChEMBL_37",
                "chembl_release_date": "2026-05-01",
                "status": "UP",
            }
        if "/assay/" in url:
            assay_id = url.rsplit("/", 1)[-1].removesuffix(".json")
            return assay_metadata(assay_id)

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

    datasets = download_frozen_snapshot(cache_dir, fake_fetcher)

    assert datasets.primary.audit.input_rows == 2
    assert datasets.primary.audit.parent_count == 1
    assert datasets.external.audit.input_rows == 2
    assert datasets.external.audit.parent_count == 1
    assert len([url for url in requested_urls if "activity.json" in url]) == 4
    assert (cache_dir / f"activities-{PRIMARY_ASSAY_ID}.json").is_file()
    assert (cache_dir / f"activities-{EXTERNAL_ASSAY_ID}.json").is_file()


def test_activity_pagination_rejects_a_total_that_changes_between_pages() -> None:
    calls = 0

    def drifting_fetcher(_url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        row = activity_row(calls)
        if calls == 1:
            return {
                "activities": [row],
                "page_meta": {
                    "next": "/chembl/api/data/activity.json?offset=1",
                    "total_count": 2,
                },
            }
        return {
            "activities": [row],
            "page_meta": {"next": None, "total_count": 3},
        }

    with pytest.raises(DataDownloadError, match="changed during pagination"):
        _fetch_activity_rows(PRIMARY_ASSAY_ID, drifting_fetcher)


def test_activity_pagination_rejects_repeated_pages_and_excess_rows() -> None:
    first_url: str | None = None

    def looping_fetcher(url: str) -> dict[str, object]:
        nonlocal first_url
        first_url = first_url or url
        return {
            "activities": [activity_row(1)],
            "page_meta": {"next": first_url, "total_count": 2},
        }

    with pytest.raises(DataDownloadError, match="repeated a page"):
        _fetch_activity_rows(PRIMARY_ASSAY_ID, looping_fetcher)

    def excess_fetcher(_url: str) -> dict[str, object]:
        return {
            "activities": [activity_row(1), activity_row(2)],
            "page_meta": {"next": None, "total_count": 1},
        }

    with pytest.raises(DataDownloadError, match="exceeded its declared total"):
        _fetch_activity_rows(PRIMARY_ASSAY_ID, excess_fetcher)
