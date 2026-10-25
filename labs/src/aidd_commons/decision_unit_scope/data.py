"""Fetch, cache, validate and classify real ChEMBL 37 activity rows.

HTTP handling is reused from `aidd_commons.chembl_egfr.data` (`_fetch_json`
and `_read_json`) rather than reimplemented. The pagination guard is the same
contract that module applies to its own activity queries, with the query
keyed on the parent molecule instead of on an assay.

The admission rule lives here, as one function, because two callers need it:
the downloader uses it to decide which assay metadata to fetch, and the
analysis uses it to decide which rows are measurements.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlencode, urljoin

from rdkit import Chem

from aidd_commons.chembl_egfr.data import DataDownloadError, _fetch_json, _read_json

from .protocol import (
    ACTIVITY_FIELDS,
    ACTIVITY_PAGE_SIZE,
    ARTIFACT_BYTE_LENGTHS,
    ASSAY_BATCH_SIZE,
    ASSAY_FIELDS,
    BOUND_RELATIONS,
    CHEMBL_API_ROOT,
    CHEMBL_RELEASE_DATE,
    CHEMBL_STATUS_URL,
    CHEMBL_VERSION,
    COHORT_PARENTS,
    COHORT_SEEDS,
    ENDPOINT_TYPES,
    POINT_RELATION,
    STANDARD_UNITS,
)

JsonObject = Mapping[str, object]
JsonFetcher = Callable[[str], JsonObject]


class DataContractError(ValueError):
    """Raised when a fetched or cached record violates the frozen contract."""


@dataclass(frozen=True)
class MoleculeRecord:
    """One declared seed molecule, as ChEMBL stores it."""

    molecule_chembl_id: str
    pref_name: str
    parent_molecule_chembl_id: str
    canonical_smiles: str
    fragment_count: int

    @property
    def is_own_parent(self) -> bool:
        return self.molecule_chembl_id == self.parent_molecule_chembl_id


@dataclass(frozen=True)
class AssayRecord:
    """The experimental context of one assay."""

    assay_chembl_id: str
    assay_type: str | None
    assay_organism: str | None
    assay_tax_id: int | None
    bao_format: str | None
    confidence_score: int | None
    document_chembl_id: str | None
    relationship_type: str | None
    target_chembl_id: str | None


@dataclass(frozen=True)
class ActivityRow:
    """One ChEMBL activity row, normalised to the fields this lab uses."""

    activity_id: int
    assay_chembl_id: str
    document_chembl_id: str
    document_journal: str | None
    document_year: int | None
    molecule_chembl_id: str
    parent_molecule_chembl_id: str
    canonical_smiles: str
    standard_type: str | None
    standard_relation: str | None
    standard_value: float | None
    standard_units: str | None
    standard_flag: int | None
    potential_duplicate: int | None
    data_validity_comment: str | None
    pchembl_value: float | None
    assay_type: str | None
    target_chembl_id: str | None
    target_organism: str | None
    target_pref_name: str | None
    toid: str | None

    @property
    def is_child_form(self) -> bool:
        """True when the tested form is not the parent entity itself."""
        return self.molecule_chembl_id != self.parent_molecule_chembl_id

    @property
    def classification(self) -> str:
        """The admission rule's verdict on this row."""
        return classify_values(
            standard_flag=self.standard_flag,
            potential_duplicate=self.potential_duplicate,
            data_validity_comment=self.data_validity_comment,
            standard_type=self.standard_type,
            standard_units=self.standard_units,
            standard_value=self.standard_value,
            canonical_smiles=self.canonical_smiles,
            standard_relation=self.standard_relation,
        )

    @property
    def grouping_key(self) -> tuple[str, str, str]:
        return (
            self.assay_chembl_id,
            self.document_chembl_id,
            self.standard_type or "",
        )

    @property
    def experiment_key(self) -> tuple[str, str]:
        return (self.assay_chembl_id, self.document_chembl_id)


@dataclass(frozen=True)
class ParentDataset:
    """Every activity row ChEMBL files under one parent molecule."""

    parent_molecule_chembl_id: str
    rows: tuple[ActivityRow, ...]


@dataclass(frozen=True)
class CohortDataset:
    """The declared cohort: its seeds, its parents and the assay context."""

    status: Mapping[str, str]
    molecules: Mapping[str, MoleculeRecord]
    parents: Mapping[str, ParentDataset]
    assays: Mapping[str, AssayRecord]


def validate_chembl_status(payload: JsonObject) -> dict[str, str]:
    """Refuse any release other than the one this protocol was frozen against."""
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


