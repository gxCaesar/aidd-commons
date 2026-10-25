"""Fetch, cache and parse the declared PubChem BioAssay records.

Each declared assay contributes two archived members, read out of two ranged
container zips with the reader in `ranged_zip.py`: the per-assay result CSV
and the per-assay description XML. Both are cached verbatim under
``.cache/assay_endpoint_controls/`` and re-validated against the frozen byte
lengths on every run, so a cache written under an older rule is re-checked
rather than silently trusted.

The parser is column-name driven. It does not assume that a row is a
measurement until it has found a compound identifier, an inline structure, a
non-empty activity outcome and at least the declared number of distinct
concentrations. Rows that fail any of those tests are counted and dropped,
never repaired.
"""

from __future__ import annotations

import csv
import gzip
import io
import re
import urllib.request
import zlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import unescape

from rdkit import Chem

from .protocol import (
    ASSAYS,
    CONTAINER_BYTES,
    DATA_FTP_BASE,
    DECLARED_ASSAYS,
    DESCRIPTION_FTP_BASE,
    MINIMUM_CONCENTRATIONS,
    AssaySpec,
    container_url,
)
from .ranged_zip import RemoteZipError, ZipEntry, read_central_directory, read_member

#: The four longitudes of a PubChem assay result row that every declared
#: assay shares.
RESULT_TAG = "PUBCHEM_RESULT_TAG"
SUBSTANCE_ID = "PUBCHEM_SID"
COMPOUND_ID = "PUBCHEM_CID"
INLINE_STRUCTURE = "PUBCHEM_EXT_DATASOURCE_SMILES"
ACTIVITY_OUTCOME = "PUBCHEM_ACTIVITY_OUTCOME"
ACTIVITY_SCORE = "PUBCHEM_ACTIVITY_SCORE"
ASSAYDATA_COMMENT = "PUBCHEM_ASSAYDATA_COMMENT"

#: Rows whose result tag starts with this are the per-column metadata rows
#: that the PubChem CSV format puts between the header and the data.
METADATA_TAG_PREFIX = "RESULT_"

#: A per-concentration column names its concentration in the column header.
#: The unit is recorded in the header too, and is normalised to micromolar.
CONCENTRATION_PATTERN = re.compile(
    r"(?i)(?:inhibition|activation|effect|response|activity)"
    r"[ _]*(?:at)?[ _]*([0-9]*\.?[0-9]+)[ _]*"
    r"(nanom|nanomolar|microm|micromolar|nm|um|µm)\b"
)

#: Protocol text is carried in the description XML as one element per line.
_PROTOCOL_ELEMENT = "PC-AssayDescription_protocol_E"
_NAME_ELEMENT = "PC-AssayDescription_name"
_COMMENT_ELEMENT = "PC-AssayDescription_comment_E"

class DataContractError(ValueError):
    """Raised when a fetched or cached record violates the declared contract."""


class DataDownloadError(RuntimeError):
    """Raised when an official PubChem file cannot be obtained or cached."""


