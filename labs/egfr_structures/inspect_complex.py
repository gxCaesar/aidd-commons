"""Represent three EGFR complexes, and treat a pose as a hypothesis.

A contact list is geometry. An interaction list is geometry plus assumptions about
protonation and about which waters exist. A pose is a placement in one receptor
state, and three common ways to judge it can disagree. This command reads three
committed experimental structures, builds their contact and interaction
representations, compares two experimental poses of one ligand, places each ligand
into each receptor, and then perturbs one crystal pose in two constructed ways.

    python labs/egfr_structures/inspect_complex.py show
    python labs/egfr_structures/inspect_complex.py check

The three complexes are experimental. The two perturbed poses are constructed here
from one of them by a declared rigid motion, and are labelled as constructed wherever
they are printed. No docking, protonation or minimisation is performed.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cif  # noqa: E402
import inspect_state  # noqa: E402

ROOT = cif.LAB.parents[1]
POLAR = {"N", "O"}

# Protein donor and acceptor roles under a declared neutral-pH assumption:
# carboxylates deprotonated, lysine and arginine protonated, histidine tautomer unknown.
BACKBONE = {"N": "donor", "O": "acceptor", "OXT": "acceptor"}
SIDE_CHAIN = {
    ("SER", "OG"): "either",
    ("THR", "OG1"): "either",
    ("TYR", "OH"): "either",
    ("ASP", "OD1"): "acceptor",
    ("ASP", "OD2"): "acceptor",
    ("GLU", "OE1"): "acceptor",
    ("GLU", "OE2"): "acceptor",
    ("ASN", "OD1"): "acceptor",
    ("ASN", "ND2"): "donor",
    ("GLN", "OE1"): "acceptor",
    ("GLN", "NE2"): "donor",
    ("LYS", "NZ"): "donor",
    ("ARG", "NE"): "donor",
    ("ARG", "NH1"): "donor",
    ("ARG", "NH2"): "donor",
    ("TRP", "NE1"): "donor",
    ("HIS", "ND1"): "tautomer-dependent",
    ("HIS", "NE2"): "tautomer-dependent",
}


def protein_role(atom: cif.Atom) -> str:
    if atom.name == "N" and atom.resname == "PRO":
        return "none"
    if atom.name in BACKBONE:
        return BACKBONE[atom.name]
    return SIDE_CHAIN.get((atom.resname, atom.name), "none")


def compatible(ligand_role: str, other_role: str) -> bool:
    """Whether one partner can donate a hydrogen and the other accept it."""
    donates = {"donor", "either"}
    accepts = {"acceptor", "either"}
    return (ligand_role in donates and other_role in accepts) or (
        ligand_role in accepts and other_role in donates
    )


def roles_match_structure(ligand: list[cif.Atom], roles: dict) -> list[str]:
    """Check every declared ligand role against the ligand's own bonding."""
    problems = []
    names = {atom.name: index for index, atom in enumerate(ligand)}
    adjacency = cif.neighbours(ligand)
    systems = cif.ring_systems(ligand)
    core = set(cif.fused_ring_core(ligand))
    in_ring = set().union(*systems) if systems else set()
    for name, spec in roles.items():
        if name not in names:
            problems.append(f"{name} is not an atom of this ligand")
            continue
        index = names[name]
        partners = [ligand[j].element for j in adjacency[index]]
        kind = spec["kind"]
        ok = {
            "quinazoline ring nitrogen": index in core and ligand[index].element == "N",
            "anilino nitrogen": ligand[index].element == "N"
            and index not in in_ring
            and sum(j in core for j in adjacency[index]) == 1
            and len(adjacency[index]) == 2,
            "secondary amine nitrogen": ligand[index].element == "N"
            and index not in in_ring
            and partners == ["C", "C"],
            "ether oxygen": ligand[index].element == "O"
            and index not in in_ring
            and partners == ["C", "C"],
            "furan oxygen": ligand[index].element == "O"
            and any(index in s and len(s) == 5 for s in systems),
            "sulfonyl oxygen": ligand[index].element == "O" and partners == ["S"],
        }.get(kind, False)
        if not ok:
            problems.append(f"{name} is declared a {kind} but its bonding says otherwise")
    return problems