def fragment_count(smiles: str) -> int:
    """The number of disconnected components in a stored structure.

    One component is a single molecule. More than one is a formulation: a
    salt, a solvate or a combination product.
    """
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None or molecule.GetNumAtoms() == 0:
        raise DataContractError(f"structure is not readable by RDKit: {smiles!r}")
    return len(Chem.GetMolFrags(molecule))


def classify_values(
    *,
    standard_flag: int | None,
    potential_duplicate: int | None,
    data_validity_comment: str | None,
    standard_type: str | None,
    standard_units: str | None,
    standard_value: float | None,
    canonical_smiles: str | None,
    standard_relation: str | None,
) -> str:
    """The protocol's admission rule, applied to one row's declared fields.

    Returns ``"point"`` for an admitted point measurement, ``"bound"`` for an
    admitted censored measurement, or the first matching exclusion reason in
    the declared priority order.
    """
    if standard_flag != 1:
        return "non_standard_activity"
    if potential_duplicate != 0:
        return "potential_duplicate"
    if data_validity_comment is not None:
        return "data_validity_comment"
    if standard_type not in ENDPOINT_TYPES:
        return "outside_endpoint_family"
    if standard_units != STANDARD_UNITS:
        return "non_nanomolar_units"
    if standard_value is None or standard_value <= 0.0:
        return "missing_value"
    if not canonical_smiles:
        return "missing_structure"
    if standard_relation == POINT_RELATION:
        return "point"
    if standard_relation in BOUND_RELATIONS:
        return "bound"
    return "missing_relation"


