"""Reading the public records the objective ladder is built from.

Four archives are read, each under its own terms: UniProtKB for the sequence,
the enzyme annotation and the function annotation; the AlphaFold database for
a predicted structure; the Protein Data Bank for a deposited structure, its
bound components and its coordinates; and SKEMPI 2.0 for measured affinity
changes.

The affinity table is read through the reader the affinity laboratory already
ships, because it is the same mirror and a second reader for one file format
would drift from it. That reader validates the snapshot's byte length, and
this laboratory keeps its copy under its own cache so the two do not write to
one place.

Every retrieval is cached and every cached file records the date it was read,
so a second run does not silently read a different record from the one the
summary was computed from.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from aidd_commons.skempi_affinity import data as skempi_data

USER_AGENT = "aidd-commons-objective-ladder/1.0 (offline teaching laboratory)"

DEFAULT_CACHE_DIR = Path(".cache/objective_ladder")

#: The affinity snapshot keeps the file name and the byte-length check of the
#: laboratory that already reads it.
SKEMPI_SUBDIR = "skempi"


class DataContractError(RuntimeError):
    """A public record could not be read, or did not carry what was expected."""


@dataclass(frozen=True)
class Retrieval:
    """One record, where it came from, and when it was read."""

    key: str
    url: str
    read_on: str
    byte_length: int


def _cache_name(url: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", url)[-120:]


def fetch(url: str, cache_dir: Path, *, suffix: str = "") -> bytes:
    """Read a URL, using the cache when it already holds a non-empty copy."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{_cache_name(url)}{suffix}"
    if target.exists() and target.stat().st_size > 0:
        cached: bytes = target.read_bytes()
        return cached
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload: bytes = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise DataContractError(f"could not read {url}: {error}") from error
    if not payload:
        raise DataContractError(f"the archive returned nothing for {url}")
    target.write_bytes(payload)
    return payload


def fetch_json(url: str, cache_dir: Path) -> Any:
    """Read a JSON document."""
    payload = fetch(url, cache_dir, suffix=".json")
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DataContractError(
            f"the archive returned unreadable JSON for {url}: {error}"
        ) from error


def read_date(cache_dir: Path) -> str:
    """The date recorded beside the cached retrievals."""
    marker = cache_dir / "read_on.txt"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    today = date.today().isoformat()
    cache_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text(today + "\n", encoding="utf-8")
    return today


# ---------------------------------------------------------------- UniProt


@dataclass(frozen=True)
class UniProtRecord:
    """What one accession carries."""

    accession: str
    name: str
    gene: str
    sequence_length: int
    sequence: str
    ec_numbers: tuple[str, ...]
    catalysis: tuple[str, ...]
    function_text: str
    url: str


def read_uniprot(accession: str, cache_dir: Path) -> UniProtRecord:
    """Read one accession from UniProtKB."""
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
    document = fetch_json(url, cache_dir)
    description = document.get("proteinDescription", {}) or {}
    recommended = description.get("recommendedName", {}) or {}
    name = recommended.get("fullName", {}) or {}
    ec_numbers: list[str] = []
    for item in recommended.get("ecNumbers") or ():
        value = str(item.get("value") or "")
        if value and value not in ec_numbers:
            ec_numbers.append(value)
    comments = document.get("comments") or []
    catalysis: list[str] = []
    for comment in comments:
        if comment.get("commentType") != "CATALYTIC ACTIVITY":
            continue
        reaction = comment.get("reaction") or {}
        number = str(reaction.get("ecNumber") or "")
        if number and number not in ec_numbers:
            ec_numbers.append(number)
        reaction_name = str(reaction.get("name") or "")
        if reaction_name:
            catalysis.append(reaction_name)
    function_text = ""
    for comment in comments:
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts") or []
            if texts:
                function_text = str(texts[0].get("value", "")).strip()
            break
    genes = document.get("genes") or []
    gene = ""
    if genes:
        gene = str((genes[0].get("geneName", {}) or {}).get("value", ""))
    sequence = str((document.get("sequence", {}) or {}).get("value") or "")
    return UniProtRecord(
        accession=accession,
        name=str(name.get("value", "")),
        gene=gene,
        sequence_length=int((document.get("sequence", {}) or {}).get("length") or 0),
        sequence=sequence,
        ec_numbers=tuple(ec_numbers),
        catalysis=tuple(catalysis),
        function_text=function_text,
        url=url,
    )


# ------------------------------------------------------- AlphaFold database


@dataclass(frozen=True)
class AlphaFoldRecord:
    """What the model archive holds for one accession."""

    accession: str
    entry_id: str
    model_created: str
    global_metric: float | None
    sequence_length: int
    url: str


def read_alphafold(accession: str, cache_dir: Path) -> AlphaFoldRecord | None:
    """Read the model archive entry for one accession, if it holds one."""
    url = f"https://alphafold.ebi.ac.uk/api/prediction/{accession}"
    document = fetch_json(url, cache_dir)
    if not isinstance(document, list) or not document:
        return None
    entry = document[0]
    metric = entry.get("globalMetricValue")
    sequence = entry.get("uniprotSequence") or ""
    return AlphaFoldRecord(
        accession=accession,
        entry_id=str(entry.get("entryId", "")),
        model_created=str(entry.get("modelCreatedDate", ""))[:10],
        global_metric=float(metric) if metric is not None else None,
        sequence_length=len(sequence),
        url=url,
    )


# ----------------------------------------------------- Protein Data Bank


