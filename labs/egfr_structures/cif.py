"""Read the parts of a PDBx/mmCIF entry that the EGFR structure labs need.

Standard library for parsing, NumPy only for superposition. The reader keeps the
first model, keeps atoms whose alternate location is absent or 'A', and counts the
atoms it set aside so that choice is visible rather than silent.

Residue numbers in a deposited file are the depositor's numbering. The labs never
compare residues across entries by that number. They map every residue to the
UniProt reference sequence through the entry's own _struct_ref_seq alignment, and
check that the mapped landmark residues have the expected residue names.
"""

from __future__ import annotations

import json
import math
import stat
from dataclasses import dataclass
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parent
MANIFEST = LAB / "entries.json"

# UniProt P00533 positions of residues the labs use as landmarks, and the residue
# each must be after mapping. A wrong numbering offset fails this check.
LANDMARKS = {
    745: "LYS",  # catalytic lysine
    762: "GLU",  # conserved glutamate on the C-helix
    790: "THR",  # gatekeeper
    793: "MET",  # hinge residue whose backbone NH faces the ligand
    855: "ASP",  # aspartate of the DFG motif
}

COVALENT_RADII = {"C": 0.76, "N": 0.71, "O": 0.66, "S": 1.05, "F": 0.57, "CL": 1.02}
BOND_TOLERANCE = 0.45


