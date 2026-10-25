"""Separate the claims that a predicted structure invites collapsing into one.

A monomer prediction, a complex prediction, a co-folded pose, a docked pose and
an experimental binding measurement are five different claims. They arrive in
similar file formats, are described with similar words, and are routinely quoted
as if one supported another. This command reads the frozen registry extract
committed beside it and shows which claim each recorded system actually supports,
and where the evidence for that claim stops.

    python labs/cofolding_claims/inspect_claims.py show
    python labs/cofolding_claims/inspect_claims.py check

No network, no download, no third-party package. `show` prints the claim classes.
`check` recomputes the relationships that must hold across the extract and exits
non-zero if any of them fails. The extract is regenerated, never hand-edited, by
`export_claim_records.py`.
"""

import argparse
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
EXTRACT = LAB / "claim-records.json"

# The task labels the registry uses, grouped by the claim each one licenses.
CLAIM_CLASSES = {
    "monomer prediction": {"structure-prediction"},
    "co-folded complex": {"co-folding"},
    "generated pose": {"molecular-docking"},
    "pose check": {"pose-validation"},
    "affinity estimate": {"affinity-prediction", "drug-target-affinity-prediction"},
}
OPENNESS_ORDER = (
    "inference_code",
    "training_code",
    "weights",
    "architecture",
    "data_recipe",
    "training_data",
    "evaluation_code",
)


def load() -> dict:
    return json.loads(EXTRACT.read_text(encoding="utf-8"))


def structure_family(extract: dict) -> list[dict]:
    wanted = set().union(*CLAIM_CLASSES.values())
    return [row for row in extract["records"] if wanted & set(row.get("tasks") or ())]


def evidenced(record: dict) -> list[str]:
    openness = record.get("openness") or {}
    return [name for name in OPENNESS_ORDER if openness.get(name, "unverified") != "unverified"]


def classes_of(record: dict) -> list[str]:
    tasks = set(record.get("tasks") or ())
    return [label for label, wanted in CLAIM_CLASSES.items() if wanted & tasks]


def show_classes(extract: dict) -> None:
    """Each class, what it licenses, and where its evidence stops."""
    family = structure_family(extract)
    print(f"CLAIM CLASSES ACROSS {len(family)} REGISTERED SYSTEMS")
    for label in CLAIM_CLASSES:
        members = [row for row in family if label in classes_of(row)]
        print(f"  {label} ({len(members)})")
        for row in members:
            marks = evidenced(row)
            modality = ", ".join(row.get("modalities") or ["unstated"])
            print(f"    {row['id']:<32} modality {modality}")
            print(f"      openness evidenced {len(marks)}/7  {', '.join(marks) or 'none'}")
    print()


def show_confusions(extract: dict) -> None:
    """The three places where a reader is invited to collapse two claims."""
    family = structure_family(extract)
    print("WHERE THE CLAIMS GET COLLAPSED")

    modalities: dict[str, set[str]] = {}
    for row in family:
        for label in classes_of(row):
            for modality in row.get("modalities") or ():
                modalities.setdefault(modality, set()).add(label)
    shared = {name: labels for name, labels in modalities.items() if len(labels) > 1}
    print("  1. The modality label does not name the claim.")
    for name, labels in sorted(shared.items()):
        print(f"     {name} carries {len(labels)} claim classes: {', '.join(sorted(labels))}")

    dual = sorted(row["id"] for row in family if len(classes_of(row)) > 1)
    print("  2. One system can make two claims at once.")
    print(f"     records declaring more than one claim class: {dual or 'none'}")
    for identifier in dual:
        row = next(r for r in family if r["id"] == identifier)
        print(f"       {identifier}: {', '.join(classes_of(row))}")
    print("     A pose and a potency are separate outputs. One being good does not")
    print("     make the other good, and they can disagree on the same compounds.")

    kinds = sorted({row["kind"] for row in family})
    print("  3. None of these is an experimental measurement.")
    print(f"     registered kinds in this family: {', '.join(kinds)}")
    print("     Experimental binding evidence lives in a measurement record, not a")
    print("     model record. No entry above can be cited for what a compound does.")
    print()


def check(extract: dict) -> list[str]:
    """Recompute what must hold across the extract. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    declared = {label: set(tasks) for label, tasks in extract["claim_classes"].items()}
    record_result(
        declared == CLAIM_CLASSES,
        "the extract declares the same five claim classes this inspector groups by",
    )

    family = structure_family(extract)
    record_result(len(family) > 0, f"the extract contains {len(family)} structure-family systems")
    record_result(
        len(family) == len(extract["records"]),
        "every extracted record belongs to the family, so nothing was carried in by name",
    )
    record_result(
        all(row.get("tasks") for row in family),
        "every system in the family declares at least one task, so none is silently included",
    )
    record_result(
        all(row.get("last_verified") for row in family),
        "every system carries a review date",
    )

    cofolders = [row for row in family if "co-folding" in (row.get("tasks") or ())]
    with_training_data = [
        row["id"] for row in cofolders if row["openness"]["training_data"] != "unverified"
    ]
    record_result(
        all(
            not (
                row["openness"]["training_data"] != "unverified"
                and row["openness"]["evaluation_code"] != "unverified"
            )
            for row in cofolders
        ),
        f"no co-folding system evidences both its training data and the code behind its"
        f" accuracy claim ({len(with_training_data)} of {len(cofolders)} evidence their"
        " training data, none evidences the evaluation code)",
    )
    published = sorted(row["id"] for row in family if "evaluation_code" in evidenced(row))
    # The co-folding systems are the ones whose accuracy claim this laboratory
    # treats as the load-bearing case, and none of them publishes the code that
    # produced the number. The wider family has exceptions, and they are named
    # rather than hidden, so a reader can see which systems can be rechecked.
    record_result(
        all("evaluation_code" not in evidenced(row) for row in cofolders),
        f"no co-folding system evidences the evaluation code behind its accuracy claim "
        f"({len(cofolders)} of {len(cofolders)})",
    )
    print(
        f"  NOTE  {len(published)} of {len(family)} systems in the family evidence the "
        f"evaluation code behind their accuracy claim"
        + (f": {', '.join(published)}" if published else "")
    )

    dual = sorted(
        row["id"]
        for row in family
        if {"co-folded complex", "affinity estimate"} <= set(classes_of(row))
    )
    record_result(
        len(dual) == 1,
        f"exactly one system claims both a co-folded complex and an affinity estimate: {dual}",
    )

    measurement_kinds = {"database", "dataset"}
    record_result(
        not measurement_kinds & {row["kind"] for row in family},
        "no system in the family is a measurement record,"
        " so none carries experimental binding evidence",
    )

    modality_classes: dict[str, set[str]] = {}
    for row in family:
        for label in classes_of(row):
            for modality in row.get("modalities") or ():
                modality_classes.setdefault(modality, set()).add(label)
    record_result(
        any(len(labels) > 1 for labels in modality_classes.values()),
        "at least one modality label spans more than one claim class,"
        " so the label cannot name the claim",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    extract = load()

    print(f"Extract {EXTRACT.relative_to(ROOT)}")
    print(f"sliced from {extract['source']} with {extract['source_records']} records")
    print()
    if action == "show":
        show_classes(extract)
        show_confusions(extract)
        print("Run 'check' to recompute the relationships between these records.")
        return

    print("CLAIM CHECKS")
    failures = check(extract)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies the extract's own consistency, not any")
    print("system's accuracy, which is the point of the second-to-last check.")


if __name__ == "__main__":
    main()
