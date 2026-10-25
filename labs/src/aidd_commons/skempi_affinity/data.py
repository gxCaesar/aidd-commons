"""Fetch and align the mirror's ragged JSONL rows without discarding partial records."""

from __future__ import annotations

import json
import math
import urllib.request
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .protocol import EXPECTED_BYTES, HEADER, SOURCE_URL

CACHE_FILENAME = "labeled_skempi2_skempi_v2.csv.jsonl"
SOURCE_FILE = "labeled/skempi2/skempi_v2.csv"


class DataContractError(ValueError):
    """A source record does not match the frozen representation."""


@dataclass(frozen=True)
class Record:
    row_index: int
    complex_id: str
    interaction_class: str
    protein_group: str
    mutant_m: float | None
    wild_type_m: float | None
    field_count: int
    mutation: str = ""
    method: str = ""
    wild_type_text: str = ""
    mutant_text: str = ""

    @property
    def complete(self) -> bool:
        return self.mutant_m is not None and self.wild_type_m is not None


@dataclass(frozen=True)
class Dataset:
    records: tuple[Record, ...]
    field_counts: dict[int, int]
    fragmented_rows: int


Fetcher = Callable[[str], bytes]


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=90) as response:
        return cast(bytes, response.read())


def validate_size(payload: bytes) -> None:
    if len(payload) != EXPECTED_BYTES:
        raise DataContractError(
            f"snapshot is {len(payload)} bytes; protocol requires {EXPECTED_BYTES}"
        )


def download_and_cache(cache_dir: Path, *, fetch: Fetcher = _fetch) -> Path:
    """Use a validated cache or fetch once; recheck its byte length on every call."""
    path = cache_dir / CACHE_FILENAME
    if path.is_file():
        validate_size(path.read_bytes())
        return path
    try:
        payload = fetch(SOURCE_URL)
    except OSError as error:
        raise DataContractError("snapshot download failed") from error
    validate_size(payload)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    validate_size(path.read_bytes())
    return path


def _affinity(value: str, row_index: int) -> float | None:
    if not value:
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise DataContractError(f"row {row_index}: invalid parsed affinity") from error
    if not math.isfinite(number) or number <= 0:
        raise DataContractError(f"row {row_index}: nonpositive or nonfinite parsed affinity")
    return number


def parse_payload(payload: bytes) -> Dataset:
    header = HEADER.split(";")
    records: list[Record] = []
    widths: Counter[int] = Counter()
    fragmented_rows = 0
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise DataContractError("snapshot is not UTF-8") from error
    for index, line in enumerate(lines):
        try:
            outer: Any = json.loads(line)
        except ValueError as error:
            raise DataContractError(f"row {index}: invalid JSON") from error
        if not isinstance(outer, dict) or set(outer) != {
            "dataset_id", "row", "row_index", "source_file"
        }:
            raise DataContractError(f"row {index}: wrong envelope")
        if (
            outer["dataset_id"] != "skempi2"
            or outer["row_index"] != index
            or outer["source_file"] != SOURCE_FILE
        ):
            raise DataContractError(f"row {index}: wrong provenance or order")
        raw = outer["row"]
        if not isinstance(raw, dict) or HEADER not in raw:
            raise DataContractError(f"row {index}: wrong 29-field header")
        fragments = {key: val for key, val in raw.items() if key != HEADER}
        if any(
            not isinstance(key, str)
            or not key.startswith("column_")
            or not key.removeprefix("column_").isdigit()
            or not isinstance(val, str)
            for key, val in fragments.items()
        ):
            raise DataContractError(f"row {index}: unexpected overflow fragment")
        fragmented_rows += bool(fragments)
        value = raw[HEADER]
        if not isinstance(value, str):
            raise DataContractError(f"row {index}: value is not text")
        fields = value.split(";")
        width = len(fields)
        if width > len(header):
            raise DataContractError(f"row {index}: wider than header")
        widths[width] += 1
        fields += [""] * (len(header) - width)
        aligned = dict(zip(header, fields, strict=True))
        complex_id = aligned["#Pdb"]
        if not complex_id:
            raise DataContractError(f"row {index}: missing complex")
        records.append(
            Record(
                row_index=index,
                complex_id=complex_id,
                interaction_class=aligned["Hold_out_type"],
                protein_group=aligned["Hold_out_proteins"],
                mutant_m=_affinity(aligned["Affinity_mut_parsed"], index),
                wild_type_m=_affinity(aligned["Affinity_wt_parsed"], index),
                field_count=width,
                mutation=aligned["Mutation(s)_PDB"],
                method=aligned["Method"],
                wild_type_text=aligned["Affinity_wt (M)"],
                mutant_text=aligned["Affinity_mut (M)"],
            )
        )
    if not records:
        raise DataContractError("snapshot has no rows")
    return Dataset(tuple(records), dict(sorted(widths.items())), fragmented_rows)


def load_cached(cache_dir: Path) -> Dataset:
    path = cache_dir / CACHE_FILENAME
    if not path.is_file():
        raise DataContractError("snapshot is not cached; run download first")
    payload = path.read_bytes()
    validate_size(payload)
    return parse_payload(payload)