def interactions(entry: cif.Entry, ligand: list[cif.Atom], roles: dict, params: dict) -> dict:
    polar_cut = params["polar_contact_angstrom"]
    carbon_cut = params["hydrophobic_contact_angstrom"]
    bridge_cut = params["water_bridge_angstrom"]
    protein = entry.protein()
    polar = []
    fingerprint: set[tuple[int, str]] = set()
    for atom in ligand:
        for other in protein:
            gap = cif.distance(atom.xyz, other.xyz)
            position = entry.to_reference(other.chain, other.seq)
            if position is None:
                continue
            if atom.element in POLAR and other.element in POLAR and gap <= polar_cut:
                ligand_role = roles.get(atom.name, {}).get("role", "undeclared")
                other_role = protein_role(other)
                polar.append(
                    {
                        "ligand_atom": atom.name,
                        "ligand_role": ligand_role,
                        "residue": f"{other.resname}{position}",
                        "protein_atom": other.name,
                        "protein_role": other_role,
                        "distance": gap,
                        "compatible": compatible(ligand_role, other_role),
                    }
                )
                fingerprint.add((position, "polar"))
            if atom.element == "C" and other.element == "C" and gap <= carbon_cut:
                fingerprint.add((position, "carbon"))
    bridges = []
    for water in entry.waters():
        near_ligand = [
            a for a in ligand if a.element in POLAR and cif.distance(a.xyz, water.xyz) <= bridge_cut
        ]
        if not near_ligand:
            continue
        for other in protein:
            if other.element in POLAR and cif.distance(other.xyz, water.xyz) <= bridge_cut:
                position = entry.to_reference(other.chain, other.seq)
                if position is None:
                    continue
                for atom in near_ligand:
                    bridges.append((atom.name, f"{other.resname}{position}", other.name))
                fingerprint.add((position, "water"))
    return {"polar": polar, "bridges": bridges, "fingerprint": fingerprint}


def tanimoto(left: set, right: set) -> float:
    return len(left & right) / len(left | right)


def rotation_about(axis: np.ndarray, degrees: float) -> np.ndarray:
    unit = axis / np.linalg.norm(axis)
    k = np.array([[0, -unit[2], unit[1]], [unit[2], 0, -unit[0]], [-unit[1], unit[0], 0]])
    theta = math.radians(degrees)
    return np.eye(3) + math.sin(theta) * k + (1 - math.cos(theta)) * (k @ k)


def closest(ligand_xyz: np.ndarray, protein_xyz: np.ndarray) -> np.ndarray:
    gaps = np.sqrt(((ligand_xyz[:, None, :] - protein_xyz[None, :, :]) ** 2).sum(axis=-1))
    return gaps.min(axis=1)


