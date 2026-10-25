"""Fetch, validate and aggregate real ChEMBL CYP450 inhibition records.

Reuses the admission rule this project's `chembl_egfr` package already
established (see `protocol.py`), applied here to two full targets rather than
two named assays, because a single target's IC50 records are themselves spread
across many independent assays and documents; that spread is part of what this
lab teaches. Nothing here imports, calls or modifies `chembl_egfr`.
"""

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

from .protocol import (
    ACTIVITY_FIELDS,
    CHEMBL_API_ROOT,
    CHEMBL_RELEASE_DATE,
    CHEMBL_STATUS_URL,
    CHEMBL_VERSION,
    PCHEMBL_CONSISTENCY_TOLERANCE,
    TARGETS,
)

JsonObject = Mapping[str, object]
JsonFetcher = Callable[[str], JsonObject]


class DataContractError(ValueError):
    """Raised when a fetched or cached record violates the admission rule."""


class DataDownloadError(RuntimeError):
    """Raised when an official ChEMBL response cannot be obtained or cached."""


@dataclass(frozen=True)
class ParentActivityRecord:
    target_chembl_id: str
    parent_molecule_chembl_id: str
    canonical_smiles: str
    target_pchembl: float
    activity_ids: tuple[int, ...]
    assay_chembl_ids: tuple[str, ...]
    document_chembl_ids: tuple[str, ...]
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
class TargetDataset:
    target_chembl_id: str
    records: tuple[ParentActivityRecord, ...]
    audit: DataAudit


@dataclass(frozen=True)
class _EligibleRow:
    activity_id: int
    parent_id: str
    canonical_smiles: str
    pchembl_value: float
    assay_chembl_id: str
    document_chembl_id: str


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


def normalise_activity_rows(rows: Sequence[JsonObject], target_chembl_id: str) -> TargetDataset:
    if target_chembl_id not in TARGETS:
        raise DataContractError(f"undeclared target: {target_chembl_id}")

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
                parent_id=_required_string(row, "parent_molecule_chembl_id"),
                canonical_smiles=canonical_smiles,
                pchembl_value=pchembl_value,
                assay_chembl_id=_required_string(row, "assay_chembl_id"),
                document_chembl_id=_required_string(row, "document_chembl_id"),
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
                target_chembl_id=target_chembl_id,
                parent_molecule_chembl_id=parent_id,
                canonical_smiles=next(iter(structures)),
                target_pchembl=float(median(labels)),
                activity_ids=tuple(sorted(row.activity_id for row in parent_rows)),
                assay_chembl_ids=tuple(sorted({row.assay_chembl_id for row in parent_rows})),
                document_chembl_ids=tuple(sorted({row.document_chembl_id for row in parent_rows})),
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
    return TargetDataset(target_chembl_id=target_chembl_id, records=tuple(records), audit=audit)


def _activity_query_url(target_chembl_id: str) -> str:
    query = urlencode(
        {
            "target_chembl_id": target_chembl_id,
            "limit": 1000,
            "only": ",".join(ACTIVITY_FIELDS),
            "standard_relation": "=",
            "standard_type": "IC50",
            "standard_units": "nM",
        }
    )
    return f"{CHEMBL_API_ROOT}/chembl/api/data/activity.json?{query}"


def fetch_target_activity_rows(target_chembl_id: str, fetcher: JsonFetcher) -> list[JsonObject]:
    url: str | None = _activity_query_url(target_chembl_id)
    rows: list[JsonObject] = []
    expected_total: int | None = None
    visited_urls: set[str] = set()
    while url is not None:
        if url in visited_urls:
            raise DataDownloadError(f"ChEMBL pagination repeated a page for {target_chembl_id}")
        visited_urls.add(url)
        payload = fetcher(url)
        raw_rows = payload.get("activities")
        page_meta = payload.get("page_meta")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataDownloadError(f"invalid ChEMBL activity page for {target_chembl_id}")
        if not isinstance(page_meta, Mapping):
            raise DataDownloadError(f"missing ChEMBL page metadata for {target_chembl_id}")
        total = page_meta.get("total_count")
        if not isinstance(total, int):
            raise DataDownloadError(f"invalid ChEMBL total count for {target_chembl_id}")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise DataDownloadError(
                f"ChEMBL total count changed during pagination for {target_chembl_id}"
            )
        rows.extend(cast(list[JsonObject], raw_rows))
        if len(rows) > expected_total:
            raise DataDownloadError(
                f"ChEMBL pagination exceeded its declared total count for {target_chembl_id}"
            )
        next_page = page_meta.get("next")
        if next_page is None:
            url = None
        elif isinstance(next_page, str):
            url = urljoin(CHEMBL_API_ROOT, next_page)
        else:
            raise DataDownloadError(f"invalid ChEMBL next page for {target_chembl_id}")
    if expected_total is None or len(rows) != expected_total:
        raise DataDownloadError(
            f"ChEMBL pagination returned {len(rows)} of {expected_total} "
            f"rows for {target_chembl_id}"
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
    """Fetch the ChEMBL status and both targets' full activity pages once, and
    cache each as its own JSON file. Does not validate or aggregate anything;
    that happens when the cache is loaded, so a cache written by an older rule
    is re-checked under the current one rather than silently trusted."""
    fetcher = fetch_json or _fetch_json
    cache_dir.mkdir(parents=True, exist_ok=True)
    status = fetcher(CHEMBL_STATUS_URL)
    validate_chembl_status(status)
    status_path = cache_dir / "status.json"
    _write_json(status_path, status)
    paths = [status_path]
    for target_id in sorted(TARGETS):
        rows = fetch_target_activity_rows(target_id, fetcher)
        path = cache_dir / f"activities-{target_id}.json"
        _write_json(path, {"target_chembl_id": target_id, "activities": rows})
        paths.append(path)
    return tuple(paths)


def load_cached_targets(cache_dir: Path) -> dict[str, TargetDataset]:
    status_payload = _read_json(cache_dir / "status.json")
    validate_chembl_status(status_payload)
    datasets: dict[str, TargetDataset] = {}
    for target_id in sorted(TARGETS):
        payload = _read_json(cache_dir / f"activities-{target_id}.json")
        if payload.get("target_chembl_id") != target_id:
            raise DataContractError(f"cached activity payload has wrong target ID: {target_id}")
        raw_rows = payload.get("activities")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataContractError(f"cached activity rows are invalid for {target_id}")
        datasets[target_id] = normalise_activity_rows(cast(list[JsonObject], raw_rows), target_id)
    return datasets
