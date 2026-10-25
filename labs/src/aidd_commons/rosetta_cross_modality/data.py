"""Fetch, validate and assemble the ROSETTA cross-modality readout pairs.

The lab reads two published objects of one Cell Painting Gallery study:
the replicate-level L1000 transcriptomic release and the replicate-level
Cell Painting imaging release of the same batch. A perturbation is the
join key. This module owns the download contract (build the URL, fetch,
compare the byte length against the size frozen in the protocol, cache it,
and never re-download a cache that is already valid), the parsing rules
(which columns are features, which are annotation), and the admission rule
that turns wells into perturbation entities.

The cache-and-validate pattern mirrors
``aidd_commons.l1000_perturbation_context.data.download_and_cache_snapshot``,
which is bound to one GEO file set and therefore cannot be reused verbatim
for a different host. The shared behaviour is kept exactly: build the URL
from the frozen relative path, fetch, compare ``len(payload)`` against the
byte size fixed in the protocol, write the payload verbatim, and re-validate
the cache on every run rather than trusting it. Two properties are added
because this lab fetches over a long-lived connection: a valid cache is not
re-downloaded, and an interrupted download resumes from the bytes already on
disk instead of starting over.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import re
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from .protocol import Contract, ContractError, SourceFile


class DataContractError(ContractError):
    """Raised when a fetched or cached record violates the admission rule."""


class DataDownloadError(RuntimeError):
    """Raised when a published object cannot be obtained or cached."""


@dataclass(frozen=True)
class FetchedChunk:
    """Bytes of a published object together with the offset they start at.

    `start_offset` is zero when the server ignored a range request and
    returned the whole object, so the caller knows to rewrite the partial
    file rather than append to it.
    """

    payload: bytes
    start_offset: int


Fetcher = Callable[[str, int], FetchedChunk]


@dataclass(frozen=True)
class Well:
    """One measured well in one readout."""

    well_id: str
    plate: str
    perturbation: str
    is_control: bool
    allele: str
    gene_symbol: str
    values: NDArray[np.float64]


@dataclass(frozen=True)
class Readout:
    """One modality's replicate-level wells and its feature vocabulary."""

    name: str
    feature_names: tuple[str, ...]
    wells: tuple[Well, ...]

    @property
    def treated_wells(self) -> tuple[Well, ...]:
        return tuple(well for well in self.wells if not well.is_control)

    @property
    def control_wells(self) -> tuple[Well, ...]:
        return tuple(well for well in self.wells if well.is_control)


@dataclass(frozen=True)
class Perturbation:
    """One genetic perturbation measured in both readouts."""

    name: str
    allele: str
    gene_symbol: str
    transcriptome: NDArray[np.float64]
    imaging: NDArray[np.float64]
    transcriptome_plates: tuple[str, ...]
    imaging_plates: tuple[str, ...]
    imaging_batches: tuple[str, ...]
    transcriptome_replicates: int
    imaging_replicates: int

    @property
    def batch_pure(self) -> bool:
        """True when every imaging well of this perturbation sits on one batch."""
        return len(self.imaging_batches) == 1

    @property
    def batch(self) -> str | None:
        return self.imaging_batches[0] if self.batch_pure else None


@dataclass(frozen=True)
class Audit:
    """Counts of what was read, what was admitted and what was dropped."""

    transcriptome_input_rows: int
    transcriptome_control_rows: int
    transcriptome_treated_rows: int
    transcriptome_distinct_wells: int
    imaging_input_rows: int
    imaging_control_rows: int
    imaging_treated_rows: int
    imaging_distinct_wells: int
    transcriptome_perturbations: int
    imaging_perturbations: int
    admitted_perturbations: int
    transcriptome_plates: int
    imaging_plates: int
    imaging_batches: int
    batch_pure_perturbations: int
    batch_mixed_perturbations: int
    exclusion_counts: dict[str, int]


