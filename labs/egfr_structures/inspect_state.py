"""Read three deposited EGFR structures as evidence, and define their binding site.

A structure file is a model refined against diffraction data, recorded with the
construct that was crystallised, the residues the model does not contain, and the
depositor's own numbering. This command reads what each committed file says about
itself, computes one conformational descriptor, and shows how a binding site and a
docking box follow from choices rather than from the protein alone.

    python labs/egfr_structures/inspect_state.py show
    python labs/egfr_structures/inspect_state.py check

Reads three committed, unmodified PDBx/mmCIF files. No network access, no structure
preparation, no docking. Standard library and NumPy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cif  # noqa: E402

ROOT = cif.LAB.parents[1]


def ranges(positions: list[int]) -> list[tuple[int, int]]:
    spans: list[list[int]] = []
    for position in positions:
        if spans and position == spans[-1][1] + 1:
            spans[-1][1] = position
        else:
            spans.append([position, position])
    return [(start, end) for start, end in spans]


def span_text(spans: list[tuple[int, int]]) -> str:
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans) or "none"


def site(entry: cif.Entry, ligand: list[cif.Atom], cutoff: float) -> set[int]:
    """Reference positions of residues with any heavy atom within `cutoff` of the ligand."""
    found = set()
    for atom in entry.protein():
        if any(cif.distance(atom.xyz, other.xyz) <= cutoff for other in ligand):
            mapped = entry.to_reference(atom.chain, atom.seq)
            if mapped is not None:
                found.add(mapped)
    return found


def jaccard(left: set[int], right: set[int]) -> float:
    return len(left & right) / len(left | right)


def superpositions(entries: dict[str, cif.Entry], data: dict) -> dict[str, dict[str, object]]:
    """Superpose every entry onto the reference on the C-alpha atoms of the reference site."""
    params = data["declared_parameters"]
    reference_id = params["reference_entry"]
    reference = entries[reference_id]
    ligands = {record["id"]: record["ligand"] for record in data["entries"]}
    reference_site = site(
        reference,
        reference.ligand(ligands[reference_id]),
        params["superposition_site_cutoff_angstrom"],
    )
    alpha = {entry_id: entry.ca_by_reference() for entry_id, entry in entries.items()}
    shared = sorted(reference_site.intersection(*(set(coords) for coords in alpha.values())))
    result: dict[str, dict[str, object]] = {}
    for entry_id in entries:
        mobile = np.array([alpha[entry_id][position] for position in shared])
        target = np.array([alpha[reference_id][position] for position in shared])
        rotation, translation = cif.kabsch(mobile, target)
        result[entry_id] = {
            "rotation": rotation,
            "translation": translation,
            "positions": shared,
            "rmsd_before": cif.rmsd(mobile, target),
            "rmsd_after": cif.rmsd(cif.apply(rotation, translation, mobile), target),
        }
    return result


def box(xyz: np.ndarray, padding: float) -> tuple[np.ndarray, np.ndarray]:
    return xyz.min(axis=0) - padding, xyz.max(axis=0) + padding


def volume(low: np.ndarray, high: np.ndarray) -> float:
    return float(np.prod(high - low))


def measure(entries: dict[str, cif.Entry], data: dict) -> dict:
    """Everything the lab reports, computed from the committed files and declarations."""
    params = data["declared_parameters"]
    records = {record["id"]: record for record in data["entries"]}
    out: dict = {"entries": {}, "sites": {}, "boxes": {}}
    for entry_id, entry in entries.items():
        ligand = entry.ligand(records[entry_id]["ligand"])
        protein = entry.protein()
        refinement = entry.refinement()
        differences = entry.engineered_differences()
        lysine = entry.atom_at(745, "NZ")
        glutamate = entry.atom_at(762, "CD")
        hinge = entry.atom_at(793, "N")
        hinge_author = None if hinge is None else hinge.seq
        out["entries"][entry_id] = {
            "refinement": refinement,
            "dates": entry.dates(),
            "title": entry.title(),
            "citation": entry.primary_citation(),
            "assemblies": entry.assemblies(),
            "chains": entry.polymer_chains(),
            "segments": entry.segments(),
            "added_residues": [d for d in differences if d["reference_position"] is None],
            "substitutions": [d for d in differences if d["reference_position"] is not None],
            "unobserved": ranges(entry.unobserved_residues()),
            "unobserved_count": len(entry.unobserved_residues()),
            "observed_range": (min(entry.residue_names()), max(entry.residue_names())),
            "landmarks": {pos: entry.residue_names().get(pos) for pos in cif.LANDMARKS},
            "hinge_author_number": hinge_author,
            "set_aside_alternates": entry.set_aside_alternates,
            "ligand_atoms": len(ligand),
            "waters": len(entry.waters()),
            "ligand_mean_b": float(np.mean([atom.b_factor for atom in ligand])),
            "protein_mean_b": float(np.mean([atom.b_factor for atom in protein])),
            "lys_glu_distance": (
                None
                if lysine is None or glutamate is None
                else cif.distance(lysine.xyz, glutamate.xyz)
            ),
        }
        out["sites"][entry_id] = {
            cutoff: site(entry, ligand, cutoff) for cutoff in params["site_cutoffs_angstrom"]
        }

    frames = superpositions(entries, data)
    out["superposition"] = frames
    reference_id = params["reference_entry"]
    for entry_id, entry in entries.items():
        ligand = entry.ligand(records[entry_id]["ligand"])
        deposited = np.array([atom.xyz for atom in ligand])
        frame = frames[entry_id]
        moved = cif.apply(frame["rotation"], frame["translation"], deposited)
        out["boxes"][entry_id] = {
            "deposited": deposited,
            "moved": moved,
            "volumes": {
                padding: {
                    "deposited_frame": volume(*box(deposited, padding)),
                    "reference_frame": volume(*box(moved, padding)),
                }
                for padding in params["box_paddings_angstrom"]
            },
        }
    reference_box = out["boxes"][reference_id]["moved"]
    out["enclosure"] = {}
    for entry_id in entries:
        if entry_id == reference_id:
            continue
        moved = out["boxes"][entry_id]["moved"]
        out["enclosure"][entry_id] = {}
        for padding in params["box_paddings_angstrom"]:
            low, high = box(reference_box, padding)
            inside = int(((moved >= low) & (moved <= high)).all(axis=1).sum())
            out["enclosure"][entry_id][padding] = (inside, len(moved))
    return out


def show(data: dict, m: dict) -> None:
    params = data["declared_parameters"]
    records = {record["id"]: record for record in data["entries"]}
    ids = list(records)

    print("1. WHAT EACH FILE IS EVIDENCE OF")
    for entry_id in ids:
        e = m["entries"][entry_id]
        r = e["refinement"]
        print(
            f"  {entry_id}  {r['method']}, {r['resolution']:.2f} A,"
            f" R-work {r['r_work']:.3f}, R-free {r['r_free']:.3f}"
            f" (gap {r['r_free'] - r['r_work']:.3f})"
        )
        print(
            f"        deposited {e['dates']['deposited']}, latest revision"
            f" {e['dates']['latest_revision']}"
        )
        print(f"        title: {e['title']}")
        c = e["citation"]
        print(f"        primary citation: {c['journal']} {c['year']}, doi {c['doi']}")
    print("  Resolution and R-free describe the whole model. They do not say how well any")
    print("  one atom, residue or ligand is determined.")
    print()

    print("2. WHAT WAS CRYSTALLISED, AND HOW IT IS NUMBERED")
    for entry_id in ids:
        e = m["entries"][entry_id]
        segment = e["segments"][0]
        print(
            f"  {entry_id}  {segment.accession} {segment.reference_start}-"
            f"{segment.reference_end} aligned; author number + {segment.offset:>2}"
            f" = reference number"
        )
        print(f"        hinge methionine: author {e['hinge_author_number']}, reference 793")
        print(
            f"        residues added by the construct: {len(e['added_residues'])};"
            f" substitutions: "
            + (
                ", ".join(
                    f"{s['reference_residue']}{s['reference_position']}{s['deposited_residue']}"
                    f" ({s['details']})"
                    for s in e["substitutions"]
                )
                or "none"
            )
        )
        print(
            f"        reference residues in the construct but not in the model:"
            f" {e['unobserved_count']} ({span_text(e['unobserved'])})"
        )
        assembly = e["assemblies"][0]
        print(
            f"        assembly annotation: {assembly['oligomeric_details']}"
            f" ({assembly['details']}); polymer chains in the file: {len(e['chains'])}"
        )
    print("  The same methionine carries two different author numbers across these files.")
    print("  Every comparison below uses reference numbers, and the check confirms that")
    print("  five landmark positions hold the expected residue in all three files.")
    print()

    print("3. STATE: ONE DESCRIPTOR, AND WHO ASSIGNED THE LABEL")
    for entry_id in ids:
        e = m["entries"][entry_id]
        print(f"  {entry_id}  Lys745 NZ to Glu762 CD: {e['lys_glu_distance']:.2f} A")
    print("  The distance is computed here. The word 'inactive' in the 4HJO title is the")
    print("  depositors' label. One distance agrees with that label; it is not a state")
    print("  assignment on its own.")
    print()

    print("4. HOW WELL THE LIGAND IS DETERMINED, RELATIVE TO ITS PROTEIN")
    for entry_id in ids:
        e = m["entries"][entry_id]
        print(
            f"  {entry_id}  {records[entry_id]['ligand_name']} ({records[entry_id]['ligand']}),"
            f" {e['ligand_atoms']} heavy atoms: mean B {e['ligand_mean_b']:.1f}"
            f" against protein {e['protein_mean_b']:.1f}; waters modelled {e['waters']}"
        )
    print("  No hydrogen atom is modelled in any file, so protonation is not in the evidence.")
    print()

    print("5. THE SITE IS A DEFINITION")
    cutoffs = params["site_cutoffs_angstrom"]
    for entry_id in ids:
        sizes = ", ".join(f"{len(m['sites'][entry_id][c])} at {c:g} A" for c in cutoffs)
        print(f"  {entry_id}  residues within the cutoff of the ligand: {sizes}")
    first = cutoffs[0]
    sites = {entry_id: m["sites"][entry_id][first] for entry_id in ids}
    erlotinib = [entry_id for entry_id in ids if records[entry_id]["ligand"] == "AQ4"]
    other = [entry_id for entry_id in ids if records[entry_id]["ligand"] != "AQ4"][0]
    only_other = sorted(sites[other] - set().union(*(sites[e] for e in erlotinib)))
    print(
        f"  At {first:g} A, erlotinib in {erlotinib[0]} and in {erlotinib[1]}: Jaccard"
        f" {jaccard(sites[erlotinib[0]], sites[erlotinib[1]]):.2f};"
        f" Glu762 in the site: "
        + ", ".join(f"{e} {'yes' if 762 in sites[e] else 'no'}" for e in erlotinib)
    )
    print(f"  Residues in the {other} site and in neither erlotinib site: {only_other}")
    print("  All three ligands sit in the ATP site. No file carries a ligand anywhere else,")
    print("  so these entries cannot define an allosteric or transient site, and no")
    print("  pocket-prediction method was run.")
    print()

    print("6. A DOCKING BOX INHERITS ITS LIGAND AND ITS FRAME")
    frames = m["superposition"]
    reference_id = params["reference_entry"]
    for entry_id in ids:
        if entry_id == reference_id:
            continue
        f = frames[entry_id]
        print(
            f"  {entry_id} onto {reference_id}: site C-alpha RMSD {f['rmsd_before']:.2f} A"
            f" before, {f['rmsd_after']:.2f} A after superposition"
            f" ({len(f['positions'])} residues)"
        )
    smallest = min(params["box_paddings_angstrom"])
    for entry_id in ids:
        volumes = m["boxes"][entry_id]["volumes"][smallest]
        print(
            f"  {entry_id}  box volume at {smallest:g} A padding: {volumes['deposited_frame']:.0f}"
            f" A^3 in its own frame, {volumes['reference_frame']:.0f} A^3 in the"
            f" {reference_id} frame"
        )
    for entry_id, by_padding in m["enclosure"].items():
        cells = ", ".join(
            f"{inside}/{total} at {p:g} A" for p, (inside, total) in by_padding.items()
        )
        print(f"  {entry_id} ligand atoms inside the {reference_id} erlotinib box: {cells}")
    print("  An axis-aligned box changes volume when the same pose is expressed in another")
    print("  frame, and a box drawn around one ligand need not enclose another ligand's pose.")
    print()


def check(data: dict, m: dict, lab: Path = cif.LAB) -> list[str]:
    """Recompute every relationship the lab reports. Returns failures."""
    failures: list[str] = []

    def record(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    params = data["declared_parameters"]
    records = {record["id"]: record for record in data["entries"]}
    mismatched = cif.mismatched_files(data, lab)
    record(
        not mismatched,
        f"every committed file passes file metadata validation, problems {mismatched}",
    )
    if mismatched:
        print("  ....  input file validation failed, so no other check is attempted")
        return failures

    wrong = {
        entry_id: {pos: name for pos, name in e["landmarks"].items() if name != cif.LANDMARKS[pos]}
        for entry_id, e in m["entries"].items()
    }
    wrong = {k: v for k, v in wrong.items() if v}
    record(
        not wrong,
        f"after mapping to reference numbers, all five landmarks hold the expected residue"
        f" in every file, wrong {wrong}",
    )
    authors = {e["hinge_author_number"] for e in m["entries"].values()}
    record(
        len(authors) > 1,
        "the hinge methionine carries more than one author number across files:"
        f" {sorted(authors, key=str)}",
    )
    incomplete = [
        entry_id
        for entry_id, e in m["entries"].items()
        if None
        in (
            e["refinement"]["resolution"],
            e["refinement"]["r_work"],
            e["refinement"]["r_free"],
            e["dates"]["deposited"],
        )
    ]
    record(
        not incomplete,
        "method, resolution, R-work, R-free and deposition date are read for every file,"
        f" missing {incomplete}",
    )
    record(
        all(e["refinement"]["r_free"] >= e["refinement"]["r_work"] for e in m["entries"].values()),
        "R-free is not below R-work in any file",
    )
    substitutions = {
        entry_id: [
            f"{s['reference_residue']}{s['reference_position']}{s['deposited_residue']}"
            for s in e["substitutions"]
        ]
        for entry_id, e in m["entries"].items()
    }
    record(
        any(substitutions.values()),
        f"at least one construct differs from the reference sequence, and the difference is"
        f" reported apart from added residues: {substitutions}",
    )
    record(
        all(e["unobserved_count"] > 0 for e in m["entries"].values()),
        "every file lists reference residues that the model does not contain",
    )
    record(
        all(e["assemblies"] and e["assemblies"][0]["details"] for e in m["entries"].values()),
        "every assembly annotation says who defined it",
    )

    distances = {entry_id: e["lys_glu_distance"] for entry_id, e in m["entries"].items()}
    reference_id = params["reference_entry"]
    others = [entry_id for entry_id in distances if entry_id != reference_id]
    record(
        distances[reference_id] is not None
        and distances[reference_id] < 4.0
        and all(distances[o] is not None and distances[o] > 10.0 for o in others),
        f"the Lys745-Glu762 distance separates the reference from the other two:"
        f" { {k: None if v is None else round(v, 2) for k, v in distances.items()} }",
    )

    cutoffs = params["site_cutoffs_angstrom"]
    record(len(cutoffs) >= 3, f"the site is reported at three or more cutoffs, {cutoffs}")
    record(
        all(
            m["sites"][entry_id][a] < m["sites"][entry_id][b]
            for entry_id in m["sites"]
            for a, b in zip(sorted(cutoffs), sorted(cutoffs)[1:], strict=False)
        ),
        "every site grows strictly as its cutoff grows, so its size is a property of the cutoff",
    )
    erlotinib = [entry_id for entry_id in records if records[entry_id]["ligand"] == "AQ4"]
    first = min(cutoffs)
    in_site = {entry_id: 762 in m["sites"][entry_id][first] for entry_id in erlotinib}
    record(
        len(set(in_site.values())) == 2,
        f"Glu762 is in one erlotinib site and not the other at {first:g} A: {in_site}",
    )
    other = [entry_id for entry_id in records if records[entry_id]["ligand"] != "AQ4"][0]
    extra = m["sites"][other][first] - set().union(*(m["sites"][e][first] for e in erlotinib))
    record(
        bool(extra),
        f"the lapatinib site contains residues in neither erlotinib site: {sorted(extra)}",
    )

    frames = m["superposition"]
    record(
        all(
            f["rmsd_after"] < 2.0
            and (entry_id == reference_id or f["rmsd_after"] < f["rmsd_before"])
            for entry_id, f in frames.items()
        ),
        "superposition on site C-alpha atoms brings every file below 2 A and improves on the"
        " deposited frames",
    )
    smallest = min(params["box_paddings_angstrom"])
    ratios = {
        entry_id: b["volumes"][smallest]["deposited_frame"]
        / b["volumes"][smallest]["reference_frame"]
        for entry_id, b in m["boxes"].items()
        if entry_id != reference_id
    }
    record(
        any(ratio > 1.5 or ratio < 1 / 1.5 for ratio in ratios.values()),
        f"the same pose gives an axis-aligned box of a different volume in another frame:"
        f" { {k: round(v, 2) for k, v in ratios.items()} }",
    )
    largest = max(params["box_paddings_angstrom"])
    inside, total = m["enclosure"][other][largest]
    record(
        inside < total,
        f"even at {largest:g} A padding the erlotinib-derived box leaves {total - inside} of"
        f" {total} lapatinib atoms outside",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    data = cif.manifest()
    entries = cif.load_all()
    print(f"Entries {cif.MANIFEST.relative_to(ROOT)}: {', '.join(entries)}")
    print("Unmodified PDBx/mmCIF files; no structure was prepared or docked")
    print()
    measured = measure(entries, data)
    if action == "show":
        show(data, measured)
        print("Run 'check' to recompute these relationships.")
        return
    print("STRUCTURE CHECKS")
    failures = check(data, measured)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies what the files say and what the declared")
    print("definitions produce, not that any structure is the state that matters in a cell.")


if __name__ == "__main__":
    main()