@dataclass(frozen=True)
class StructureRecord:
    """What the archive holds for one deposited structure."""

    entry_id: str
    method: str
    ligand_ids: tuple[str, ...]
    polymer_entity_ids: tuple[str, ...]
    deposition_date: str
    url: str


def read_structure(entry_id: str, cache_dir: Path) -> StructureRecord:
    """Read one deposited structure's header."""
    url = f"https://data.rcsb.org/rest/v1/core/entry/{entry_id}"
    document = fetch_json(url, cache_dir)
    container = document.get("rcsb_entry_container_identifiers", {}) or {}
    experiments = document.get("exptl") or []
    method = str(experiments[0].get("method", "")) if experiments else ""
    information = document.get("rcsb_entry_info", {}) or {}
    accession = document.get("rcsb_accession_info", {}) or {}
    return StructureRecord(
        entry_id=entry_id,
        method=method,
        ligand_ids=tuple(information.get("nonpolymer_bound_components") or ()),
        polymer_entity_ids=tuple(container.get("polymer_entity_ids") or ()),
        deposition_date=str(accession.get("deposit_date", "")),
        url=url,
    )


def find_structures(accession: str, cache_dir: Path, *, rows: int = 800) -> list[str]:
    """List the deposited structures that name one accession."""
    query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": (
                    "rcsb_polymer_entity_container_identifiers"
                    ".reference_sequence_identifiers.database_accession"
                ),
                "operator": "exact_match",
                "value": accession,
            },
        },
        "return_type": "entry",
        "request_options": {"paginate": {"start": 0, "rows": rows}},
    }
    url = "https://search.rcsb.org/rcsbsearch/v2/query"
    payload = json.dumps(query).encode("utf-8")
    cache_dir.mkdir(parents=True, exist_ok=True)
    # The cache is per accession, or every target would read the first answer.
    target = cache_dir / f"search_{accession}.json"
    if target.exists() and target.stat().st_size > 0:
        document = json.loads(target.read_text(encoding="utf-8"))
    else:
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise DataContractError(f"could not search the structure archive: {error}") from error
        target.write_bytes(raw)
        document = json.loads(raw.decode("utf-8"))
    return [str(item["identifier"]) for item in document.get("result_set", [])]


def read_coordinates(entry_id: str, cache_dir: Path) -> str:
    """Read the deposited coordinates of one structure as text."""
    url = f"https://files.rcsb.org/download/{entry_id}.cif"
    payload = fetch(url, cache_dir, suffix=".cif")
    return payload.decode("utf-8", errors="replace")


def read_entry_accessions(entry_id: str, cache_dir: Path) -> tuple[str, ...]:
    """Read the accessions the entry's polymer entities actually reference.

    The search service returns a candidate list, so every structure the
    laboratory relies on is checked against the entry itself before it is
    treated as a structure of the target.
    """
    entry = fetch_json(f"https://data.rcsb.org/rest/v1/core/entry/{entry_id}", cache_dir)
    identifiers = entry.get("rcsb_entry_container_identifiers", {}) or {}
    accessions: list[str] = []
    for entity_id in identifiers.get("polymer_entity_ids") or ():
        entity = fetch_json(
            f"https://data.rcsb.org/rest/v1/core/polymer_entity/{entry_id}/{entity_id}",
            cache_dir,
        )
        container = entity.get("rcsb_polymer_entity_container_identifiers", {}) or {}
        for reference in container.get("reference_sequence_identifiers") or ():
            if str(reference.get("database_name")) != "UniProt":
                continue
            accession = str(reference.get("database_accession") or "")
            if accession and accession not in accessions:
                accessions.append(accession)
    return tuple(accessions)


# ---------------------------------------------------------------- SKEMPI


@dataclass(frozen=True)
class AffinityRecord:
    """One row of the affinity archive, with what it does and does not carry."""

    structure_code: str
    protein_group: str
    mutation: str
    affinity_wild_type: float | None
    affinity_mutant: float | None
    wild_type_text: str
    mutant_text: str
    method: str
    field_count: int

    @property
    def carries_a_value(self) -> bool:
        """Whether the row carries an affinity quantity for either side."""
        return self.affinity_wild_type is not None or self.affinity_mutant is not None

    @property
    def carries_a_change(self) -> bool:
        """Whether the row carries both sides of a change."""
        return self.affinity_wild_type is not None and self.affinity_mutant is not None


def read_affinity_records(cache_dir: Path) -> list[AffinityRecord]:
    """Read every row of the affinity archive.

    The snapshot is the one the affinity laboratory already reads, and the
    reader that ships with it aligns the mirror's ragged rows and checks the
    snapshot's byte length. This function only translates the rows it returns
    into the shape the ladder reads.
    """
    dataset = skempi_data.load_cached(cache_dir / SKEMPI_SUBDIR)
    records: list[AffinityRecord] = []
    for row in dataset.records:
        code = row.complex_id.split("_")[0]
        if not code or not code[0].isdigit():
            continue
        records.append(
            AffinityRecord(
                structure_code=code,
                protein_group=row.protein_group,
                mutation=row.mutation,
                affinity_wild_type=row.wild_type_m,
                affinity_mutant=row.mutant_m,
                wild_type_text=row.wild_type_text,
                mutant_text=row.mutant_text,
                method=row.method,
                field_count=row.field_count,
            )
        )
    return records


def download_affinity_snapshot(cache_dir: Path) -> Path:
    """Fetch the affinity snapshot once, and check its byte length on every call."""
    return skempi_data.download_and_cache(cache_dir / SKEMPI_SUBDIR)
