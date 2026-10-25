"""Fetch, validate and aggregate real LINCS L1000 perturbation-context records.

Reads GEO series GSE70138 directly: the instance-level metadata, the
perturbagen catalog, and the Level 2 (directly measured, not inferred)
978-landmark-gene expression matrix. A parent-molecule-style admission rule
is applied to instance rows, and each admitted compound-in-cell-line entity's
final value is a vehicle-control-subtracted differential expression profile,
not the raw absolute expression, because raw Level 2 values are dominated by
shared cross-condition baseline structure (see the lab guide for the real
comparison that shows this). Nothing here imports, calls or modifies
chembl_egfr, cyp_assay_system or az_clearance_system.
"""

from __future__ import annotations

import csv
import gzip
import io
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray
from rdkit import Chem

from .protocol import CELL_LINE_A, CELL_LINE_B, FILES, FIXED_DOSE, FIXED_TIME, GEO_SUPPL_BASE_URL

Fetcher = Callable[[str], bytes]


class DataContractError(ValueError):
    """Raised when a fetched or cached record violates the admission rule."""


class DataDownloadError(RuntimeError):
    """Raised when an official GEO file cannot be obtained or cached."""


@dataclass(frozen=True)
class InstanceRow:
    inst_id: str
    cell_id: str
    det_plate: str
    det_well: str
    pert_id: str
    pert_iname: str
    pert_type: str
    pert_dose: str
    pert_time: str


@dataclass(frozen=True)
class PerturbagenRecord:
    pert_id: str
    canonical_smiles: str
    pert_iname: str


@dataclass(frozen=True)
class DataAudit:
    input_rows: int
    retained_rows: int
    admitted_entity_count: int
    duplicate_entity_count: int
    exclusion_counts: dict[str, int]


@dataclass(frozen=True)
class SignatureRecord:
    pert_id: str
    pert_iname: str
    cell_id: str
    canonical_smiles: str
    replicate_count: int
    differential_profile: NDArray[np.float64]


@dataclass(frozen=True)
class CellLineDataset:
    cell_id: str
    signatures: dict[str, SignatureRecord]
    audit: DataAudit


