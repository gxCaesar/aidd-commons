"""Turn one set of molecules into several datasets, by changing only the definitions.

Positives, negatives, inactive compounds, decoys, class balance and the
generalization unit are choices, not properties of the molecules. This command
reads a committed set that stores measurements and rules but no class labels, and
reports what each choice does to the dataset that comes out.

    python labs/binder_definition/inspect_definition.py show
    python labs/binder_definition/inspect_definition.py check

Reads one committed JSON file and uses RDKit for scaffolds. No model is fitted,
no compound was assayed, and nothing here is a screening proposal.
"""

import argparse
import json
import sys
from pathlib import Path

from rdkit import RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog("rdApp.*")

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DATASET = LAB / "dataset.json"


def load() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def positives(data: dict, threshold: float) -> list[str]:
    return [row["id"] for row in data["measured"] if row["value"] >= threshold]


def undetermined(data: dict, threshold: float) -> list[str]:
    """Compounds the measurement did not place on either side of the cutoff."""
    slack = data["endpoint"]["assay_uncertainty"]
    return [row["id"] for row in data["measured"] if abs(row["value"] - threshold) <= slack]


def scaffold_of(smiles: str) -> str:
    return MurckoScaffold.MurckoScaffoldSmiles(smiles=smiles)


def unit_counts(rows: list[dict]) -> dict:
    scaffolds: dict[str, list[str]] = {}
    undefined = []
    for row in rows:
        core = scaffold_of(row["smiles"])
        if not core:
            undefined.append(row["id"])
            continue
        scaffolds.setdefault(core, []).append(row["id"])
    return {
        "molecules": len(rows),
        "scaffolds": len(scaffolds),
        "undefined": undefined,
        "groups": scaffolds,
    }


def composition(data: dict, threshold: float, include_decoys: bool) -> dict:
    """What the negative class is made of, once someone decides what goes in it."""
    positive = set(positives(data, threshold))
    measured_negative = [row["id"] for row in data["measured"] if row["id"] not in positive]
    decoys = [row["id"] for row in data["decoys"]["members"]] if include_decoys else []
    negatives = measured_negative + decoys
    total = len(positive) + len(negatives)
    return {
        "positives": sorted(positive),
        "measured_negatives": measured_negative,
        "decoys": decoys,
        "negative_total": len(negatives),
        "never_measured_share": len(decoys) / len(negatives) if negatives else 0.0,
        "prevalence": len(positive) / total if total else 0.0,
        "total": total,
    }


def show(data: dict) -> None:
    primary = data["primary_threshold"]["value"]
    slack = data["endpoint"]["assay_uncertainty"]
    measured = data["measured"]

    print(f"ONE SET OF {len(measured)} MEASURED COMPOUNDS, FIVE CUTOFFS")
    print(f"  {'cutoff':>7} {'positives':>10} {'undetermined':>13}   ids")
    for cutoff in data["threshold_grid"]:
        found = positives(data, cutoff)
        near = undetermined(data, cutoff)
        print(f"  {cutoff:>7} {len(found):>10} {len(near):>13}   {', '.join(found)}")
    print()
    print(
        f"  Nothing was measured again. The count moves from"
        f" {len(positives(data, data['threshold_grid'][-1]))} to"
        f" {len(positives(data, data['threshold_grid'][0]))} because a number was chosen."
    )
    print()

    near = undetermined(data, primary)
    print(f"SOME CLASSES ARE DECIDED BY NOISE  cutoff {primary}, assay uncertainty {slack}")
    for row in measured:
        if row["id"] in near:
            side = "positive" if row["value"] >= primary else "negative"
            print(
                f"  {row['id']} measured {row['value']} sits {abs(row['value'] - primary):.1f}"
                f" from the cutoff and is filed as {side}"
            )
    print(f"  {len(near)} of {len(measured)} compounds are within the assay uncertainty of the")
    print("  cutoff. A repeat measurement is expected to move them across it, so their")
    print("  class is a property of one reading rather than of the compound.")
    print()

    without = composition(data, primary, include_decoys=False)
    with_decoys = composition(data, primary, include_decoys=True)
    print("A NEGATIVE IS TWO DIFFERENT THINGS")
    print(
        f"  {'dataset':<22} {'positives':>10} {'negatives':>10}"
        f" {'never measured':>15} {'prevalence':>11}"
    )
    for name, block in (("measured only", without), ("with decoys", with_decoys)):
        print(
            f"  {name:<22} {len(block['positives']):>10} {block['negative_total']:>10}"
            f" {block['never_measured_share']:>14.0%} {block['prevalence']:>11.3f}"
        )
    print()
    print(
        f"  Adding decoys moved prevalence from {without['prevalence']:.3f} to"
        f" {with_decoys['prevalence']:.3f} without measuring anything."
    )
    print("  Precision of a random selector equals prevalence, so the number any")
    print("  reported precision must beat was moved by a choice about untested molecules.")
    print(f"  In the larger dataset {with_decoys['never_measured_share']:.0%} of the negative")
    print("  class carries no measurement at all, and calling it 'negatives' hides that.")
    print()