def measure(entries: dict[str, cif.Entry], data: dict) -> dict:
    params = data["declared_parameters"]
    roles = data["ligand_roles"]
    records = {record["id"]: record for record in data["entries"]}
    reference_id = params["reference_entry"]
    out: dict = {"interactions": {}, "roles": {}, "waters": {}}
    ligands = {
        entry_id: entries[entry_id].ligand(records[entry_id]["ligand"]) for entry_id in entries
    }
    for entry_id, entry in entries.items():
        comp = records[entry_id]["ligand"]
        out["roles"][entry_id] = roles_match_structure(ligands[entry_id], roles[comp])
        out["interactions"][entry_id] = interactions(entry, ligands[entry_id], roles[comp], params)
        out["waters"][entry_id] = len(entry.waters())

    ids = list(entries)
    out["tanimoto"] = {}
    for i, left in enumerate(ids):
        for right in ids[i + 1 :]:
            a = out["interactions"][left]["fingerprint"]
            b = out["interactions"][right]["fingerprint"]
            dry = {x for x in a if x[1] != "water"}, {x for x in b if x[1] != "water"}
            out["tanimoto"][(left, right)] = {
                "all": tanimoto(a, b),
                "without_water": tanimoto(*dry),
            }

    frames = inspect_state.superpositions(entries, data)
    out["superposition"] = frames

    def moved(entry_id: str, atoms: list[cif.Atom]) -> np.ndarray:
        frame = frames[entry_id]
        return cif.apply(frame["rotation"], frame["translation"], np.array([a.xyz for a in atoms]))

    # Two experimental poses of one ligand, compared in the reference frame by atom name.
    erlotinib = [entry_id for entry_id in ids if records[entry_id]["ligand"] == "AQ4"]
    first, second = erlotinib
    left_atoms, right_atoms = ligands[first], ligands[second]
    right_index = {atom.name: i for i, atom in enumerate(right_atoms)}
    shared = [atom.name for atom in left_atoms if atom.name in right_index]
    left_xyz = moved(first, left_atoms)
    right_xyz = moved(second, right_atoms)
    left_index = {atom.name: i for i, atom in enumerate(left_atoms)}
    a = np.array([left_xyz[left_index[name]] for name in shared])
    b = np.array([right_xyz[right_index[name]] for name in shared])
    core_names = {left_atoms[i].name for i in cif.fused_ring_core(left_atoms)}
    core_rows = [i for i, name in enumerate(shared) if name in core_names]
    rest_rows = [i for i, name in enumerate(shared) if name not in core_names]
    displacement = np.linalg.norm(a - b, axis=1)
    out["two_poses"] = {
        "entries": (first, second),
        "atoms": len(shared),
        "rmsd": cif.rmsd(a, b),
        "core_rmsd": cif.rmsd(a[core_rows], b[core_rows]),
        "rest_rmsd": cif.rmsd(a[rest_rows], b[rest_rows]),
        "largest": max(zip(displacement, shared, strict=True)),
        "core_mean_b": {
            e: float(np.mean([x.b_factor for x in ligands[e] if x.name in core_names]))
            for e in erlotinib
        },
        "rest_mean_b": {
            e: float(np.mean([x.b_factor for x in ligands[e] if x.name not in core_names]))
            for e in erlotinib
        },
    }

    # Each ligand pose placed into each receptor, rigidly, in the reference frame.
    clash = params["clash_angstrom"]
    out["placement"] = {}
    for ligand_id in ids:
        pose = moved(ligand_id, ligands[ligand_id])
        for receptor_id in ids:
            receptor = moved(receptor_id, entries[receptor_id].protein())
            nearest = closest(pose, receptor)
            out["placement"][(ligand_id, receptor_id)] = {
                "clashing_atoms": int((nearest < clash).sum()),
                "closest": float(nearest.min()),
            }

    # Constructed hypotheses from the reference crystal pose, in its own receptor.
    reference = entries[reference_id]
    pose_atoms = ligands[reference_id]
    xyz = np.array([atom.xyz for atom in pose_atoms])
    receptor = np.array([atom.xyz for atom in reference.protein()])
    hinge = np.array(reference.atom_at(793, "N").xyz)
    comp = records[reference_id]["ligand"]
    ring_acceptors = [
        i
        for i, atom in enumerate(pose_atoms)
        if roles[comp].get(atom.name, {}).get("kind") == "quinazoline ring nitrogen"
    ]
    anchor = min(ring_acceptors, key=lambda i: float(np.linalg.norm(xyz[i] - hinge)))
    axis = xyz[anchor] - hinge

    def judge(label: str, candidate: np.ndarray) -> dict:
        nearest = closest(candidate, receptor)
        hinge_gap = float(np.linalg.norm(candidate[anchor] - hinge))
        return {
            "label": label,
            "rmsd": cif.rmsd(xyz, candidate),
            "hinge": hinge_gap,
            "hinge_kept": hinge_gap <= params["hinge_contact_angstrom"],
            "clashing_atoms": int((nearest < clash).sum()),
            "rmsd_passes": cif.rmsd(xyz, candidate) <= params["pose_rmsd_convention_angstrom"],
        }

    shift = params["constructed_translation_angstrom"] * axis / np.linalg.norm(axis)
    spin = rotation_about(axis, params["constructed_rotation_degrees"])
    out["anchor"] = pose_atoms[anchor].name
    out["hypotheses"] = [
        judge("crystal pose", xyz),
        judge(
            f"constructed: translated {params['constructed_translation_angstrom']:g} A"
            " away from the hinge",
            xyz + shift,
        ),
        judge(
            f"constructed: rotated {params['constructed_rotation_degrees']:g} degrees"
            " about the hinge contact",
            (xyz - xyz[anchor]) @ spin.T + xyz[anchor],
        ),
    ]
    return out