@dataclass(frozen=True)
class Dataset:
    """Everything the analysis needs, and the audit that describes it."""

    perturbations: tuple[Perturbation, ...]
    transcriptome_features: tuple[str, ...]
    imaging_features: tuple[str, ...]
    transcriptome_wells: tuple[Well, ...]
    imaging_wells: tuple[Well, ...]
    imaging_batch_of_plate: dict[str, str]
    audit: Audit


def _fetch_range(url: str, start: int) -> FetchedChunk:
    """Fetch the published object, honouring a byte offset when one is asked
    for. A server that ignores the range is answered with the whole object
    and a zero offset, so the caller rewrites rather than appends."""
    request = urllib.request.Request(url)
    if start > 0:
        request.add_header("Range", f"bytes={start}-")
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            if start > 0 and response.status != 206:
                return _fetch_range(url, 0)
            return FetchedChunk(payload=response.read(), start_offset=start)
    except OSError as error:
        raise DataDownloadError(f"could not fetch published object {url}: {error}") from error


def _cached_file_is_valid(path: Path, source: SourceFile) -> bool:
    return path.is_file() and path.stat().st_size == source.byte_length


def download_and_cache_snapshot(
    cache_dir: Path, contract: Contract, *, fetch: Fetcher | None = None
) -> tuple[Path, ...]:
    """Fetch every object the contract declares and cache it verbatim.

    Each object's downloaded size is checked against the size fixed in the
    contract; a different size under the same name is a contract violation,
    not something to accept quietly. The entity tag the gallery's own
    listing carries is checked once, at the moment of acquisition, so a
    cache that was already present is not re-read and re-hashed.

    A cache that is already the right size is left alone. An interrupted
    download leaves a ``.part`` file behind, and the next run resumes from
    the bytes already on disk.
    """
    fetcher = fetch or _fetch_range
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for source in contract.files:
        path = cache_dir / source.filename
        if _cached_file_is_valid(path, source):
            paths.append(path)
            continue
        part = path.with_name(path.name + ".part")
        offset = part.stat().st_size if part.is_file() else 0
        chunk = fetcher(source.url, offset)
        total = chunk.start_offset + len(chunk.payload)
        if total != source.byte_length:
            raise DataContractError(
                f"{source.key}: downloaded {total} bytes, the contract declares "
                f"{source.byte_length}"
            )
        if chunk.start_offset == 0:
            mode = "wb"
        else:
            mode = "ab"
        with part.open(mode) as handle:
            handle.write(chunk.payload)
        content_etag = hashlib.md5(part.read_bytes()).hexdigest()
        if content_etag != source.s3_etag:
            part.unlink(missing_ok=True)
            raise DataContractError(
                f"{source.key}: content ETag {content_etag} does not match the entity "
                f"tag {source.s3_etag} published with this object"
            )
        part.replace(path)
        paths.append(path)
    return tuple(paths)


def validate_cached_files(cache_dir: Path, contract: Contract) -> None:
    """Re-check the cache against the frozen contract on every run."""
    for source in contract.files:
        path = cache_dir / source.filename
        if not path.is_file():
            raise DataContractError(f"{source.key}: cached file {source.filename} is not present")
        actual = path.stat().st_size
        if actual != source.byte_length:
            raise DataContractError(
                f"{source.key}: cached size {actual} does not match the contract "
                f"{source.byte_length}"
            )


def _read_csv_gz(path: Path) -> tuple[list[str], list[list[str]]]:
    try:
        with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            rows = list(reader)
    except (OSError, StopIteration, UnicodeDecodeError) as error:
        raise DataDownloadError(f"could not read cached file {path}: {error}") from error
    return header, rows


def _feature_columns(
    header: list[str], pattern: str, label: str
) -> tuple[tuple[str, ...], list[int]]:
    matcher = re.compile(pattern)
    names = tuple(name for name in header if matcher.match(name))
    if not names:
        raise DataContractError(f"no {label} feature column matches {pattern!r}")
    positions = [header.index(name) for name in names]
    return names, positions


def _require_columns(header: list[str], required: tuple[str, ...], label: str) -> None:
    missing = [name for name in required if name not in header]
    if missing:
        raise DataContractError(f"{label} file is missing required columns: {missing}")


