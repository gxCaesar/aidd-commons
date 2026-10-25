"""Separate the seven components a docking score comes out of, and check comparability.

A docking score is reported as a number with units, which invites comparison with
any other number carrying those units. It is the output of seven declared choices,
and two protocols that differ in any of the score-affecting ones produce numbers on
different scales. This command reads committed protocol declarations and works out
which pairs may be compared at all.

    python labs/docking_protocol/inspect_protocol.py show
    python labs/docking_protocol/inspect_protocol.py check

No docking program is run, no structure is prepared, and the reported numbers are
illustrative rather than results. Reads one committed JSON file, standard library
only.
"""

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
PROTOCOLS = LAB / "protocols.json"


def load() -> dict:
    return json.loads(PROTOCOLS.read_text(encoding="utf-8"))


def scoring_components(data: dict) -> list[str]:
    return [name for name, spec in data["components"].items() if spec["affects_the_number"]]


def evidence_components(data: dict) -> list[str]:
    return [name for name, spec in data["components"].items() if not spec["affects_the_number"]]


def differences(data: dict, left: dict, right: dict) -> list[str]:
    return [name for name in data["components"] if left[name] != right[name]]


def comparable(data: dict, left: dict, right: dict) -> tuple[bool, list[str]]:
    """Comparable only when identical on every component that affects the number."""
    blocking = [name for name in scoring_components(data) if left[name] != right[name]]
    return not blocking, blocking


def unsupported_claims(data: dict, protocol: dict) -> list[str]:
    """What a protocol cannot report, given what it left undeclared."""
    missing = []
    if protocol["validation"] == "none":
        missing.append("any claim that its scores behave as scores, because nothing was validated")
    if protocol["decoys"] == "none":
        missing.append("an enrichment figure, because there is no decoy set to enrich against")
    return missing


def show(data: dict) -> None:
    protocols = data["protocols"]
    print("SEVEN COMPONENTS, AND WHICH OF THEM MOVE THE NUMBER")
    for name, spec in data["components"].items():
        mark = "moves the number" if spec["affects_the_number"] else "moves what it means"
        print(f"  {name:<16} {mark}")
        print(f"      {spec['why']}")
    print()

    print("THREE PROTOCOLS, ONE REFERENCE LIGAND, THREE NUMBERS IN THE SAME UNITS")
    for protocol in protocols:
        print(
            f"  {protocol['id']:<15} {protocol['reported_score_for_reference_ligand']:>6}"
            f"   rescoring: {protocol['rescoring']}"
        )
        print(
            f"      constraints {protocol['constraints']}; decoys {protocol['decoys']};"
            f" validation {protocol['validation']}"
        )
    print()

    print("WHICH PAIRS MAY BE COMPARED")
    for left, right in combinations(protocols, 2):
        ok, blocking = comparable(data, left, right)
        verdict = "comparable" if ok else "NOT comparable"
        print(f"  {left['id']} against {right['id']}: {verdict}")
        if blocking:
            for name in blocking:
                print(f"      differs in {name}, which moves the number")
    print()
    print(f"  {data['comparability_rule']}")
    print()

    baseline = next(p for p in protocols if p["id"] == "p-baseline")
    rescored = next(p for p in protocols if p["id"] == "p-rescored")
    gap = (
        baseline["reported_score_for_reference_ligand"]
        - rescored["reported_score_for_reference_ligand"]
    )
    print("THE MOST TEMPTING COMPARISON IS THE ONE TO REFUSE")
    print(f"  {rescored['id']} reports {rescored['reported_score_for_reference_ligand']} against")
    print(
        f"  {baseline['id']} at {baseline['reported_score_for_reference_ligand']},"
        f" a difference of {abs(gap):.1f} in the same units,"
    )
    print("  on the same ligand and the same structure. The two protocols differ only in")
    print("  rescoring, so the second number came out of a different function. Nothing")
    print("  about the ligand changed and the gap is entirely the protocol.")
    print()