def show(data: dict, m: dict) -> None:
    params = data["declared_parameters"]
    records = {record["id"]: record for record in data["entries"]}
    ids = list(records)

    print("1. A CONTACT IS GEOMETRY; AN INTERACTION ADDS AN ASSUMPTION")
    print(
        f"  Polar pairs within {params['polar_contact_angstrom']:g} A, with the roles each partner"
    )
    print("  would need. Roles are declared, because no file models a hydrogen.")
    for entry_id in ids:
        pairs = m["interactions"][entry_id]["polar"]
        usable = sum(p["compatible"] for p in pairs)
        print(f"  {entry_id}  {len(pairs)} polar pairs, {usable} donor-acceptor compatible")
        for p in sorted(pairs, key=lambda p: p["distance"]):
            verdict = (
                "could be a hydrogen bond"
                if p["compatible"]
                else "not a hydrogen bond under these roles"
            )
            print(
                f"        {p['ligand_atom']:<4} {p['ligand_role']:<9} {p['residue']:>7}"
                f" {p['protein_atom']:<4} {p['protein_role']:<9} {p['distance']:.2f} A  {verdict}"
            )
    print(f"  {data['ligand_roles']['assumption']}")
    print()

    print("2. WATER-MEDIATED CONTACTS DEPEND ON WHICH WATERS WERE MODELLED")
    for entry_id in ids:
        bridges = m["interactions"][entry_id]["bridges"]
        text = "; ".join(f"{a} - water - {r} {n}" for a, r, n in bridges) or "none"
        print(f"  {entry_id}  {m['waters'][entry_id]} waters modelled; bridges: {text}")
    print()

    print("3. A FINGERPRINT BELONGS TO A COMPLEX, NOT TO A LIGAND")
    for entry_id in ids:
        fp = m["interactions"][entry_id]["fingerprint"]
        kinds = {kind: sum(1 for _, k in fp if k == kind) for kind in ("polar", "carbon", "water")}
        print(f"  {entry_id}  {len(fp)} residue-interaction bits {kinds}")
    for (left, right), values in m["tanimoto"].items():
        same = (
            "same ligand"
            if records[left]["ligand"] == records[right]["ligand"]
            else "different ligands"
        )
        print(
            f"  {left} vs {right} ({same}): Tanimoto {values['all']:.3f},"
            f" {values['without_water']:.3f} without water bits"
        )
    print()

    print("4. TWO EXPERIMENTAL POSES OF ONE LIGAND")
    t = m["two_poses"]
    first, second = t["entries"]
    frames = m["superposition"]
    print(
        f"  {second} superposed on {first} by {len(frames[second]['positions'])} site C-alpha atoms"
        f" ({frames[second]['rmsd_after']:.2f} A)"
    )
    print(
        f"  erlotinib, {t['atoms']} atoms matched by name: RMSD {t['rmsd']:.2f} A;"
        f" quinazoline core {t['core_rmsd']:.2f} A; everything else {t['rest_rmsd']:.2f} A"
    )
    print(f"  largest single displacement {t['largest'][0]:.2f} A at {t['largest'][1]}")
    for entry_id in t["entries"]:
        print(
            f"  {entry_id} mean B: core {t['core_mean_b'][entry_id]:.1f},"
            f" rest {t['rest_mean_b'][entry_id]:.1f}"
        )
    print(
        f"  Under a {params['pose_rmsd_convention_angstrom']:g} A convention these are one pose,"
        f" while parts of the ligand sit in different places."
    )
    print()

    print("5. ONE POSE, THREE RECEPTOR STATES")
    print(
        f"  Each ligand placed rigidly into each receptor; clash = heavy atom within"
        f" {params['clash_angstrom']:g} A of a protein heavy atom"
    )
    header = "  ligand from \\ receptor " + "".join(f"{r:>16}" for r in ids)
    print(header)
    for ligand_id in ids:
        placed = [m["placement"][(ligand_id, r)] for r in ids]
        cells = "".join(
            f"{p['clashing_atoms']:>4} ({p['closest']:.2f} A)".rjust(16) for p in placed
        )
        print(f"  {ligand_id} {records[ligand_id]['ligand_name']:<10}{cells}")
    print("  Side chains are not moved. A clash says the pose does not fit that receptor")
    print("  conformation, not that the ligand cannot bind the protein.")
    print()

    print("6. THREE WAYS TO JUDGE A POSE, AND WHERE THEY DISAGREE")
    print(
        f"  Hinge contact: {m['anchor']} to Met793 N within {params['hinge_contact_angstrom']:g} A."
        f" RMSD convention {params['pose_rmsd_convention_angstrom']:g} A."
    )
    for h in m["hypotheses"]:
        print(f"  {h['label']}")
        print(
            f"      RMSD {h['rmsd']:.2f} A ({'passes' if h['rmsd_passes'] else 'fails'}),"
            f" hinge {h['hinge']:.2f} A ({'kept' if h['hinge_kept'] else 'lost'}),"
            f" clashing atoms {h['clashing_atoms']}"
        )
    print("  The two constructed poses are not predictions. They are rigid motions of the")
    print("  crystal pose, chosen to show that the three criteria answer different questions.")
    print()