def show_units(data: dict) -> None:
    primary = data["primary_threshold"]["value"]
    counts = unit_counts(data["measured"])
    print("THE GENERALIZATION UNIT IS NOT THE MOLECULE")
    print(
        f"  {counts['molecules']} measured molecules collapse to {counts['scaffolds']}"
        " Bemis-Murcko scaffolds."
    )
    for core, members in sorted(counts["groups"].items(), key=lambda kv: -len(kv[1])):
        if len(members) > 1:
            print(f"    {len(members)} molecules share {core}: {', '.join(members)}")
    print("  A random split over molecules puts members of the same scaffold on both")
    print("  sides, so a held-out molecule can be a near copy of a training one.")
    print()
    if counts["undefined"]:
        print(
            f"  {len(counts['undefined'])} compound(s) have no scaffold at all:"
            f" {', '.join(counts['undefined'])}"
        )
        print(f"  {data['generalization_units']['acyclic_note']}")
        print()

    positive_rows = [row for row in data["measured"] if row["id"] in set(positives(data, primary))]
    positive_units = unit_counts(positive_rows)
    print(f"  At the primary cutoff there are {positive_units['molecules']} positives, sitting on")
    print(f"  {positive_units['scaffolds']} scaffolds. The number of independent positive")
    print("  units is the second number, and it is the one a test set can spend.")
    print()


def show_limits() -> None:
    print("WHAT THIS DOES NOT DO")
    print("  It fits no model and reports no performance. Every number above changed")
    print("  because a definition changed, which is the point: a benchmark can be made")
    print("  easier or harder without touching a molecule or running an assay.")
    print("  It also does not say which choices are correct. A decoy set is a legitimate")
    print("  tool when its assumption is stated. The failure is reporting decoys and")
    print("  measured inactives under one word and quoting a metric over the union.")
    print()


def check(data: dict) -> list[str]:
    """Recompute every relationship from the committed dataset. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    record_result(
        data["primary_threshold"]["declared_before_analysis"] is True,
        "the primary cutoff was declared before the analysis",
    )
    record_result(
        data["endpoint"]["assay_uncertainty"] > 0,
        f"the endpoint declares a positive assay uncertainty,"
        f" {data['endpoint']['assay_uncertainty']}, so no class can look exactly determined",
    )
    record_result(
        all(set(row) == {"id", "smiles", "value"} for row in data["measured"])
        and all(set(row) == {"id", "smiles"} for row in data["decoys"]["members"]),
        "no compound carries a class label, because a class is produced by a choice",
    )
    record_result(
        all("value" not in row for row in data["decoys"]["members"]),
        f"none of the {len(data['decoys']['members'])} decoys carries a measurement of any kind",
    )
    record_result(
        bool(data["decoys"]["assumption"]),
        "the decoy set states the assumption it rests on rather than implying evidence",
    )

    counts = {cutoff: len(positives(data, cutoff)) for cutoff in data["threshold_grid"]}
    record_result(
        len(set(counts.values())) > 1,
        f"one unchanged set of measurements yields different positive counts: {counts}",
    )
    record_result(
        max(counts.values()) >= 2 * min(counts.values()),
        f"the largest count is at least twice the smallest, {max(counts.values())}"
        f" against {min(counts.values())}, from choosing a number",
    )

    primary = data["primary_threshold"]["value"]
    near = undetermined(data, primary)
    record_result(
        len(near) > 0,
        f"{len(near)} of {len(data['measured'])} compounds sit within the assay uncertainty"
        f" of the cutoff, so their class is one reading: {near}",
    )
    record_result(
        any(row["value"] >= primary for row in data["measured"] if row["id"] in near)
        and any(row["value"] < primary for row in data["measured"] if row["id"] in near),
        "the undetermined compounds fall on both sides of the cutoff, so the ambiguity"
        " is not confined to one class",
    )

    without = composition(data, primary, include_decoys=False)
    with_decoys = composition(data, primary, include_decoys=True)
    record_result(
        without["positives"] == with_decoys["positives"],
        "adding decoys changes no positive, because it adds no measurement",
    )
    record_result(
        with_decoys["prevalence"] < without["prevalence"],
        f"prevalence falls from {without['prevalence']:.3f} to {with_decoys['prevalence']:.3f}"
        " purely from a decision about untested molecules",
    )
    record_result(
        with_decoys["never_measured_share"] > 0.5,
        f"most of the enlarged negative class was never measured:"
        f" {with_decoys['never_measured_share']:.0%}",
    )
    record_result(
        without["never_measured_share"] == 0.0,
        "the measured-only dataset contains no unmeasured negative, so the two"
        " datasets differ in kind rather than in size",
    )

    units = unit_counts(data["measured"])
    shared = {core: ids for core, ids in units["groups"].items() if len(ids) > 1}
    record_result(
        bool(shared),
        f"the {units['molecules']} molecules collapse to {units['scaffolds']} scaffolds,"
        f" with {len(shared)} scaffold(s) carrying more than one molecule,"
        " so molecules are not independent units",
    )
    record_result(
        len(units["undefined"]) > 0,
        f"at least one compound has no scaffold at all, leaving the unit undefined"
        f" rather than coarse: {units['undefined']}",
    )
    positive_rows = [row for row in data["measured"] if row["id"] in set(positives(data, primary))]
    positive_units = unit_counts(positive_rows)
    record_result(
        positive_units["scaffolds"] < positive_units["molecules"],
        f"the {positive_units['molecules']} positives sit on"
        f" {positive_units['scaffolds']} scaffolds, which is the number a test set spends",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    data = load()

    print(f"Dataset {DATASET.relative_to(ROOT)}")
    print(
        f"{len(data['measured'])} measured compounds and"
        f" {len(data['decoys']['members'])} decoys, no class labels stored"
    )
    print()
    if action == "show":
        show(data)
        show_units(data)
        show_limits()
        print("Run 'check' to recompute these counts from the committed dataset.")
        return

    print("DEFINITION CHECKS")
    failures = check(data)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies what each definition does to the dataset,")
    print("not that any definition is the right one and not that any compound binds.")


if __name__ == "__main__":
    main()