def show_evidence(data: dict) -> None:
    print("WHAT EACH PROTOCOL CANNOT REPORT")
    for protocol in data["protocols"]:
        missing = unsupported_claims(data, protocol)
        print(f"  {protocol['id']}")
        for line in missing or ["nothing above is out of reach for this protocol"]:
            print(f"      {line}")
    print()
    print("  Validation and decoys move no score. They decide whether a score means")
    print("  anything and whether an enrichment figure exists, which is why a protocol")
    print("  that leaves them undeclared can still produce a full column of numbers.")
    print()
    print("WHAT A SCORE IS NOT")
    print(f"  {data['what_a_score_is_not']}")
    print()


def check(data: dict) -> list[str]:
    """Recompute every relationship from the committed declarations. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    names = set(data["components"])
    record_result(
        len(names) == 7,
        f"the record names seven components a score comes out of: {sorted(names)}",
    )
    record_result(
        all(spec.get("why") for spec in data["components"].values()),
        "every component says why it does or does not move the number",
    )
    incomplete = [protocol["id"] for protocol in data["protocols"] if not names <= set(protocol)]
    record_result(
        not incomplete,
        f"every protocol declares all seven components, incomplete {incomplete}",
    )
    if failures:
        print("  ....  a protocol is not fully declared, so no comparison is attempted")
        return failures

    record_result(
        set(evidence_components(data)) == {"decoys", "validation"},
        f"decoys and validation are the components that move meaning rather than the"
        f" number: {sorted(evidence_components(data))}",
    )

    pairs = list(combinations(data["protocols"], 2))
    verdicts = {(left["id"], right["id"]): comparable(data, left, right) for left, right in pairs}
    record_result(
        all(not ok for ok, _ in verdicts.values()),
        f"no pair in this set may be compared, and each is blocked by a named component:"
        f" { {k: v[1] for k, v in verdicts.items()} }",
    )

    baseline = next(p for p in data["protocols"] if p["id"] == "p-baseline")
    rescored = next(p for p in data["protocols"] if p["id"] == "p-rescored")
    differing = differences(data, baseline, rescored)
    record_result(
        differing == ["rescoring"],
        f"the baseline and the rescored protocol differ in exactly one component,"
        f" {differing}, which is the cleanest case of an incomparable pair",
    )
    record_result(
        baseline["reported_score_for_reference_ligand"]
        != rescored["reported_score_for_reference_ligand"],
        f"they report different numbers for the same reference ligand:"
        f" {baseline['reported_score_for_reference_ligand']} against"
        f" {rescored['reported_score_for_reference_ligand']}",
    )

    unvalidated = [
        protocol["id"] for protocol in data["protocols"] if protocol["validation"] == "none"
    ]
    record_result(
        len(unvalidated) > 0,
        f"at least one protocol declares no validation, so its scores were never checked"
        f" to behave as scores: {unvalidated}",
    )
    record_result(
        all(
            unsupported_claims(data, protocol)
            for protocol in data["protocols"]
            if protocol["id"] in unvalidated
        ),
        "an unvalidated protocol is recorded as unable to support the claims it lacks"
        " the components for",
    )
    without_decoys = [
        protocol["id"] for protocol in data["protocols"] if protocol["decoys"] == "none"
    ]
    record_result(
        all(
            any("enrichment" in line for line in unsupported_claims(data, protocol))
            for protocol in data["protocols"]
            if protocol["id"] in without_decoys
        ),
        f"a protocol without decoys cannot report an enrichment figure: {without_decoys}",
    )
    record_result(
        bool(data["what_a_score_is_not"]),
        "the record states what a reported score is not, rather than leaving it implied",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    data = load()

    print(f"Protocols {PROTOCOLS.relative_to(ROOT)}")
    print(f"{len(data['protocols'])} declared protocols, no docking program run")
    print()
    if action == "show":
        show(data)
        show_evidence(data)
        print("Run 'check' to recompute these comparability verdicts.")
        return

    print("PROTOCOL CHECKS")
    failures = check(data)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies which scores may be compared and what each")
    print("protocol cannot report, not that any score is correct.")


if __name__ == "__main__":
    main()
