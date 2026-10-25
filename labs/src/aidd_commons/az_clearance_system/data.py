"""Fetch, validate and aggregate real ChEMBL intrinsic-clearance records.

All three assays read here belong to one ChEMBL dataset deposition
(document CHEMBL3301361), so unlike the CYP assay-system package this admits
by named assay, not by whole target. Nothing here imports, calls or modifies
chembl_egfr or cyp_assay_system.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from statistics import median
from typing import cast
from urllib.error import URLError
from urllib.parse import urlencode, urljoin
from urllib.request import urlopen

from rdkit import Chem

from .protocol import (
    ACTIVITY_FIELDS,
    CHEMBL_API_ROOT,
    CHEMBL_RELEASE_DATE,
    CHEMBL_STATUS_URL,
    CHEMBL_VERSION,
    DOCUMENT_CHEMBL_ID,
    SYSTEMS,
    VALUE_CONSISTENCY_TOLERANCE,
)

JsonObject = Mapping[str, object]
JsonFetcher = Callable[[str], JsonObject]


class DataContractError(ValueError):
    """Raised when a fetched or cached record violates the admission rule."""


class DataDownloadError(RuntimeError):
    """Raised when an official ChEMBL response cannot be obtained or cached."""


@dataclass(frozen=True)
class ParentClearanceRecord:
    assay_chembl_id: str
    parent_molecule_chembl_id: str
    canonical_smiles: str
    intrinsic_clearance: float
    standard_units: str
    activity_ids: tuple[int, ...]
    replicate_count: int
    value_range: float


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
class SystemDataset:
    assay_chembl_id: str
    records: tuple[ParentClearanceRecord, ...]
    audit: DataAudit


@dataclass(frozen=True)
class _EligibleRow:
    activity_id: int
    parent_id: str
    canonical_smiles: str
    clearance: float
    standard_units: str


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


def _exclusion_reason(row: JsonObject) -> str | None:
    if row.get("standard_type") != "CL":
        return "wrong_endpoint"
    if row.get("standard_relation") is not None:
        # This assay reports an exact intrinsic-clearance value with an empty
        # relation field; "<" and ">" mark a censored reading outside the
        # assay's quantifiable range (see the assay description), not noise.
        return "censored_value"
    if row.get("standard_flag") != 1:
        return "non_standard_activity"
    if row.get("potential_duplicate") != 0:
        return "potential_duplicate"
    if row.get("data_validity_comment") is not None:
        return "data_validity_comment"
    if row.get("standard_value") in (None, ""):
        return "missing_label"
    if row.get("canonical_smiles") in (None, ""):
        return "missing_structure"
    if row.get("molecule_chembl_id") != row.get("parent_molecule_chembl_id"):
        return "not_parent_structure"
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


def normalise_activity_rows(rows: Sequence[JsonObject], assay_chembl_id: str) -> SystemDataset:
    if assay_chembl_id not in SYSTEMS:
        raise DataContractError(f"undeclared assay: {assay_chembl_id}")

    exclusions: Counter[str] = Counter()
    seen_activity_ids: set[int] = set()
    eligible: list[_EligibleRow] = []

    for row in rows:
        activity_id = _required_int(row, "activity_id")
        if activity_id in seen_activity_ids:
            raise DataContractError(f"duplicate activity ID: {activity_id}")
        seen_activity_ids.add(activity_id)

        exclusion = _exclusion_reason(row)
        if exclusion is not None:
            exclusions[exclusion] += 1
            continue

        source_smiles = _required_string(row, "canonical_smiles")
        molecule = Chem.MolFromSmiles(source_smiles)
        if molecule is None or molecule.GetNumAtoms() == 0:
            raise DataContractError(f"activity {activity_id} has an invalid parent structure")
        canonical_smiles = Chem.MolToSmiles(molecule, isomericSmiles=True)

        standard_value = _finite_float(row, "standard_value")
        raw_value = _finite_float(row, "value")
        if abs(standard_value - raw_value) > VALUE_CONSISTENCY_TOLERANCE:
            raise DataContractError(
                f"activity {activity_id} standard_value does not agree with the raw value"
            )
        if standard_value <= 0.0:
            raise DataContractError(f"activity {activity_id} standard_value must be positive")
        standard_units = _required_string(row, "standard_units")

        eligible.append(
            _EligibleRow(
                activity_id=activity_id,
                parent_id=_required_string(row, "parent_molecule_chembl_id"),
                canonical_smiles=canonical_smiles,
                clearance=standard_value,
                standard_units=standard_units,
            )
        )

    grouped: dict[str, list[_EligibleRow]] = defaultdict(list)
    for eligible_row in eligible:
        grouped[eligible_row.parent_id].append(eligible_row)

    records: list[ParentClearanceRecord] = []
    duplicate_ranges: list[float] = []
    for parent_id, parent_rows in sorted(grouped.items()):
        structures = {row.canonical_smiles for row in parent_rows}
        if len(structures) != 1:
            raise DataContractError(f"parent {parent_id} maps to multiple canonical structures")
        units = {row.standard_units for row in parent_rows}
        if len(units) != 1:
            raise DataContractError(f"parent {parent_id} reports more than one unit")
        values = sorted(row.clearance for row in parent_rows)
        value_range = values[-1] - values[0]
        if len(parent_rows) > 1:
            duplicate_ranges.append(value_range)
        records.append(
            ParentClearanceRecord(
                assay_chembl_id=assay_chembl_id,
                parent_molecule_chembl_id=parent_id,
                canonical_smiles=next(iter(structures)),
                intrinsic_clearance=float(median(values)),
                standard_units=next(iter(units)),
                activity_ids=tuple(sorted(row.activity_id for row in parent_rows)),
                replicate_count=len(parent_rows),
                value_range=float(value_range),
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
    return SystemDataset(assay_chembl_id=assay_chembl_id, records=tuple(records), audit=audit)


def _activity_query_url(assay_chembl_id: str) -> str:
    query = urlencode(
        {
            "assay_chembl_id": assay_chembl_id,
            "document_chembl_id": DOCUMENT_CHEMBL_ID,
            "standard_type": "CL",
            "limit": 1000,
            "only": ",".join(ACTIVITY_FIELDS),
        }
    )
    return f"{CHEMBL_API_ROOT}/chembl/api/data/activity.json?{query}"


def fetch_assay_activity_rows(assay_chembl_id: str, fetcher: JsonFetcher) -> list[JsonObject]:
    url: str | None = _activity_query_url(assay_chembl_id)
    rows: list[JsonObject] = []
    expected_total: int | None = None
    visited_urls: set[str] = set()
    while url is not None:
        if url in visited_urls:
            raise DataDownloadError(f"ChEMBL pagination repeated a page for {assay_chembl_id}")
        visited_urls.add(url)
        payload = fetcher(url)
        raw_rows = payload.get("activities")
        page_meta = payload.get("page_meta")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataDownloadError(f"invalid ChEMBL activity page for {assay_chembl_id}")
        if not isinstance(page_meta, Mapping):
            raise DataDownloadError(f"missing ChEMBL page metadata for {assay_chembl_id}")
        total = page_meta.get("total_count")
        if not isinstance(total, int):
            raise DataDownloadError(f"invalid ChEMBL total count for {assay_chembl_id}")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise DataDownloadError(
                f"ChEMBL total count changed during pagination for {assay_chembl_id}"
            )
        rows.extend(cast(list[JsonObject], raw_rows))
        if len(rows) > expected_total:
            raise DataDownloadError(
                f"ChEMBL pagination exceeded its declared total count for {assay_chembl_id}"
            )
        next_page = page_meta.get("next")
        if next_page is None:
            url = None
        elif isinstance(next_page, str):
            url = urljoin(CHEMBL_API_ROOT, next_page)
        else:
            raise DataDownloadError(f"invalid ChEMBL next page for {assay_chembl_id}")
    if expected_total is None or len(rows) != expected_total:
        raise DataDownloadError(
            f"ChEMBL pagination returned {len(rows)} of {expected_total} rows for {assay_chembl_id}"
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


def download_and_cache_snapshot(
    cache_dir: Path, *, fetch_json: JsonFetcher | None = None
) -> tuple[Path, ...]:
    """Fetch the ChEMBL status and all three named assays' full activity pages
    once, and cache each as its own JSON file. Does not validate or aggregate
    anything; that happens when the cache is loaded, so a cache written under
    an older admission rule is re-checked under the current one rather than
    silently trusted."""
    fetcher = fetch_json or _fetch_json
    cache_dir.mkdir(parents=True, exist_ok=True)
    status = fetcher(CHEMBL_STATUS_URL)
    validate_chembl_status(status)
    status_path = cache_dir / "status.json"
    _write_json(status_path, status)
    paths = [status_path]
    for assay_id in sorted(SYSTEMS):
        rows = fetch_assay_activity_rows(assay_id, fetcher)
        path = cache_dir / f"activities-{assay_id}.json"
        _write_json(path, {"assay_chembl_id": assay_id, "activities": rows})
        paths.append(path)
    return tuple(paths)


def load_cached_systems(cache_dir: Path) -> dict[str, SystemDataset]:
    status_payload = _read_json(cache_dir / "status.json")
    validate_chembl_status(status_payload)
    datasets: dict[str, SystemDataset] = {}
    for assay_id in sorted(SYSTEMS):
        payload = _read_json(cache_dir / f"activities-{assay_id}.json")
        if payload.get("assay_chembl_id") != assay_id:
            raise DataContractError(f"cached activity payload has wrong assay ID: {assay_id}")
        raw_rows = payload.get("activities")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataContractError(f"cached activity rows are invalid for {assay_id}")
        datasets[assay_id] = normalise_activity_rows(cast(list[JsonObject], raw_rows), assay_id)
    return datasets