def _numeric_row(row: list[str], positions: list[int], label: str) -> NDArray[np.float64]:
    values = np.empty(len(positions), dtype=np.float64)
    for index, position in enumerate(positions):
        text = row[position]
        try:
            value = float(text)
        except ValueError as error:
            raise DataContractError(f"{label} feature cell {text!r} is not a number") from error
        if not np.isfinite(value):
            raise DataContractError(f"{label} feature cell {text!r} is not finite")
        values[index] = value
    return values


def _load_transcriptome(path: Path, contract: Contract) -> Readout:
    header, rows = _read_csv_gz(path)
    _require_columns(header, contract.transcriptome_required_columns, "transcriptome")
    names, positions = _feature_columns(
        header, contract.transcriptome_feature_pattern, "transcriptome"
    )
    perturbation_at = header.index(contract.transcriptome_join_key)
    type_at = header.index("pert_type")
    plate_at = header.index("det_plate")
    allele_at, symbol_at = (
        header.index(column) for column in contract.transcriptome_label_columns
    )
    id_at = header.index("id")
    wells = [
        Well(
            well_id=row[id_at],
            plate=row[plate_at],
            perturbation=row[perturbation_at],
            is_control=row[type_at] == contract.control_pert_type,
            allele=row[allele_at],
            gene_symbol=row[symbol_at],
            values=_numeric_row(row, positions, "transcriptome"),
        )
        for row in rows
    ]
    return Readout(name="transcriptome", feature_names=names, wells=tuple(wells))


def _load_imaging(path: Path, contract: Contract) -> Readout:
    header, rows = _read_csv_gz(path)
    _require_columns(header, contract.imaging_required_columns, "imaging")
    names, positions = _feature_columns(header, contract.imaging_feature_pattern, "imaging")
    perturbation_at = header.index(contract.imaging_join_key)
    type_at = header.index("pert_type")
    plate_at = header.index("Metadata_Plate")
    well_at = header.index("Metadata_Well")
    wells = [
        Well(
            well_id=f"{row[plate_at]}:{row[well_at]}",
            plate=row[plate_at],
            perturbation=row[perturbation_at],
            is_control=row[type_at] == contract.control_pert_type,
            allele="",
            gene_symbol="",
            values=_numeric_row(row, positions, "imaging"),
        )
        for row in rows
    ]
    return Readout(name="imaging", feature_names=names, wells=tuple(wells))


def _profile(wells: list[Well]) -> NDArray[np.float64]:
    stacked = np.array([well.values for well in wells], dtype=np.float64)
    profile: NDArray[np.float64] = np.median(stacked, axis=0)
    return profile