def classify_row(row: Mapping[str, Any]) -> str:
    """The protocol's admission rule, applied to one raw activity row."""
    return classify_values(
        standard_flag=_optional_int(row.get("standard_flag")),
        potential_duplicate=_optional_int(row.get("potential_duplicate")),
        data_validity_comment=_optional_str(row.get("data_validity_comment")),
        standard_type=_optional_str(row.get("standard_type")),
        standard_units=_optional_str(row.get("standard_units")),
        standard_value=_optional_float(row.get("standard_value")),
        canonical_smiles=_optional_str(row.get("canonical_smiles")),
        standard_relation=_optional_str(row.get("standard_relation")),
    )


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (str, int, float)):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def _required_str(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DataContractError(f"activity field {field} must be a non-empty string")
    return value


def _required_int(row: Mapping[str, Any], field: str) -> int:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataContractError(f"activity field {field} must be an integer")
    return value


def normalise_activity_row(row: Mapping[str, Any]) -> ActivityRow:
    """Normalise one raw ChEMBL activity row into the lab's row type."""
    return ActivityRow(
        activity_id=_required_int(row, "activity_id"),
        assay_chembl_id=_required_str(row, "assay_chembl_id"),
        document_chembl_id=_required_str(row, "document_chembl_id"),
        document_journal=_optional_str(row.get("document_journal")),
        document_year=_optional_int(row.get("document_year")),
        molecule_chembl_id=_required_str(row, "molecule_chembl_id"),
        parent_molecule_chembl_id=_required_str(row, "parent_molecule_chembl_id"),
        canonical_smiles=_optional_str(row.get("canonical_smiles")) or "",
        standard_type=_optional_str(row.get("standard_type")),
        standard_relation=_optional_str(row.get("standard_relation")),
        standard_value=_optional_float(row.get("standard_value")),
        standard_units=_optional_str(row.get("standard_units")),
        standard_flag=_optional_int(row.get("standard_flag")),
        potential_duplicate=_optional_int(row.get("potential_duplicate")),
        data_validity_comment=_optional_str(row.get("data_validity_comment")),
        pchembl_value=_optional_float(row.get("pchembl_value")),
        assay_type=_optional_str(row.get("assay_type")),
        target_chembl_id=_optional_str(row.get("target_chembl_id")),
        target_organism=_optional_str(row.get("target_organism")),
        target_pref_name=_optional_str(row.get("target_pref_name")),
        toid=_optional_str(row.get("toid")),
    )


def normalise_molecule(payload: JsonObject, seed_id: str, pref_name: str) -> MoleculeRecord:
    """Validate one declared seed molecule against the declared cohort."""
    if payload.get("molecule_chembl_id") != seed_id:
        raise DataContractError(
            f"molecule payload is for {payload.get('molecule_chembl_id')!r}, expected {seed_id!r}"
        )
    if payload.get("pref_name") != pref_name:
        raise DataContractError(
            f"molecule {seed_id} is named {payload.get('pref_name')!r}, expected {pref_name!r}"
        )
    hierarchy = payload.get("molecule_hierarchy")
    if not isinstance(hierarchy, Mapping):
        raise DataContractError(f"molecule {seed_id} has no molecule_hierarchy")
    parent_id = hierarchy.get("parent_chembl_id")
    if not isinstance(parent_id, str) or not parent_id.strip():
        raise DataContractError(f"molecule {seed_id} has no parent_chembl_id")
    if parent_id not in COHORT_PARENTS:
        raise DataContractError(
            f"molecule {seed_id} resolves to parent {parent_id!r}, "
            "which the protocol does not declare"
        )
    structures = payload.get("molecule_structures")
    if not isinstance(structures, Mapping):
        raise DataContractError(f"molecule {seed_id} has no molecule_structures")
    smiles = structures.get("canonical_smiles")
    if not isinstance(smiles, str) or not smiles.strip():
        raise DataContractError(f"molecule {seed_id} has no canonical_smiles")
    return MoleculeRecord(
        molecule_chembl_id=seed_id,
        pref_name=pref_name,
        parent_molecule_chembl_id=parent_id,
        canonical_smiles=smiles,
        fragment_count=fragment_count(smiles),
    )


def _activity_query_url(parent_id: str) -> str:
    query = urlencode(
        {
            "parent_molecule_chembl_id": parent_id,
            "limit": ACTIVITY_PAGE_SIZE,
            "only": ",".join(ACTIVITY_FIELDS),
        }
    )
    return f"{CHEMBL_API_ROOT}/chembl/api/data/activity.json?{query}"


def fetch_parent_activity_rows(parent_id: str, fetcher: JsonFetcher) -> list[JsonObject]:
    """Fetch every activity row ChEMBL files under one parent molecule.

    The guard is the same one `aidd_commons.chembl_egfr.data` applies to its
    own activity pages: the declared total must not move between pages, a page
    must not repeat, and the number of rows returned must match the total.
    """
    url: str | None = _activity_query_url(parent_id)
    rows: list[JsonObject] = []
    expected_total: int | None = None
    visited_urls: set[str] = set()
    while url is not None:
        if url in visited_urls:
            raise DataDownloadError(f"ChEMBL pagination repeated a page for {parent_id}")
        visited_urls.add(url)
        payload = fetcher(url)
        raw_rows = payload.get("activities")
        page_meta = payload.get("page_meta")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataDownloadError(f"invalid ChEMBL activity page for {parent_id}")
        if not isinstance(page_meta, Mapping):
            raise DataDownloadError(f"missing ChEMBL page metadata for {parent_id}")
        total = page_meta.get("total_count")
        if not isinstance(total, int):
            raise DataDownloadError(f"invalid ChEMBL total count for {parent_id}")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise DataDownloadError(f"ChEMBL total count changed during pagination for {parent_id}")
        rows.extend(cast(list[JsonObject], raw_rows))
        if len(rows) > expected_total:
            raise DataDownloadError(
                f"ChEMBL pagination exceeded its declared total count for {parent_id}"
            )
        next_page = page_meta.get("next")
        if next_page is None:
            url = None
        elif isinstance(next_page, str):
            url = urljoin(CHEMBL_API_ROOT, next_page)
        else:
            raise DataDownloadError(f"invalid ChEMBL next page for {parent_id}")
    if expected_total is None or len(rows) != expected_total:
        raise DataDownloadError(
            f"ChEMBL pagination returned {len(rows)} of {expected_total} rows for {parent_id}"
        )
    return sorted(rows, key=lambda row: cast(int, row["activity_id"]))


def fetch_assay_records(assay_ids: Sequence[str], fetcher: JsonFetcher) -> list[JsonObject]:
    """Fetch the assay records behind a set of assay identifiers."""
    records: list[JsonObject] = []
    unique = sorted(set(assay_ids))
    for start in range(0, len(unique), ASSAY_BATCH_SIZE):
        batch = unique[start : start + ASSAY_BATCH_SIZE]
        query = urlencode(
            {
                "assay_chembl_id__in": ",".join(batch),
                "limit": ASSAY_BATCH_SIZE,
                "only": ",".join(ASSAY_FIELDS),
            }
        )
        payload = fetcher(f"{CHEMBL_API_ROOT}/chembl/api/data/assay.json?{query}")
        raw_rows = payload.get("assays")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataDownloadError("invalid ChEMBL assay page")
        records.extend(cast(list[JsonObject], raw_rows))
    return sorted(records, key=lambda row: cast(str, row["assay_chembl_id"]))


def normalise_assay_record(payload: Mapping[str, Any]) -> AssayRecord:
    assay_id = payload.get("assay_chembl_id")
    if not isinstance(assay_id, str) or not assay_id.strip():
        raise DataContractError("assay record has no assay_chembl_id")
    return AssayRecord(
        assay_chembl_id=assay_id,
        assay_type=_optional_str(payload.get("assay_type")),
        assay_organism=_optional_str(payload.get("assay_organism")),
        assay_tax_id=_optional_int(payload.get("assay_tax_id")),
        bao_format=_optional_str(payload.get("bao_format")),
        confidence_score=_optional_int(payload.get("confidence_score")),
        document_chembl_id=_optional_str(payload.get("document_chembl_id")),
        relationship_type=_optional_str(payload.get("relationship_type")),
        target_chembl_id=_optional_str(payload.get("target_chembl_id")),
    )


def _artefact_is_current(path: Path) -> bool:
    """True when the cached artefact still has its frozen byte length."""
    expected = ARTIFACT_BYTE_LENGTHS.get(path.name)
    if expected is None:
        return False
    return path.is_file() and path.stat().st_size == expected


def _assert_frozen_length(path: Path) -> None:
    """Refuse a cached artefact whose byte length is not the frozen one."""
    expected = ARTIFACT_BYTE_LENGTHS.get(path.name)
    if expected is None:
        return
    if not path.is_file():
        raise DataContractError(f"{path.name}: cached artefact is not present")
    actual = path.stat().st_size
    if actual != expected:
        raise DataContractError(
            f"{path.name}: cached artefact is {actual} bytes, "
            f"the frozen protocol declares {expected}"
        )


def _write_artefact(path: Path, payload: object) -> int:
    """Write one cached artefact and check it against the frozen byte length."""
    data = (json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    expected = ARTIFACT_BYTE_LENGTHS.get(path.name)
    if expected is not None and len(data) != expected:
        raise DataContractError(
            f"{path.name}: fetched {len(data)} bytes, the frozen protocol declares {expected}"
        )
    path.write_bytes(data)
    return len(data)


def _admitted_assay_ids(cache_dir: Path) -> list[str]:
    """The assays behind every admitted row, which is what the lab needs context for."""
    assay_ids: set[str] = set()
    for parent_id in COHORT_PARENTS:
        payload = _read_json(cache_dir / f"activities-{parent_id}.json")
        raw_rows = payload.get("activities")
        if not isinstance(raw_rows, list):
            raise DataContractError(f"cached activity rows are invalid for {parent_id}")
        for row in cast(list[JsonObject], raw_rows):
            if classify_row(row) in ("point", "bound"):
                assay_id = row.get("assay_chembl_id")
                if isinstance(assay_id, str) and assay_id.strip():
                    assay_ids.add(assay_id)
    return sorted(assay_ids)


@dataclass(frozen=True)
class DownloadReport:
    """What one download did: which artefacts it fetched and which it kept."""

    paths: tuple[Path, ...]
    fetched: tuple[str, ...]
    reused: tuple[str, ...]
    total_bytes: int

    def describe(self) -> str:
        return (
            f"{len(self.fetched)} artefact(s) fetched, {len(self.reused)} reused from cache, "
            f"{self.total_bytes} bytes in the cache"
        )


def download_and_cache_snapshot(
    cache_dir: Path, *, fetch_json: JsonFetcher | None = None
) -> DownloadReport:
    """Fetch and cache every artefact this protocol declares.

    The download is resumable. A cached artefact whose byte length still
    matches the frozen value is kept and not re-fetched; a missing or
    mismatched one is fetched again. The ChEMBL status endpoint is always
    contacted, because the live release assertion is the point of the check.
    """
    fetcher = fetch_json or _fetch_json
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    fetched: list[str] = []
    reused: list[str] = []

    status = fetcher(CHEMBL_STATUS_URL)
    validate_chembl_status(status)
    status_path = cache_dir / "status.json"
    _write_artefact(status_path, status)
    paths.append(status_path)
    fetched.append(status_path.name)

    molecules_path = cache_dir / "molecules.json"
    if not _artefact_is_current(molecules_path):
        molecules: dict[str, object] = {}
        for seed_id, pref_name in COHORT_SEEDS:
            payload = fetcher(
                f"{CHEMBL_API_ROOT}/chembl/api/data/molecule/{seed_id}.json"
            )
            record = normalise_molecule(payload, seed_id, pref_name)
            molecules[seed_id] = {
                "canonical_smiles": record.canonical_smiles,
                "fragment_count": record.fragment_count,
                "molecule_chembl_id": record.molecule_chembl_id,
                "parent_molecule_chembl_id": record.parent_molecule_chembl_id,
                "pref_name": record.pref_name,
            }
        _write_artefact(molecules_path, {"molecules": molecules})
        fetched.append(molecules_path.name)
    else:
        reused.append(molecules_path.name)
    paths.append(molecules_path)

    for parent_id in COHORT_PARENTS:
        path = cache_dir / f"activities-{parent_id}.json"
        if not _artefact_is_current(path):
            rows = fetch_parent_activity_rows(parent_id, fetcher)
            _write_artefact(
                path, {"parent_molecule_chembl_id": parent_id, "activities": rows}
            )
            fetched.append(path.name)
        else:
            reused.append(path.name)
        paths.append(path)

    assays_path = cache_dir / "assays.json"
    if not _artefact_is_current(assays_path):
        records = fetch_assay_records(_admitted_assay_ids(cache_dir), fetcher)
        _write_artefact(assays_path, {"assays": records})
        fetched.append(assays_path.name)
    else:
        reused.append(assays_path.name)
    paths.append(assays_path)

    total_bytes = sum(path.stat().st_size for path in paths)
    return DownloadReport(
        paths=tuple(paths),
        fetched=tuple(fetched),
        reused=tuple(reused),
        total_bytes=total_bytes,
    )


def load_cached_cohort(cache_dir: Path) -> CohortDataset:
    """Load the cached cohort and re-check it against the frozen contract."""
    for name in ("status.json", "molecules.json", "assays.json"):
        _assert_frozen_length(cache_dir / name)
    for parent_id in COHORT_PARENTS:
        _assert_frozen_length(cache_dir / f"activities-{parent_id}.json")

    status_payload = _read_json(cache_dir / "status.json")
    status = validate_chembl_status(status_payload)

    molecules_payload = _read_json(cache_dir / "molecules.json")
    raw_molecules = molecules_payload.get("molecules")
    if not isinstance(raw_molecules, Mapping):
        raise DataContractError("cached molecules artefact is invalid")
    molecules: dict[str, MoleculeRecord] = {}
    for seed_id, _pref_name in COHORT_SEEDS:
        entry = raw_molecules.get(seed_id)
        if not isinstance(entry, Mapping):
            raise DataContractError(f"cached molecules artefact has no entry for {seed_id}")
        molecules[seed_id] = MoleculeRecord(
            molecule_chembl_id=str(entry.get("molecule_chembl_id")),
            pref_name=str(entry.get("pref_name")),
            parent_molecule_chembl_id=str(entry.get("parent_molecule_chembl_id")),
            canonical_smiles=str(entry.get("canonical_smiles")),
            fragment_count=int(cast(int, entry.get("fragment_count"))),
        )
    resolved = {record.parent_molecule_chembl_id for record in molecules.values()}
    if resolved != set(COHORT_PARENTS):
        raise DataContractError(
            "cached molecules artefact resolves to parents that differ from the protocol"
        )

    parents: dict[str, ParentDataset] = {}
    for parent_id in COHORT_PARENTS:
        payload = _read_json(cache_dir / f"activities-{parent_id}.json")
        if payload.get("parent_molecule_chembl_id") != parent_id:
            raise DataContractError(f"cached activity payload has wrong parent ID: {parent_id}")
        raw_rows = payload.get("activities")
        if not isinstance(raw_rows, list) or not all(isinstance(row, Mapping) for row in raw_rows):
            raise DataContractError(f"cached activity rows are invalid for {parent_id}")
        rows = tuple(normalise_activity_row(cast(Mapping[str, Any], row)) for row in raw_rows)
        parents[parent_id] = ParentDataset(parent_molecule_chembl_id=parent_id, rows=rows)

    assays_payload = _read_json(cache_dir / "assays.json")
    raw_assays = assays_payload.get("assays")
    if not isinstance(raw_assays, list) or not all(isinstance(row, Mapping) for row in raw_assays):
        raise DataContractError("cached assays artefact is invalid")
    assays = {
        record.assay_chembl_id: record
        for record in (
            normalise_assay_record(cast(Mapping[str, Any], row)) for row in raw_assays
        )
    }

    return CohortDataset(
        status=status, molecules=molecules, parents=parents, assays=assays
    )


def exclusion_counts(rows: Sequence[ActivityRow]) -> Counter[str]:
    """Count the exclusion reasons of a set of rows, in the declared order."""
    counts: Counter[str] = Counter()
    for row in rows:
        reason = row.classification
        if reason in ("point", "bound"):
            continue
        counts[reason] += 1
    return counts
