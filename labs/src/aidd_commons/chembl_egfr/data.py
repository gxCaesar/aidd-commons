from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite, log10
from pathlib import Path
from statistics import median
from typing import cast
from urllib.error import URLError
from urllib.parse import urlencode, urljoin
from urllib.request import urlopen

from rdkit import Chem

from aidd_commons.chembl_egfr.protocol import (
    ASSAY_CONTRACTS,
    CHEMBL_API_ROOT,
    CHEMBL_RELEASE_DATE,
    CHEMBL_STATUS_URL,
    CHEMBL_VERSION,
    EXPECTED_PARENT_COUNTS,
    EXPECTED_QUERY_ROWS,
    EXPECTED_RETAINED_ROWS,
    PCHEMBL_CONSISTENCY_TOLERANCE,
    AssayContract,
)

JsonObject = Mapping[str, object]
JsonFetcher = Callable[[str], JsonObject]

ACTIVITY_FIELDS = (
    "activity_id",
    "assay_chembl_id",
    "canonical_smiles",
    "data_validity_comment",
    "molecule_chembl_id",
    "parent_molecule_chembl_id",
    "pchembl_value",
    "potential_duplicate",
    "standard_flag",
    "standard_relation",
    "standard_type",
    "standard_units",
    "standard_value",
)


class DataContractError(ValueError):
    """Raised when ChEMBL source data depart from the frozen task contract."""


class DataDownloadError(RuntimeError):
    """Raised when an official ChEMBL response cannot be obtained or cached."""


@dataclass(frozen=True)
class ParentActivityRecord:
    assay_chembl_id: str
    parent_molecule_chembl_id: str
    canonical_smiles: str
    target_pchembl: float
    activity_ids: tuple[int, ...]
    replicate_count: int
    pchembl_range: float


@dataclass(frozen=True)
class DataAudit:
    input_rows: int
    retained_rows: int
    parent_count: int
    duplicate_parent_count: int
    median_duplicate_range: float | None
    maximum_duplicate_range: float | None
    exclusion_counts: Mapping[str, int]


@dataclass(frozen=True)
class AssayDataset:
    assay_chembl_id: str
    records: tuple[ParentActivityRecord, ...]
    audit: DataAudit


@dataclass(frozen=True)
class CachedDatasets:
    status: Mapping[str, str]
    assay_metadata: Mapping[str, Mapping[str, object]]
    primary: AssayDataset
    external: AssayDataset


@dataclass(frozen=True)
class _EligibleRow:
    activity_id: int
    parent_id: str
    canonical_smiles: str
    pchembl_value: float


