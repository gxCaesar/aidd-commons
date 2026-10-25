"""Enumerate declared design spaces and ask what each one can and cannot reach.

A candidate space is quoted as a size. The size comes from the inputs and the
reach comes from the construction, and only one of them is usually reported. This
command enumerates three committed spaces exactly and tests four target molecules
against each.

    python labs/design_space/inspect_space.py show
    python labs/design_space/inspect_space.py check

Reads one committed JSON file and uses RDKit to build and canonicalise. No
molecule here is a design proposal and no space is a real screening library.
"""

import argparse
import json
import sys
from pathlib import Path

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
SPACES = LAB / "spaces.json"


def load() -> dict:
    return json.loads(SPACES.read_text(encoding="utf-8"))


def build(core: str, r1: str, r2: str) -> str | None:
    smiles = core.replace("[*:1]", r1).replace("[*:2]", r2)
    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol) if mol is not None else None


def enumerate_space(spec: dict) -> dict:
    """Every product the construction can write, with the nominal size beside it."""
    members, failed = set(), 0
    for r1 in spec["r1"]:
        for r2 in spec["r2"]:
            product = build(spec["core"], r1, r2)
            if product is None:
                failed += 1
            else:
                members.add(product)
    nominal = len(spec["r1"]) * len(spec["r2"])
    return {
        "nominal": nominal,
        "distinct": len(members),
        "unbuildable": failed,
        "members": members,
    }


def reach(data: dict) -> dict[str, dict[str, bool]]:
    spaces = {name: enumerate_space(spec) for name, spec in data["spaces"].items()}
    table = {}
    for target in data["targets"]:
        canonical = Chem.CanonSmiles(target["smiles"])
        table[target["id"]] = {
            name: canonical in space["members"] for name, space in spaces.items()
        }
    return table


def show(data: dict) -> None:
    spaces = {name: enumerate_space(spec) for name, spec in data["spaces"].items()}
    print("THREE DECLARED SPACES")
    print(f"  {'space':<20} {'nominal':>8} {'distinct':>9} {'unbuildable':>12}   construction")
    for name, spec in data["spaces"].items():
        block = spaces[name]
        print(
            f"  {name:<20} {block['nominal']:>8} {block['distinct']:>9}"
            f" {block['unbuildable']:>12}   {spec['construction']}"
        )
    print()
    print(f"  {data['what_a_space_is']}")
    print()

    table = reach(data)
    print("WHAT EACH SPACE CAN REACH")
    header = "".join(f"{name:>20}" for name in data["spaces"])
    print(f"  {'target':<6}{header}   description")
    for target in data["targets"]:
        row = table[target["id"]]
        marks = "".join(f"{('yes' if row[name] else 'no'):>20}" for name in data["spaces"])
        print(f"  {target['id']:<6}{marks}   {target['description']}")
    print()

    small, grown = spaces["enumeration"], spaces["enumeration_grown"]
    factor = grown["nominal"] / small["nominal"]
    gained = [
        target["id"]
        for target in data["targets"]
        if table[target["id"]]["enumeration_grown"] and not table[target["id"]]["enumeration"]
    ]
    never = [
        target["id"]
        for target in data["targets"]
        if not table[target["id"]]["enumeration"] and not table[target["id"]]["enumeration_grown"]
    ]
    print("SIZE DOES NOT BUY REACH")
    print(
        f"  Growing the lists took the space from {small['nominal']} to"
        f" {grown['nominal']}, a factor of {factor:.0f}."
    )
    print(f"  Targets that became reachable: {gained}")
    print(f"  Targets still unreachable at any list size: {never}")
    print("  The second group is not far away. One of them differs from a reachable")
    print("  molecule by a single atom in the ring. It is unreachable because the core")
    print("  is fixed by the construction, and no amount of substituent buys a new core.")
    print()

    hop = [
        target["id"]
        for target in data["targets"]
        if table[target["id"]]["scaffold_hop"] and not table[target["id"]]["enumeration_grown"]
    ]
    print("A DIFFERENT CONSTRUCTION REACHES DIFFERENT CHEMISTRY, NOT MORE OF IT")
    print(f"  The third space is the same size as the first and reaches {hop},")
    print("  which neither enumeration space reaches at any size. It also reaches none")
    print("  of what they do. Two spaces of equal size can be disjoint.")
    print()