@dataclass(frozen=True)
class ConcentrationPoint:
    """One per-concentration measurement."""

    concentration_um: float
    value: float | None
    category: str | None

    @property
    def is_numeric(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class MeasurementRow:
    """One archived row: one compound in one assay."""

    compound_id: str
    substance_id: str
    smiles: str
    outcome: str
    activity_score: float | None
    comment: str
    qualifier: str
    endpoints: Mapping[str, float]
    points: tuple[ConcentrationPoint, ...]
    replicate_count: int | None
    extra_numbers: Mapping[str, float] = field(default_factory=dict)

    @property
    def numeric_point_count(self) -> int:
        return sum(1 for point in self.points if point.is_numeric)

    @property
    def distinct_concentration_count(self) -> int:
        return len({round(point.concentration_um, 12) for point in self.points})


@dataclass(frozen=True)
class DataAudit:
    input_rows: int
    retained_rows: int
    admitted_compounds: int
    exclusion_counts: Mapping[str, int]


@dataclass(frozen=True)
class AssayDataset:
    """One assay, parsed and audited."""

    spec: AssaySpec
    name: str
    protocol_text: str
    comment_text: str
    rows: tuple[MeasurementRow, ...]
    audit: DataAudit


def _fetch_range(url: str, start: int, end: int) -> bytes:
    request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload: bytes = response.read()
            return payload
    except OSError as error:
        raise DataDownloadError(f"could not read bytes {start}-{end} of {url}: {error}") from error


def _read_member(
    url: str,
    container_bytes: int,
    member: str,
    compressed_bytes: int,
    member_bytes: int,
    expected_crc: int,
) -> bytes:
    """Read one member out of a ranged container and undo its gzip layer.

    The returned bytes are the archived record itself, not the gzip member.
    """
    entries = read_central_directory(url, container_bytes, fetch=_fetch_range)
    if member not in entries:
        raise DataContractError(f"member {member} is not present in {url}")
    entry = entries[member]
    if entry.compressed_size != compressed_bytes:
        raise DataContractError(
            f"member {member} of {url} is stored in {entry.compressed_size} bytes, "
            f"the protocol declares {compressed_bytes}"
        )
    if entry.uncompressed_size != member_bytes:
        raise DataContractError(
            f"member {member} of {url} holds {entry.uncompressed_size} bytes, "
            f"the protocol declares {member_bytes}"
        )
    if entry.crc32 != expected_crc:
        raise DataContractError(
            f"member {member} of {url} has CRC-32 {entry.crc32}, "
            f"the protocol declares {expected_crc}"
        )
    payload = read_member(url, entry, fetch=_fetch_range)
    if len(payload) != member_bytes:
        raise DataContractError(
            f"member {member} of {url} decompressed to {len(payload)} bytes, "
            f"the protocol declares {member_bytes}"
        )
    return payload


def _gunzip(payload: bytes, label: str) -> bytes:
    try:
        return gzip.decompress(payload)
    except (OSError, zlib.error) as error:
        raise DataContractError(f"{label} is not a readable gzip member: {error}") from error


def _write_atomically(path: Path, payload: bytes) -> None:
    """Write a cache file through a temporary name, so an interrupted run
    leaves either the old file or the new one and never a half-written one."""
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(payload)
    temporary.replace(path)


def download_and_cache_assays(cache_dir: Path) -> tuple[Path, ...]:
    """Fetch every declared assay record and cache it under ``cache_dir``.

    The download is resumable: a cache file that already holds exactly the
    frozen byte length is left alone and is not fetched again, and a file that
    is being written is written through a ``.part`` name so an interrupted run
    does not leave a truncated cache behind. Every run re-reads the cached
    bytes and re-checks their length against the protocol.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for aid in DECLARED_ASSAYS:
        spec = ASSAYS[aid]
        data_bytes = spec.source_data.record_bytes
        description_bytes = spec.source_description.record_bytes
        data_path = cache_dir / f"aid{aid}.csv"
        description_path = cache_dir / f"aid{aid}.descr.xml"
        if not _cache_is_valid(data_path, data_bytes):
            payload = _read_member(
                container_url(DATA_FTP_BASE, spec.source_data.container),
                CONTAINER_BYTES[spec.source_data.container]["data"],
                spec.source_data.member,
                spec.source_data.compressed_bytes,
                spec.source_data.member_bytes,
                spec.source_data.crc32,
            )
            record = _gunzip(payload, spec.source_data.member)
            if len(record) != data_bytes:
                raise DataContractError(
                    f"member {spec.source_data.member} holds {len(record)} archived bytes, "
                    f"the protocol declares {data_bytes}"
                )
            _write_atomically(data_path, record)
        if not _cache_is_valid(description_path, description_bytes):
            payload = _read_member(
                container_url(DESCRIPTION_FTP_BASE, spec.source_description.container),
                CONTAINER_BYTES[spec.source_description.container]["description"],
                spec.source_description.member,
                spec.source_description.compressed_bytes,
                spec.source_description.member_bytes,
                spec.source_description.crc32,
            )
            record = _gunzip(payload, spec.source_description.member)
            if len(record) != description_bytes:
                raise DataContractError(
                    f"member {spec.source_description.member} holds {len(record)} archived bytes, "
                    f"the protocol declares {description_bytes}"
                )
            _write_atomically(description_path, record)
        written.extend((data_path, description_path))
    return tuple(written)


def _cache_is_valid(path: Path, expected_bytes: int) -> bool:
    return path.is_file() and path.stat().st_size == expected_bytes


def _xml_text(xml: str, element: str) -> str:
    pattern = re.compile(
        rf"<{re.escape(element)}(?:\s[^>]*)?>(?P<text>.*?)</{re.escape(element)}>", re.S
    )
    return "\n".join(
        " ".join(unescape(match.group("text")).split()) for match in pattern.finditer(xml)
    )


def _element_text(xml: str, element: str) -> str:
    match = re.search(
        rf"<{re.escape(element)}(?:\s[^>]*)?>(?P<text>.*?)</{re.escape(element)}>", xml, re.S
    )
    if match is None:
        return ""
    return " ".join(unescape(match.group("text")).split())


def _parse_concentration_column(header: str) -> float | None:
    """The concentration, in micromolar, that a per-concentration column names."""
    match = CONCENTRATION_PATTERN.search(header)
    if match is None:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit in ("nanom", "nanomolar", "nm"):
        return value * 1e-3
    return value


def _parse_number(raw: str) -> float | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def _valid_structure(smiles: str) -> bool:
    if not smiles:
        return False
    molecule = Chem.MolFromSmiles(smiles)
    return molecule is not None and molecule.GetNumAtoms() > 0


def _row_exclusion(row: Mapping[str, str], spec: AssaySpec) -> str | None:
    compound_id = (row.get(COMPOUND_ID) or "").strip()
    if not compound_id:
        return "no_compound_identifier"
    if not compound_id.isdigit():
        return "malformed_compound_identifier"
    if not _valid_structure((row.get(INLINE_STRUCTURE) or "").strip()):
        return "missing_or_invalid_inline_structure"
    if not (row.get(ACTIVITY_OUTCOME) or "").strip():
        return "no_activity_outcome"
    if not any(
        _parse_number(row.get(column, "")) is not None for column in spec.endpoint_columns
    ):
        return "no_endpoint_value"
    return None


def parse_assay_csv(text: str, spec: AssaySpec) -> tuple[tuple[MeasurementRow, ...], DataAudit]:
    """Parse one archived per-assay result CSV into admitted rows plus an audit.

    The PubChem CSV format puts a header row, then one metadata row per
    column group (``RESULT_TYPE``, ``RESULT_DESCR``, ``RESULT_UNIT`` and
    sometimes more), then the data rows. The metadata rows are recognised by
    their result tag and are never admitted.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise DataContractError(f"assay {spec.aid}: the archived CSV has no header row")
    header = list(reader.fieldnames)
    for required in (RESULT_TAG, SUBSTANCE_ID, COMPOUND_ID, INLINE_STRUCTURE, ACTIVITY_OUTCOME):
        if required not in header:
            raise DataContractError(f"assay {spec.aid}: the archived CSV has no {required} column")
    if spec.qualifier_column not in header:
        raise DataContractError(
            f"assay {spec.aid}: the archived CSV has no {spec.qualifier_column} qualifier column"
        )
    for column in spec.endpoint_columns:
        if column not in header:
            raise DataContractError(
                f"assay {spec.aid}: the archived CSV has no {column} endpoint column"
            )

    concentration_columns: list[tuple[str, float]] = []
    for column in header:
        concentration = _parse_concentration_column(column)
        if concentration is not None:
            concentration_columns.append((column, concentration))
    if len(concentration_columns) < MINIMUM_CONCENTRATIONS:
        raise DataContractError(
            f"assay {spec.aid}: the archived CSV carries {len(concentration_columns)} "
            f"per-concentration columns, the protocol requires at least "
            f"{MINIMUM_CONCENTRATIONS}"
        )

    exclusions: Counter[str] = Counter()
    rows: list[MeasurementRow] = []
    input_rows = 0
    seen_compounds: set[str] = set()
    for raw_row in reader:
        tag = (raw_row.get(RESULT_TAG) or "").strip()
        if tag.startswith(METADATA_TAG_PREFIX):
            continue
        input_rows += 1
        exclusion = _row_exclusion(raw_row, spec)
        if exclusion is not None:
            exclusions[exclusion] += 1
            continue
        compound_id = (raw_row.get(COMPOUND_ID) or "").strip()
        if compound_id in seen_compounds:
            exclusions["repeated_compound"] += 1
            continue
        seen_compounds.add(compound_id)

        points: list[ConcentrationPoint] = []
        for column, concentration in concentration_columns:
            raw_value = (raw_row.get(column) or "").strip()
            number = _parse_number(raw_value)
            category = None if number is not None else (raw_value or None)
            if number is None and raw_value in ("", "."):
                number = None
                category = None
            points.append(
                ConcentrationPoint(
                    concentration_um=concentration,
                    value=number,
                    category=category,
                )
            )
        distinct = len({round(point.concentration_um, 12) for point in points})
        if distinct < MINIMUM_CONCENTRATIONS:
            exclusions["too_few_concentrations"] += 1
            seen_compounds.discard(compound_id)
            continue

        endpoints: dict[str, float] = {}
        for column, label in zip(spec.endpoint_columns, spec.endpoint_labels, strict=True):
            number = _parse_number(raw_row.get(column, ""))
            if number is not None:
                endpoints[label] = number

        rows.append(
            MeasurementRow(
                compound_id=compound_id,
                substance_id=(raw_row.get(SUBSTANCE_ID) or "").strip(),
                smiles=(raw_row.get(INLINE_STRUCTURE) or "").strip(),
                outcome=(raw_row.get(ACTIVITY_OUTCOME) or "").strip(),
                activity_score=_parse_number(raw_row.get(ACTIVITY_SCORE, "")),
                comment=(raw_row.get(ASSAYDATA_COMMENT) or "").strip(),
                qualifier=(raw_row.get(spec.qualifier_column) or "").strip(),
                endpoints=endpoints,
                points=tuple(points),
                replicate_count=_replicate_count(raw_row, spec),
                extra_numbers={
                    column: number
                    for column in spec.hill_parameter_columns
                    if (number := _parse_number(raw_row.get(column, ""))) is not None
                },
            )
        )

    audit = DataAudit(
        input_rows=input_rows,
        retained_rows=len(rows),
        admitted_compounds=len({row.compound_id for row in rows}),
        exclusion_counts=dict(sorted(exclusions.items())),
    )
    return tuple(rows), audit


def _replicate_count(row: Mapping[str, str], spec: AssaySpec) -> int | None:
    """The number the archive itself records for one row.

    Which number this is depends on the assay, so the column is declared per
    assay: most of these assays record the number of data points in the
    compound's curve, and the zebrafish assay records the number of
    independent determinations instead.
    """
    if spec.determination_column not in row:
        return None
    number = _parse_number(row.get(spec.determination_column, ""))
    if number is None:
        return None
    return int(number)


def load_cached_assays(cache_dir: Path) -> dict[int, AssayDataset]:
    """Load every declared assay from the cache, re-checking the frozen lengths."""
    datasets: dict[int, AssayDataset] = {}
    for aid in DECLARED_ASSAYS:
        spec = ASSAYS[aid]
        data_path = cache_dir / f"aid{aid}.csv"
        description_path = cache_dir / f"aid{aid}.descr.xml"
        for path, expected in (
            (data_path, spec.source_data.record_bytes),
            (description_path, spec.source_description.record_bytes),
        ):
            if not path.is_file():
                raise DataContractError(
                    f"cache file {path} is not present; run "
                    "'python labs/assay_endpoint_controls/run_lab.py download' first"
                )
            actual = path.stat().st_size
            if actual != expected:
                raise DataContractError(
                    f"cache file {path} holds {actual} bytes, the protocol declares {expected}"
                )
        rows, audit = parse_assay_csv(data_path.read_text(encoding="utf-8"), spec)
        xml = description_path.read_text(encoding="utf-8")
        datasets[aid] = AssayDataset(
            spec=spec,
            name=_element_text(xml, _NAME_ELEMENT) or spec.name,
            protocol_text=_xml_text(xml, _PROTOCOL_ELEMENT),
            comment_text=_xml_text(xml, _COMMENT_ELEMENT),
            rows=rows,
            audit=audit,
        )
    return datasets


def control_mentions(protocol_text: str, keywords: Sequence[str]) -> tuple[str, ...]:
    """The frozen control keywords that the archived protocol text contains."""
    lowered = protocol_text.lower()
    return tuple(keyword for keyword in keywords if keyword in lowered)


def declared_container_bytes(spec: AssaySpec) -> Mapping[str, int]:
    """The frozen container lengths for one assay, for the protocol check."""
    return {
        "data": CONTAINER_BYTES[spec.source_data.container]["data"],
        "description": CONTAINER_BYTES[spec.source_description.container]["description"],
    }


def zip_entry_summary(entries: Mapping[str, ZipEntry], member: str) -> str:
    """A short human-readable line about one member of a container."""
    entry = entries[member]
    return (
        f"{member}: {entry.uncompressed_size} bytes stored, "
        f"{entry.compressed_size} bytes in the container, CRC-32 {entry.crc32}"
    )


__all__ = [
    "AssayDataset",
    "ConcentrationPoint",
    "DataAudit",
    "DataContractError",
    "DataDownloadError",
    "MeasurementRow",
    "RemoteZipError",
    "control_mentions",
    "download_and_cache_assays",
    "load_cached_assays",
    "parse_assay_csv",
]