def tokenize(text: str) -> list[tuple[str, bool]]:
    """Split CIF text into (value, was_quoted) tokens."""
    tokens: list[tuple[str, bool]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith(";"):
            parts = [line[1:]]
            index += 1
            while index < len(lines) and not lines[index].startswith(";"):
                parts.append(lines[index])
                index += 1
            tokens.append(("\n".join(parts).strip(), True))
            index += 1
            continue
        position, length = 0, len(line)
        while position < length:
            char = line[position]
            if char.isspace():
                position += 1
                continue
            if char == "#":
                break
            if char in "'\"":
                end = position + 1
                while True:
                    end = line.find(char, end)
                    if end == -1:
                        raise ValueError(f"unterminated quote on line {index + 1}")
                    if end + 1 == length or line[end + 1].isspace():
                        break
                    end += 1
                tokens.append((line[position + 1 : end], True))
                position = end + 1
                continue
            end = position
            while end < length and not line[end].isspace():
                end += 1
            tokens.append((line[position:end], False))
            position = end
        index += 1
    return tokens


def parse(text: str) -> dict[str, list[dict[str, str | None]]]:
    """Return category -> rows. A key-value category becomes a single row."""

    def value(token: tuple[str, bool]) -> str | None:
        raw, quoted = token
        return None if not quoted and raw in ("?", ".") else raw

    def is_keyword(token: tuple[str, bool]) -> bool:
        raw, quoted = token
        return not quoted and (
            raw.startswith("_") or raw.lower() == "loop_" or raw.startswith("data_")
        )

    tokens = tokenize(text)
    categories: dict[str, list[dict[str, str | None]]] = {}
    index = 0
    while index < len(tokens):
        raw, quoted = tokens[index]
        if not quoted and raw.startswith("data_"):
            index += 1
        elif not quoted and raw.lower() == "loop_":
            index += 1
            tags: list[str] = []
            while index < len(tokens) and not tokens[index][1] and tokens[index][0].startswith("_"):
                tags.append(tokens[index][0])
                index += 1
            values: list[str | None] = []
            while index < len(tokens) and not is_keyword(tokens[index]):
                values.append(value(tokens[index]))
                index += 1
            if not tags or len(values) % len(tags):
                raise ValueError(f"loop {tags[:1]} has {len(values)} values for {len(tags)} tags")
            category = tags[0].split(".")[0]
            items = [tag.split(".", 1)[1] for tag in tags]
            width = len(items)
            for start in range(0, len(values), width):
                categories.setdefault(category, []).append(
                    dict(zip(items, values[start : start + width], strict=True))
                )
        elif not quoted and raw.startswith("_"):
            category, item = raw.split(".", 1)
            categories.setdefault(category, [{}])[0][item] = value(tokens[index + 1])
            index += 2
        else:
            raise ValueError(f"unexpected token {raw!r}")
    return categories


@dataclass(frozen=True)
class Atom:
    group: str
    element: str
    name: str
    resname: str
    chain: str
    seq: int
    xyz: tuple[float, float, float]
    occupancy: float
    b_factor: float


@dataclass(frozen=True)
class Segment:
    """One stretch of the deposited chain aligned to the reference sequence."""

    chain: str
    accession: str
    author_start: int
    author_end: int
    reference_start: int
    reference_end: int

    @property
    def offset(self) -> int:
        return self.reference_start - self.author_start


class Entry:
    def __init__(self, entry_id: str, text: str) -> None:
        self.id = entry_id
        self.categories = parse(text)
        self.atoms: list[Atom] = []
        self.set_aside_alternates = 0
        for row in self.categories["_atom_site"]:
            if row.get("pdbx_PDB_model_num") not in (None, "1"):
                continue
            if row["label_alt_id"] not in (None, "A"):
                self.set_aside_alternates += 1
                continue
            self.atoms.append(
                Atom(
                    group=str(row["group_PDB"]),
                    element=str(row["type_symbol"]).upper(),
                    name=str(row["auth_atom_id"]),
                    resname=str(row["auth_comp_id"]),
                    chain=str(row["auth_asym_id"]),
                    seq=int(str(row["auth_seq_id"])),
                    xyz=(
                        float(str(row["Cartn_x"])),
                        float(str(row["Cartn_y"])),
                        float(str(row["Cartn_z"])),
                    ),
                    occupancy=float(str(row["occupancy"])),
                    b_factor=float(str(row["B_iso_or_equiv"])),
                )
            )

    def one(self, category: str, item: str) -> str | None:
        rows = self.categories.get(category)
        return rows[0].get(item) if rows else None

    def rows(self, category: str) -> list[dict[str, str | None]]:
        return self.categories.get(category, [])

    # Evidence recorded by the depositor ------------------------------------------------

    def refinement(self) -> dict[str, float | str | None]:
        def number(item: str) -> float | None:
            raw = self.one("_refine", item)
            return None if raw is None else float(raw)

        return {
            "method": self.one("_exptl", "method"),
            "resolution": number("ls_d_res_high"),
            "r_work": number("ls_R_factor_R_work"),
            "r_free": number("ls_R_factor_R_free"),
        }

    def dates(self) -> dict[str, str | None]:
        revisions = [
            row["revision_date"]
            for row in self.rows("_pdbx_audit_revision_history")
            if row.get("revision_date")
        ]
        return {
            "deposited": self.one("_pdbx_database_status", "recvd_initial_deposition_date"),
            "latest_revision": max(str(date) for date in revisions) if revisions else None,
        }

    def title(self) -> str:
        return " ".join(str(self.one("_struct", "title") or "").split())

    def primary_citation(self) -> dict[str, str | None]:
        for row in self.rows("_citation"):
            if row.get("id") == "primary":
                return {
                    "title": " ".join(str(row.get("title") or "").split()),
                    "journal": row.get("journal_abbrev"),
                    "year": row.get("year"),
                    "doi": row.get("pdbx_database_id_DOI"),
                }
        return {"title": None, "journal": None, "year": None, "doi": None}

    def assemblies(self) -> list[dict[str, str | None]]:
        return [
            {
                "id": row.get("id"),
                "details": row.get("details"),
                "oligomeric_details": row.get("oligomeric_details"),
                "oligomeric_count": row.get("oligomeric_count"),
            }
            for row in self.rows("_pdbx_struct_assembly")
        ]

    def polymer_chains(self) -> list[str]:
        return sorted({atom.chain for atom in self.atoms if atom.group == "ATOM"})

    # Numbering -------------------------------------------------------------------------

    def segments(self) -> list[Segment]:
        segments = []
        for row in self.rows("_struct_ref_seq"):
            segments.append(
                Segment(
                    chain=str(row["pdbx_strand_id"]),
                    accession=str(row["pdbx_db_accession"]),
                    author_start=int(str(row["pdbx_auth_seq_align_beg"])),
                    author_end=int(str(row["pdbx_auth_seq_align_end"])),
                    reference_start=int(str(row["db_align_beg"])),
                    reference_end=int(str(row["db_align_end"])),
                )
            )
        return segments

    def to_reference(self, chain: str, author_seq: int) -> int | None:
        for segment in self.segments():
            if segment.chain == chain and segment.author_start <= author_seq <= segment.author_end:
                return author_seq + segment.offset
        return None

    def engineered_differences(self) -> list[dict[str, str | None]]:
        return [
            {
                "reference_residue": row.get("db_mon_id"),
                "deposited_residue": row.get("mon_id"),
                "reference_position": row.get("pdbx_seq_db_seq_num"),
                "details": row.get("details"),
            }
            for row in self.rows("_struct_ref_seq_dif")
        ]

    def unobserved_residues(self) -> list[int]:
        """Reference positions of polymer residues the model does not contain."""
        positions = []
        for row in self.rows("_pdbx_unobs_or_zero_occ_residues"):
            if row.get("polymer_flag") != "Y" or row.get("occupancy_flag") != "1":
                continue
            mapped = self.to_reference(str(row["auth_asym_id"]), int(str(row["auth_seq_id"])))
            if mapped is not None:
                positions.append(mapped)
        return sorted(positions)

    # Atom selections -------------------------------------------------------------------

    def protein(self) -> list[Atom]:
        return [atom for atom in self.atoms if atom.group == "ATOM" and atom.element != "H"]

    def waters(self) -> list[Atom]:
        return [atom for atom in self.atoms if atom.resname == "HOH"]

    def ligand(self, comp_id: str) -> list[Atom]:
        return [
            atom
            for atom in self.atoms
            if atom.group == "HETATM" and atom.resname == comp_id and atom.element != "H"
        ]

    def residue_names(self) -> dict[int, str]:
        """Reference position -> residue name, for observed protein residues."""
        names: dict[int, str] = {}
        for atom in self.protein():
            mapped = self.to_reference(atom.chain, atom.seq)
            if mapped is not None:
                names[mapped] = atom.resname
        return names

    def atom_at(self, reference_seq: int, name: str) -> Atom | None:
        for atom in self.protein():
            if atom.name == name and self.to_reference(atom.chain, atom.seq) == reference_seq:
                return atom
        return None

    def ca_by_reference(self) -> dict[int, tuple[float, float, float]]:
        coords = {}
        for atom in self.protein():
            if atom.name == "CA":
                mapped = self.to_reference(atom.chain, atom.seq)
                if mapped is not None:
                    coords[mapped] = atom.xyz
        return coords


# Manifest and loading ----------------------------------------------------------------


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def mismatched_files(data: dict, lab: Path = LAB) -> list[str]:
    """Diagnose file/metadata mismatches, without certifying byte identity."""
    failures: list[str] = []
    for record in data["entries"]:
        path = lab / record["file"]
        entry_id = record["id"]
        try:
            file_stat = path.lstat()
        except OSError:
            failures.append(f"{entry_id}: input is not a readable regular file")
            continue
        if not stat.S_ISREG(file_stat.st_mode):
            failures.append(f"{entry_id}: input is not a regular file")
            continue
        if file_stat.st_size != record["size_bytes"]:
            failures.append(f"{entry_id}: byte size differs from the declared size")
            continue
        try:
            categories = parse(path.read_text(encoding="utf-8"))
            identities = categories.get("_entry", [])
            if len(identities) != 1 or identities[0].get("id") != entry_id:
                failures.append(f"{entry_id}: deposited entry identifier differs")
                continue
            status = categories.get("_pdbx_database_status", [])
            if (
                len(status) != 1
                or status[0].get("entry_id") != entry_id
                or status[0].get("recvd_initial_deposition_date") != record["deposited_on"]
            ):
                failures.append(f"{entry_id}: deposition metadata differs")
                continue
            revisions = categories.get("_pdbx_audit_revision_history", [])
            latest = max(revisions, key=lambda row: int(str(row["ordinal"])), default={})
            revision = {
                key: latest.get(key)
                for key in ("major_revision", "minor_revision", "revision_date")
            }
            if revision != record["latest_revision"]:
                failures.append(f"{entry_id}: latest deposited revision differs")
        except (OSError, UnicodeError, ValueError, KeyError, IndexError):
            failures.append(f"{entry_id}: PDBx/mmCIF metadata cannot be read")
    return failures


def load_entry(record: dict) -> Entry:
    return Entry(record["id"], (LAB / record["file"]).read_text(encoding="utf-8"))


def load_all() -> dict[str, Entry]:
    return {record["id"]: load_entry(record) for record in manifest()["entries"]}


# Geometry ----------------------------------------------------------------------------


def distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return math.dist(left, right)


def kabsch(mobile: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rotation and translation that move `mobile` onto `target` in least squares."""
    mobile_centre = mobile.mean(axis=0)
    target_centre = target.mean(axis=0)
    covariance = (mobile - mobile_centre).T @ (target - target_centre)
    left, _, right = np.linalg.svd(covariance)
    sign = np.sign(np.linalg.det(left @ right))
    correction = np.diag([1.0, 1.0, sign])
    rotation = (left @ correction @ right).T
    translation = target_centre - mobile_centre @ rotation.T
    return rotation, translation


def apply(rotation: np.ndarray, translation: np.ndarray, xyz: np.ndarray) -> np.ndarray:
    return xyz @ rotation.T + translation


def rmsd(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.sqrt(((left - right) ** 2).sum(axis=1).mean()))


def bonds(atoms: list[Atom]) -> set[tuple[int, int]]:
    """Covalent bonds inferred from distance, since deposited ligands carry no bond table."""
    found = set()
    for i, left in enumerate(atoms):
        for j in range(i + 1, len(atoms)):
            right = atoms[j]
            limit = COVALENT_RADII[left.element] + COVALENT_RADII[right.element] + BOND_TOLERANCE
            if distance(left.xyz, right.xyz) <= limit:
                found.add((i, j))
    return found


def neighbours(atoms: list[Atom]) -> dict[int, set[int]]:
    found: dict[int, set[int]] = {index: set() for index in range(len(atoms))}
    for i, j in bonds(atoms):
        found[i].add(j)
        found[j].add(i)
    return found


def fused_ring_core(atoms: list[Atom]) -> list[int]:
    """Indices of the largest ring system, which for these inhibitors is the bicyclic core."""
    systems = ring_systems(atoms)
    return sorted(max(systems, key=len)) if systems else []


def ring_systems(atoms: list[Atom]) -> list[set[int]]:
    """Sets of atoms joined by ring bonds, largest first.

    A bond is a ring bond when removing it leaves its two atoms connected. Fused
    rings share ring bonds and therefore land in one system.
    """
    edges = bonds(atoms)
    adjacency = neighbours(atoms)

    def connected_without(i: int, j: int) -> bool:
        seen, stack = {i}, [i]
        while stack:
            node = stack.pop()
            for other in adjacency[node]:
                if (node, other) in ((i, j), (j, i)) or other in seen:
                    continue
                if other == j:
                    return True
                seen.add(other)
                stack.append(other)
        return False

    ring_edges = [(i, j) for i, j in edges if connected_without(i, j)]
    ring_neighbours: dict[int, set[int]] = {}
    for i, j in ring_edges:
        ring_neighbours.setdefault(i, set()).add(j)
        ring_neighbours.setdefault(j, set()).add(i)
    components: list[set[int]] = []
    unvisited = set(ring_neighbours)
    while unvisited:
        start = unvisited.pop()
        component, stack = {start}, [start]
        while stack:
            node = stack.pop()
            for other in ring_neighbours[node]:
                if other in unvisited:
                    unvisited.discard(other)
                    component.add(other)
                    stack.append(other)
        components.append(component)
    return sorted(components, key=lambda component: (-len(component), min(component)))