def check(data: dict, m: dict, lab: Path = cif.LAB) -> list[str]:
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
    problems = {entry_id: p for entry_id, p in m["roles"].items() if p}
    record(
        not problems,
        f"every declared ligand role agrees with the ligand's own bonding, problems {problems}",
    )
    if problems:
        print("  ....  roles are wrong, so no interaction verdict is attempted")
        return failures

    undeclared = sorted(
        {
            p["ligand_atom"]
            for i in m["interactions"].values()
            for p in i["polar"]
            if p["ligand_role"] == "undeclared"
        }
    )
    record(
        not undeclared,
        f"every ligand atom in a polar pair has a declared role, undeclared {undeclared}",
    )
    hinge = {
        entry_id: [p for p in i["polar"] if p["residue"] == "MET793" and p["protein_atom"] == "N"]
        for entry_id, i in m["interactions"].items()
    }
    record(
        all(len(v) == 1 and v[0]["compatible"] for v in hinge.values()),
        "every complex has exactly one polar pair to the Met793 backbone nitrogen, and it is"
        " donor-acceptor compatible",
    )
    rejected = {
        entry_id: [
            f"{p['ligand_atom']}-{p['residue']} {p['protein_atom']}"
            for p in i["polar"]
            if not p["compatible"]
        ]
        for entry_id, i in m["interactions"].items()
    }
    record(
        any(rejected.values()),
        "at least one geometric polar pair is not a hydrogen bond under the declared roles:"
        f" {rejected}",
    )
    waters = m["waters"]
    record(
        len(set(waters.values())) == len(waters),
        f"the files model different numbers of waters: {waters}",
    )
    record(
        all(m["interactions"][e]["bridges"] for e in m["interactions"]),
        "every complex has at least one water-mediated contact, so leaving waters out changes"
        " the representation",
    )

    pairs = m["tanimoto"]
    same = [
        v["all"]
        for (left, right), v in pairs.items()
        if records[left]["ligand"] == records[right]["ligand"]
    ]
    record(
        same and all(value < 1.0 for value in same),
        "the same ligand in two complexes gives different fingerprints:"
        f" Tanimoto {[round(v, 3) for v in same]}",
    )

    t = m["two_poses"]
    record(
        t["core_rmsd"] < t["rest_rmsd"],
        f"the two erlotinib poses agree better in the core ({t['core_rmsd']:.2f} A) than elsewhere"
        f" ({t['rest_rmsd']:.2f} A)",
    )
    record(
        t["rmsd"] <= params["pose_rmsd_convention_angstrom"] < t["largest"][0],
        f"the whole-ligand RMSD {t['rmsd']:.2f} A passes the"
        f" {params['pose_rmsd_convention_angstrom']:g} A convention while one atom moves"
        f" {t['largest'][0]:.2f} A",
    )

    own = {e: m["placement"][(e, e)]["clashing_atoms"] for e in records}
    record(
        all(v == 0 for v in own.values()),
        f"every ligand fits its own receptor without a clash: {own}",
    )
    lapatinib = [e for e in records if records[e]["ligand"] == "FMM"][0]
    reference_id = params["reference_entry"]
    others = [e for e in records if e not in (lapatinib, reference_id)]
    into_reference = m["placement"][(lapatinib, reference_id)]["clashing_atoms"]
    into_other = [m["placement"][(lapatinib, e)]["clashing_atoms"] for e in others]
    record(
        into_reference > 0 and any(v < into_reference for v in into_other),
        f"the lapatinib pose clashes in the reference receptor ({into_reference} atoms) and less in"
        f" another receptor state ({into_other})",
    )

    crystal, shifted, spun = m["hypotheses"]
    record(
        crystal["rmsd"] == 0 and crystal["hinge_kept"] and crystal["clashing_atoms"] == 0,
        "the crystal pose passes all three criteria in its own receptor",
    )
    record(
        shifted["rmsd_passes"] and not shifted["hinge_kept"],
        f"a constructed pose passes the RMSD convention and loses the hinge contact"
        f" (RMSD {shifted['rmsd']:.2f} A, hinge {shifted['hinge']:.2f} A)",
    )
    record(
        spun["rmsd_passes"] and spun["hinge_kept"] and spun["clashing_atoms"] > 0,
        f"a constructed pose passes the RMSD convention, keeps the hinge contact and clashes"
        f" (RMSD {spun['rmsd']:.2f} A, {spun['clashing_atoms']} clashing atoms)",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    data = cif.manifest()
    entries = cif.load_all()
    print(f"Entries {cif.MANIFEST.relative_to(ROOT)}: {', '.join(entries)}")
    print("Three experimental complexes; two constructed poses are labelled where printed")
    print()
    measured = measure(entries, data)
    if action == "show":
        show(data, measured)
        print("Run 'check' to recompute these relationships.")
        return
    print("COMPLEX CHECKS")
    failures = check(data, measured)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies what the declared definitions produce from these")
    print("three structures, not that any pose, contact or water is correct.")


if __name__ == "__main__":
    main()