def load_cached_dataset(cache_dir: Path, contract: Contract) -> Dataset:
    """Read both cached readouts and assemble the perturbation entities.

    An entity is one perturbation name that carries at least one treated well
    in each readout. Its profile in a readout is the median across that
    perturbation's replicate wells in that readout, which keeps one bad well
    from deciding a profile and keeps every perturbation to exactly one row
    per readout, so no replicate of a perturbation can be split across a
    training and a test side of any evaluation.
    """
    validate_cached_files(cache_dir, contract)
    transcriptome = _load_transcriptome(
        cache_dir / contract.transcriptome_file.filename, contract
    )
    imaging = _load_imaging(cache_dir / contract.imaging_file.filename, contract)
    if not transcriptome.control_wells:
        raise DataContractError(
            "the transcriptomic readout carries no control well, so the contract's "
            "control type does not match this release"
        )
    if not imaging.control_wells:
        raise DataContractError(
            "the imaging readout carries no control well, so the contract's control "
            "type does not match this release"
        )

    exclusions: Counter[str] = Counter()
    transcriptome_by_perturbation: dict[str, list[Well]] = defaultdict(list)
    for well in transcriptome.treated_wells:
        if not well.perturbation:
            exclusions["transcriptome_empty_perturbation_name"] += 1
            continue
        transcriptome_by_perturbation[well.perturbation].append(well)
    imaging_by_perturbation: dict[str, list[Well]] = defaultdict(list)
    for well in imaging.treated_wells:
        if not well.perturbation:
            exclusions["imaging_empty_perturbation_name"] += 1
            continue
        imaging_by_perturbation[well.perturbation].append(well)

    for name in transcriptome_by_perturbation:
        if name not in imaging_by_perturbation:
            exclusions["transcriptome_only_perturbation"] += 1
    for name in imaging_by_perturbation:
        if name not in transcriptome_by_perturbation:
            exclusions["imaging_only_perturbation"] += 1
    for label, catalogue in (
        ("transcriptome", transcriptome_by_perturbation),
        ("imaging", imaging_by_perturbation),
    ):
        if len(catalogue) < 2:
            raise DataContractError(
                f"the {label} readout carries a single treated perturbation identifier, "
                "so the join key names a column that does not identify perturbations"
            )

    annotation: dict[str, tuple[str, str]] = {}
    for well in transcriptome.treated_wells:
        if well.perturbation and well.perturbation not in annotation:
            annotation[well.perturbation] = (well.allele, well.gene_symbol)

    imaging_batches = _imaging_batches(
        cache_dir / contract.imaging_file.filename, contract
    )

    perturbations: list[Perturbation] = []
    for name in sorted(set(transcriptome_by_perturbation) & set(imaging_by_perturbation)):
        transcriptome_wells = transcriptome_by_perturbation[name]
        imaging_wells = imaging_by_perturbation[name]
        batches = tuple(sorted({imaging_batches[well.plate] for well in imaging_wells}))
        allele, gene_symbol = annotation[name]
        perturbations.append(
            Perturbation(
                name=name,
                allele=allele,
                gene_symbol=gene_symbol,
                transcriptome=_profile(transcriptome_wells),
                imaging=_profile(imaging_wells),
                transcriptome_plates=tuple(sorted({w.plate for w in transcriptome_wells})),
                imaging_plates=tuple(sorted({w.plate for w in imaging_wells})),
                imaging_batches=batches,
                transcriptome_replicates=len(transcriptome_wells),
                imaging_replicates=len(imaging_wells),
            )
        )

    batch_pure = sum(1 for perturbation in perturbations if perturbation.batch_pure)
    audit = Audit(
        transcriptome_input_rows=len(transcriptome.wells),
        transcriptome_control_rows=len(transcriptome.control_wells),
        transcriptome_treated_rows=len(transcriptome.treated_wells),
        transcriptome_distinct_wells=len({well.well_id for well in transcriptome.wells}),
        imaging_input_rows=len(imaging.wells),
        imaging_control_rows=len(imaging.control_wells),
        imaging_treated_rows=len(imaging.treated_wells),
        imaging_distinct_wells=len({well.well_id for well in imaging.wells}),
        transcriptome_perturbations=len(transcriptome_by_perturbation),
        imaging_perturbations=len(imaging_by_perturbation),
        admitted_perturbations=len(perturbations),
        transcriptome_plates=len({well.plate for well in transcriptome.wells}),
        imaging_plates=len({well.plate for well in imaging.wells}),
        imaging_batches=len({imaging_batches[well.plate] for well in imaging.wells}),
        batch_pure_perturbations=batch_pure,
        batch_mixed_perturbations=len(perturbations) - batch_pure,
        exclusion_counts=dict(sorted(exclusions.items())),
    )
    return Dataset(
        perturbations=tuple(perturbations),
        transcriptome_features=transcriptome.feature_names,
        imaging_features=imaging.feature_names,
        transcriptome_wells=transcriptome.wells,
        imaging_wells=imaging.wells,
        imaging_batch_of_plate=imaging_batches,
        audit=audit,
    )


def _imaging_batches(path: Path, contract: Contract) -> dict[str, str]:
    """Map each imaging assay plate to the plate map it belongs to."""
    header, rows = _read_csv_gz(path)
    plate_at = header.index("Metadata_Plate")
    map_at = header.index("Metadata_Plate_Map_Name")
    batches: dict[str, str] = {}
    for row in rows:
        batches.setdefault(row[plate_at], row[map_at])
    return batches