def _fetch_bytes(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            payload: bytes = response.read()
            return payload
    except OSError as error:
        raise DataDownloadError(f"could not fetch official GEO file from {url}: {error}") from error


def download_and_cache_snapshot(
    cache_dir: Path, *, fetch: Fetcher | None = None
) -> tuple[Path, ...]:
    """Fetch every file this protocol declares from the official GEO FTP
    mirror and cache it verbatim. Each file's downloaded size is checked
    against the size fixed in `protocol.py`; GEO shipping a same-named file
    under a different size is treated as a contract violation, not silently
    accepted, since this series has previously reissued files under a new
    name rather than revising one in place."""
    fetcher = fetch or _fetch_bytes
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for key, (filename, expected_size) in FILES.items():
        url = f"{GEO_SUPPL_BASE_URL}/{filename}"
        payload = fetcher(url)
        if len(payload) != expected_size:
            raise DataContractError(
                f"{key}: downloaded {len(payload)} bytes, protocol declares {expected_size}"
            )
        path = cache_dir / filename
        path.write_bytes(payload)
        paths.append(path)
    return tuple(paths)


def _read_gz_tsv(path: Path) -> list[dict[str, str]]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise DataDownloadError(f"could not read cached file {path}: {error}") from error
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
        text = io.TextIOWrapper(gz, encoding="utf-8")
        reader = csv.DictReader(text, delimiter="\t")
        return list(reader)


def _validate_cached_sizes(cache_dir: Path) -> None:
    for key, (filename, expected_size) in FILES.items():
        path = cache_dir / filename
        if not path.is_file():
            raise DataContractError(f"{key}: cached file {filename} is not present")
        actual = path.stat().st_size
        if actual != expected_size:
            raise DataContractError(
                f"{key}: cached size {actual} does not match protocol {expected_size}"
            )


def _load_instance_rows(cache_dir: Path) -> list[InstanceRow]:
    filename, _ = FILES["inst_info"]
    rows = _read_gz_tsv(cache_dir / filename)
    parsed = []
    for row in rows:
        parsed.append(
            InstanceRow(
                inst_id=row["inst_id"],
                cell_id=row["cell_id"],
                det_plate=row["det_plate"],
                det_well=row["det_well"],
                pert_id=row["pert_id"],
                pert_iname=row["pert_iname"],
                pert_type=row["pert_type"],
                pert_dose=row["pert_dose"],
                pert_time=row["pert_time"],
            )
        )
    return parsed


def _load_perturbagens(cache_dir: Path) -> dict[str, PerturbagenRecord]:
    filename, _ = FILES["pert_info"]
    rows = _read_gz_tsv(cache_dir / filename)
    by_id: dict[str, PerturbagenRecord] = {}
    for row in rows:
        by_id[row["pert_id"]] = PerturbagenRecord(
            pert_id=row["pert_id"],
            canonical_smiles=row["canonical_smiles"],
            pert_iname=row["pert_iname"],
        )
    return by_id


def _valid_structure(smiles: str) -> bool:
    if not smiles or smiles in ("-666", "restricted"):
        return False
    molecule = Chem.MolFromSmiles(smiles)
    return molecule is not None and molecule.GetNumAtoms() > 0


def load_cached_cell_lines(cache_dir: Path) -> dict[str, CellLineDataset]:
    """Load both fixed cell lines' admitted, vehicle-control-differential
    signatures from the cache. Every gene expression value returned here is
    directly measured (Level 2, 978 landmark genes), never an inferred or
    imputed value."""
    _validate_cached_sizes(cache_dir)
    instances = _load_instance_rows(cache_dir)
    perturbagens = _load_perturbagens(cache_dir)

    by_inst_id = {r.inst_id: r for r in instances}
    if len(by_inst_id) != len(instances):
        raise DataContractError("duplicate inst_id values in inst_info")

    filename, _ = FILES["level2_gctx"]
    gctx_gz_path = cache_dir / filename
    gctx_path = cache_dir / filename.removesuffix(".gz")
    if not gctx_path.is_file():
        with gzip.open(gctx_gz_path, "rb") as gz, gctx_path.open("wb") as out:
            out.write(gz.read())
    with h5py.File(gctx_path, "r") as h5:
        col_ids = [c.decode("utf-8") for c in h5["0/META/COL/id"][:]]
        matrix = h5["0/DATA/0/matrix"][:]

    datasets: dict[str, CellLineDataset] = {}
    for cell_id in (CELL_LINE_A, CELL_LINE_B):
        datasets[cell_id] = _build_cell_line_dataset(
            cell_id, col_ids, matrix, by_inst_id, perturbagens
        )
    return datasets


def _build_cell_line_dataset(
    cell_id: str,
    col_ids: list[str],
    matrix: NDArray[np.float32],
    by_inst_id: dict[str, InstanceRow],
    perturbagens: dict[str, PerturbagenRecord],
) -> CellLineDataset:
    exclusions: Counter[str] = Counter()
    vehicle_rows_by_plate: dict[str, list[int]] = defaultdict(list)
    candidate_treated: list[tuple[int, InstanceRow]] = []
    input_rows = 0

    for column_index, cid in enumerate(col_ids):
        row = by_inst_id.get(cid)
        if row is None or row.cell_id != cell_id:
            continue
        if row.pert_type == "ctl_vehicle":
            if row.pert_time != FIXED_TIME:
                continue
            vehicle_rows_by_plate[row.det_plate].append(column_index)
            continue
        if row.pert_type != "trt_cp":
            continue
        input_rows += 1
        if row.pert_time != FIXED_TIME:
            exclusions["wrong_time"] += 1
            continue
        if row.pert_dose != FIXED_DOSE:
            exclusions["wrong_dose"] += 1
            continue
        perturbagen = perturbagens.get(row.pert_id)
        if perturbagen is None or not _valid_structure(perturbagen.canonical_smiles):
            exclusions["missing_structure"] += 1
            continue
        candidate_treated.append((column_index, row))

    vehicle_profile_cache: dict[str, NDArray[np.float64] | None] = {}

    def vehicle_profile(plate: str) -> NDArray[np.float64] | None:
        if plate not in vehicle_profile_cache:
            indices = vehicle_rows_by_plate.get(plate)
            if not indices:
                vehicle_profile_cache[plate] = None
            else:
                vehicle_profile_cache[plate] = np.median(
                    matrix[sorted(indices), :].astype(np.float64), axis=0
                )
        return vehicle_profile_cache[plate]

    by_pert: dict[str, list[NDArray[np.float64]]] = defaultdict(list)
    retained_rows = 0
    for column_index, row in candidate_treated:
        baseline = vehicle_profile(row.det_plate)
        if baseline is None:
            exclusions["no_plate_vehicle_control"] += 1
            continue
        retained_rows += 1
        differential = matrix[column_index, :].astype(np.float64) - baseline
        by_pert[row.pert_id].append(differential)

    signatures: dict[str, SignatureRecord] = {}
    duplicate_entity_count = 0
    for pert_id, diffs in sorted(by_pert.items()):
        if len(diffs) > 1:
            duplicate_entity_count += 1
        perturbagen = perturbagens[pert_id]
        signatures[pert_id] = SignatureRecord(
            pert_id=pert_id,
            pert_iname=perturbagen.pert_iname,
            cell_id=cell_id,
            canonical_smiles=perturbagen.canonical_smiles,
            replicate_count=len(diffs),
            differential_profile=np.median(np.array(diffs), axis=0),
        )

    audit = DataAudit(
        input_rows=input_rows,
        retained_rows=retained_rows,
        admitted_entity_count=len(signatures),
        duplicate_entity_count=duplicate_entity_count,
        exclusion_counts=dict(sorted(exclusions.items())),
    )
    return CellLineDataset(cell_id=cell_id, signatures=signatures, audit=audit)