def show_limits(data: dict) -> None:
    table = reach(data)
    unreachable = [
        target["id"] for target in data["targets"] if not any(table[target["id"]].values())
    ]
    print("WHAT REACHABILITY IS NOT")
    print(f"  {data['what_reachability_is_not']}")
    print(f"  One target is reachable in none of the three spaces: {unreachable}.")
    print("  That is a statement about these three constructions and about nothing else.")
    print("  A fourth construction would reach it, and would fail to reach something")
    print("  these three cover.")
    print()


def check(data: dict) -> list[str]:
    """Recompute every relationship from the committed declarations. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    record_result(
        len(data["spaces"]) >= 3,
        f"the record declares {len(data['spaces'])} constructions to compare",
    )
    record_result(
        all(
            spec.get("construction") and spec.get("cannot_reach")
            for spec in data["spaces"].values()
        ),
        "every space states its construction and what it cannot reach",
    )
    spaces = {name: enumerate_space(spec) for name, spec in data["spaces"].items()}
    record_result(
        all(block["unbuildable"] == 0 for block in spaces.values()),
        "every declared product builds, so no space is quietly smaller than its inputs",
    )
    record_result(
        all(
            block["nominal"] == len(data["spaces"][name]["r1"]) * len(data["spaces"][name]["r2"])
            for name, block in spaces.items()
        ),
        "each nominal size is the product of its input lists rather than a stated number",
    )

    table = reach(data)
    small, grown = spaces["enumeration"], spaces["enumeration_grown"]
    record_result(
        grown["nominal"] > small["nominal"],
        f"the grown space is larger, {small['nominal']} against {grown['nominal']}",
    )
    record_result(
        data["spaces"]["enumeration"]["core"] == data["spaces"]["enumeration_grown"]["core"],
        "the grown space shares the core, so only its inputs changed",
    )
    gained = [
        key for key, row in table.items() if row["enumeration_grown"] and not row["enumeration"]
    ]
    never = [
        key for key, row in table.items() if not row["enumeration"] and not row["enumeration_grown"]
    ]
    record_result(
        len(gained) > 0 and len(never) > 0,
        f"growing the space reached {gained} and left {never} unreachable, so size buys"
        " more of the same reach rather than different reach",
    )
    record_result(
        data["spaces"]["scaffold_hop"]["core"] != data["spaces"]["enumeration"]["core"],
        "the third space differs in construction rather than in size",
    )
    record_result(
        spaces["scaffold_hop"]["nominal"] == small["nominal"],
        f"it is the same nominal size as the first, {spaces['scaffold_hop']['nominal']},"
        " so any difference in reach is not a difference in size",
    )
    record_result(
        not (spaces["scaffold_hop"]["members"] & grown["members"]),
        "the third space and the grown space share no member at all, so two spaces can"
        " be disjoint without either being larger",
    )
    hop_only = [
        key for key, row in table.items() if row["scaffold_hop"] and not row["enumeration_grown"]
    ]
    record_result(
        len(hop_only) > 0,
        f"a different construction reaches targets no amount of enumeration does: {hop_only}",
    )
    unreachable = [key for key, row in table.items() if not any(row.values())]
    record_result(
        len(unreachable) > 0,
        f"at least one target is reachable in none of the declared spaces: {unreachable}",
    )
    record_result(
        bool(data["what_reachability_is_not"]),
        "the record states that reachable does not mean makeable",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    data = load()

    print(f"Spaces {SPACES.relative_to(ROOT)}")
    print(f"{len(data['spaces'])} declared constructions, {len(data['targets'])} target molecules")
    print()
    if action == "show":
        show(data)
        show_limits(data)
        print("Run 'check' to recompute these sizes and reachability verdicts.")
        return

    print("DESIGN SPACE CHECKS")
    failures = check(data)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies what each construction reaches, not that any")
    print("molecule can be made and not that any space is worth searching.")


if __name__ == "__main__":
    main()