def validate_chembl_status(payload: JsonObject) -> dict[str, str]:
    expected = {
        "chembl_db_version": CHEMBL_VERSION,
        "chembl_release_date": CHEMBL_RELEASE_DATE,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise DataContractError(
                f"ChEMBL release field {field} differs from the frozen value {value}"
            )
    if payload.get("status") != "UP":
        raise DataContractError("ChEMBL status endpoint does not report UP")
    return expected


def validate_assay_metadata(payload: JsonObject, contract: AssayContract) -> dict[str, object]:
    expected: dict[str, object] = {
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
    for field, value in expected.items():
        if payload.get(field) != value:
            raise DataContractError(
                f"assay {contract.assay_chembl_id} field {field} differs from {value!r}"
            )
    return expected


def normalise_activity_rows(rows: Sequence[JsonObject], assay_chembl_id: str) -> AssayDataset:
    if not assay_chembl_id.strip():
        raise DataContractError("assay ChEMBL ID must not be empty")

    exclusions: Counter[str] = Counter()
    seen_activity_ids: set[int] = set()
    eligible: list[_EligibleRow] = []

    for row in rows:
        activity_id = _required_int(row, "activity_id")
        if activity_id in seen_activity_ids:
            raise DataContractError(f"duplicate activity ID: {activity_id}")
        seen_activity_ids.add(activity_id)

        if row.get("assay_chembl_id") != assay_chembl_id:
            raise DataContractError(f"activity {activity_id} belongs to a different assay")
        exclusion = _exclusion_reason(row)
        if exclusion is not None:
            exclusions[exclusion] += 1
            continue

        molecule_id = _required_string(row, "molecule_chembl_id")
        parent_id = _required_string(row, "parent_molecule_chembl_id")
        if molecule_id != parent_id:
            raise DataContractError(
                f"activity {activity_id} requires a separately fetched parent molecule structure"
            )

        source_smiles = _required_string(row, "canonical_smiles")
        molecule = Chem.MolFromSmiles(source_smiles)
        if molecule is None or molecule.GetNumAtoms() == 0:
            raise DataContractError(
                f"activity {activity_id} has an invalid parent molecule structure"
            )
        canonical_smiles = Chem.MolToSmiles(molecule, isomericSmiles=True)

        pchembl_value = _finite_float(row, "pchembl_value")
        standard_value = _finite_float(row, "standard_value")
        if standard_value <= 0.0:
            raise DataContractError(f"activity {activity_id} standard_value must be positive")
        if row.get("standard_units") != "nM":
            raise DataContractError(f"activity {activity_id} standard_units must be nM")
        expected_pchembl = 9.0 - log10(standard_value)
        pchembl_delta = round(abs(pchembl_value - expected_pchembl), 12)
        if pchembl_delta > PCHEMBL_CONSISTENCY_TOLERANCE:
            raise DataContractError(
                f"activity {activity_id} pChEMBL does not agree with standard_value in nM"
            )
        eligible.append(
            _EligibleRow(
                activity_id=activity_id,
                parent_id=parent_id,
                canonical_smiles=canonical_smiles,
                pchembl_value=pchembl_value,
            )
        )

    grouped: dict[str, list[_EligibleRow]] = defaultdict(list)
    for eligible_row in eligible:
        grouped[eligible_row.parent_id].append(eligible_row)

    records: list[ParentActivityRecord] = []
    duplicate_ranges: list[float] = []
    for parent_id, parent_rows in sorted(grouped.items()):
        structures = {row.canonical_smiles for row in parent_rows}
        if len(structures) != 1:
            raise DataContractError(f"parent {parent_id} maps to multiple canonical structures")
        labels = sorted(row.pchembl_value for row in parent_rows)
        label_range = labels[-1] - labels[0]
        if len(parent_rows) > 1:
            duplicate_ranges.append(label_range)
        records.append(
            ParentActivityRecord(
                assay_chembl_id=assay_chembl_id,
                parent_molecule_chembl_id=parent_id,
                canonical_smiles=next(iter(structures)),
                target_pchembl=float(median(labels)),
                activity_ids=tuple(sorted(row.activity_id for row in parent_rows)),
                replicate_count=len(parent_rows),
                pchembl_range=float(label_range),
            )
        )

    audit = DataAudit(
        input_rows=len(rows),
        retained_rows=len(eligible),
        parent_count=len(records),
        duplicate_parent_count=len(duplicate_ranges),
        median_duplicate_range=(float(median(duplicate_ranges)) if duplicate_ranges else None),
        maximum_duplicate_range=max(duplicate_ranges) if duplicate_ranges else None,
        exclusion_counts=dict(sorted(exclusions.items())),
    )
    return AssayDataset(
        assay_chembl_id=assay_chembl_id,
        records=tuple(records),
        audit=audit,
    )


def assert_parent_disjoint(primary: AssayDataset, external: AssayDataset) -> None:
    primary_ids = {record.parent_molecule_chembl_id for record in primary.records}
    external_ids = {record.parent_molecule_chembl_id for record in external.records}
    overlap = sorted(primary_ids & external_ids)
    if overlap:
        raise DataContractError(
            f"primary and external assays have parent-molecule overlap: {overlap[:5]}"
        )


def validate_frozen_dataset_counts(dataset: AssayDataset) -> None:
    assay_id = dataset.assay_chembl_id
    expected_query = EXPECTED_QUERY_ROWS.get(assay_id)
    expected_retained = EXPECTED_RETAINED_ROWS.get(assay_id)
    expected_parents = EXPECTED_PARENT_COUNTS.get(assay_id)
    if expected_query is None or expected_retained is None or expected_parents is None:
        raise DataContractError(f"assay is not in the frozen protocol: {assay_id}")
    observed = (
        dataset.audit.input_rows,
        dataset.audit.retained_rows,
        dataset.audit.parent_count,
    )
    expected = (expected_query, expected_retained, expected_parents)
    if observed != expected:
        raise DataContractError(
            f"assay {assay_id} counts differ from frozen query/retained/parent counts: "
            f"observed={observed}, expected={expected}"
        )


def download_frozen_snapshot(
    cache_dir: Path, fetch_json: JsonFetcher | None = None
) -> CachedDatasets:
    fetcher = fetch_json or _fetch_json
    cache_dir.mkdir(parents=True, exist_ok=True)

    status = fetcher(CHEMBL_STATUS_URL)
    validate_chembl_status(status)
    _write_json(cache_dir / "status.json", status)

    for assay_id, contract in sorted(ASSAY_CONTRACTS.items()):
        assay_url = f"{CHEMBL_API_ROOT}/chembl/api/data/assay/{assay_id}.json"
        metadata = fetcher(assay_url)
        validate_assay_metadata(metadata, contract)
        _write_json(cache_dir / f"assay-{assay_id}.json", metadata)

        rows = _fetch_activity_rows(assay_id, fetcher)
        _write_json(
            cache_dir / f"activities-{assay_id}.json",
            {
                "activities": rows,
                "assay_chembl_id": assay_id,
                "query_total_count": len(rows),
            },
        )

    return load_cached_frozen_datasets(cache_dir)


def load_cached_frozen_datasets(cache_dir: Path) -> CachedDatasets:
    status_payload = _read_json(cache_dir / "status.json")
    status = validate_chembl_status(status_payload)
    metadata: dict[str, Mapping[str, object]] = {}
    datasets: dict[str, AssayDataset] = {}
    for assay_id, contract in sorted(ASSAY_CONTRACTS.items()):
        assay_payload = _read_json(cache_dir / f"assay-{assay_id}.json")
        metadata[assay_id] = validate_assay_metadata(assay_payload, contract)
        activity_payload = _read_json(cache_dir / f"activities-{assay_id}.json")
        if activity_payload.get("assay_chembl_id") != assay_id:
            raise DataContractError(f"cached activity payload has wrong assay ID: {assay_id}")
        raw_rows = activity_payload.get("activities")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataContractError(f"cached activity rows are invalid for {assay_id}")
        if activity_payload.get("query_total_count") != len(raw_rows):
            raise DataContractError(f"cached activity count is invalid for {assay_id}")
        dataset = normalise_activity_rows(cast(list[JsonObject], raw_rows), assay_id)
        validate_frozen_dataset_counts(dataset)
        datasets[assay_id] = dataset

    primary = datasets[next(key for key in datasets if key == "CHEMBL5736995")]
    external = datasets[next(key for key in datasets if key == "CHEMBL3705421")]
    assert_parent_disjoint(primary, external)
    return CachedDatasets(
        status=status,
        assay_metadata=metadata,
        primary=primary,
        external=external,
    )


def _exclusion_reason(row: JsonObject) -> str | None:
    if row.get("standard_type") != "IC50":
        return "wrong_endpoint"
    if row.get("standard_relation") != "=":
        return "non_exact_relation"
    if row.get("standard_flag") != 1:
        return "non_standard_activity"
    if row.get("potential_duplicate") != 0:
        return "potential_duplicate"
    if row.get("data_validity_comment") is not None:
        return "data_validity_comment"
    if row.get("pchembl_value") in (None, ""):
        return "missing_label"
    if row.get("canonical_smiles") in (None, ""):
        return "missing_structure"
    return None


def _required_int(row: JsonObject, field: str) -> int:
    value = row.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise DataContractError(f"activity field {field} must be an integer")
    return value


def _required_string(row: JsonObject, field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DataContractError(f"activity field {field} must be a non-empty string")
    return value


def _finite_float(row: JsonObject, field: str) -> float:
    value = row.get(field)
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise DataContractError(f"activity field {field} must be numeric")
    try:
        parsed = float(value)
    except ValueError as error:
        raise DataContractError(f"activity field {field} must be numeric") from error
    if not isfinite(parsed):
        raise DataContractError(f"activity field {field} must be finite")
    return parsed


def _activity_query_url(assay_id: str) -> str:
    query = urlencode(
        {
            "assay_chembl_id": assay_id,
            "limit": 1000,
            "only": ",".join(ACTIVITY_FIELDS),
            "pchembl_value__isnull": "false",
            "potential_duplicate": 0,
            "standard_flag": 1,
            "standard_relation": "=",
            "standard_type": "IC50",
        }
    )
    return f"{CHEMBL_API_ROOT}/chembl/api/data/activity.json?{query}"


def _fetch_activity_rows(assay_id: str, fetcher: JsonFetcher) -> list[JsonObject]:
    url: str | None = _activity_query_url(assay_id)
    rows: list[JsonObject] = []
    expected_total: int | None = None
    visited_urls: set[str] = set()
    while url is not None:
        if url in visited_urls:
            raise DataDownloadError(f"ChEMBL pagination repeated a page for {assay_id}")
        visited_urls.add(url)
        payload = fetcher(url)
        raw_rows = payload.get("activities")
        page_meta = payload.get("page_meta")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataDownloadError(f"invalid ChEMBL activity page for {assay_id}")
        if not isinstance(page_meta, Mapping):
            raise DataDownloadError(f"missing ChEMBL page metadata for {assay_id}")
        total = page_meta.get("total_count")
        if not isinstance(total, int):
            raise DataDownloadError(f"invalid ChEMBL total count for {assay_id}")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise DataDownloadError(f"ChEMBL total count changed during pagination for {assay_id}")
        rows.extend(cast(list[JsonObject], raw_rows))
        if len(rows) > expected_total:
            raise DataDownloadError(
                f"ChEMBL pagination exceeded its declared total count for {assay_id}"
            )
        next_page = page_meta.get("next")
        if next_page is None:
            url = None
        elif isinstance(next_page, str):
            url = urljoin(CHEMBL_API_ROOT, next_page)
        else:
            raise DataDownloadError(f"invalid ChEMBL next page for {assay_id}")
    if expected_total is None or len(rows) != expected_total:
        raise DataDownloadError(
            f"ChEMBL pagination returned {len(rows)} of {expected_total} rows for {assay_id}"
        )
    return sorted(rows, key=lambda row: _required_int(row, "activity_id"))


def _fetch_json(url: str) -> JsonObject:
    try:
        with urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataDownloadError(
            f"could not fetch official ChEMBL JSON from {url}: {error}"
        ) from error
    if not isinstance(payload, Mapping):
        raise DataDownloadError(f"official ChEMBL response is not a JSON object: {url}")
    return cast(JsonObject, payload)


def _read_json(path: Path) -> JsonObject:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataDownloadError(f"could not read cached ChEMBL JSON {path}: {error}") from error
    if not isinstance(payload, Mapping):
        raise DataContractError(f"cached ChEMBL payload is not a JSON object: {path}")
    return cast(JsonObject, payload)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
