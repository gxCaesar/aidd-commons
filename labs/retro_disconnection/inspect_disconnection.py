"""Compare disconnection families, and keep route recovery apart from feasibility.

Rule, retrieval, template and learned disconnections are usually compared with a
single recovery percentage. That number hides two things. It hides that the
families fail for different reasons, because each inherits its coverage from
somewhere different. And it hides that recovering a recorded route says nothing
about whether the route can be run.

    python labs/retro_disconnection/inspect_disconnection.py compare
    python labs/retro_disconnection/inspect_disconnection.py check

Reads two committed JSON files and applies reaction SMARTS with RDKit. No model
is trained or executed, no reaction is run, and nothing here is a synthesis
proposal.
"""

import argparse
import json
import sys
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
ROUTES = LAB / "routes.json"
METHODS = LAB / "methods.json"


def load() -> tuple[dict, dict]:
    return (
        json.loads(ROUTES.read_text(encoding="utf-8")),
        json.loads(METHODS.read_text(encoding="utf-8")),
    )


def canonical_set(smiles_list: list[str]) -> str:
    return ".".join(sorted(Chem.CanonSmiles(s) for s in smiles_list))


def apply_transforms(transforms: dict, route: dict) -> set[str]:
    """Every disconnection the family proposes for this product."""
    transform = transforms.get(route["transformation_class"])
    if transform is None:
        return set()
    reaction = AllChem.ReactionFromSmarts(transform)
    product = Chem.MolFromSmiles(route["product"])
    proposals = set()
    for outcome in reaction.RunReactants((product,)):
        try:
            proposals.add(".".join(sorted(Chem.MolToSmiles(mol) for mol in outcome)))
        except Exception:  # noqa: BLE001 - an unparsable outcome is simply not a proposal
            continue
    return proposals


def run_family(routes: dict, methods: dict, family: str) -> dict[str, dict]:
    """What one family proposes for every route, and whether the record is among it."""
    spec = methods["families"][family]
    members = set(routes["precedent_set"]["members"])
    by_id = {row["id"]: row for row in routes["routes"]}
    results = {}
    for route in routes["routes"]:
        recorded = canonical_set(route["recorded_reactants"])
        if family == "retrieval":
            hit = route["id"] in members
            proposals = {canonical_set(by_id[route["id"]]["recorded_reactants"])} if hit else set()
        else:
            proposals = apply_transforms(spec.get("transforms", {}), route)
        results[route["id"]] = {
            "recovered": recorded in proposals,
            "proposals": len(proposals),
            "in_precedent": route["id"] in members,
            "transformation_class": route["transformation_class"],
        }
    return results


def score(results: dict[str, dict], subset: set[str] | None = None) -> tuple[int, int]:
    rows = [row for key, row in results.items() if subset is None or key in subset]
    return sum(1 for row in rows if row["recovered"]), len(rows)


def runnable_families(methods: dict) -> list[str]:
    return [name for name, spec in methods["families"].items() if spec["runs_here"]]


def show_comparison(routes: dict, methods: dict) -> None:
    """Three families run, one declared, and the reasons they fail differ."""
    members = set(routes["precedent_set"]["members"])
    unseen = {row["id"] for row in routes["routes"]} - members
    families = runnable_families(methods)
    total = len(routes["routes"])

    print(f"DISCONNECTION FAMILIES OVER {total} RECORDED ROUTES")
    for name, spec in methods["families"].items():
        mark = "runs" if spec["runs_here"] else "DECLARED, NOT RUN"
        print(f"  {name:<11} {mark:<18} coverage depends on {spec['coverage_depends_on']}")
    print()

    print(f"  {'family':<11} {'all':>8} {'in precedent':>14} {'not in precedent':>18}")
    results = {}
    for name in families:
        results[name] = run_family(routes, methods, name)
        overall = score(results[name])
        seen = score(results[name], members)
        new = score(results[name], unseen)
        print(
            f"  {name:<11} {overall[0]:>3}/{overall[1]:<4} {seen[0]:>7}/{seen[1]:<6}"
            f" {new[0]:>11}/{new[1]:<6}"
        )
    print()

    print("THE SAME METHOD, TWO SCORES, ONE SPLIT")
    retrieval = results["retrieval"]
    seen_hit, seen_n = score(retrieval, members)
    all_hit, all_n = score(retrieval, unseen | members)
    print(f"  Retrieval recovers {seen_hit} of {seen_n} routes that are in the precedent set.")
    print(f"  That is {seen_hit / seen_n:.0%}, and it is a lookup succeeding on its own table.")
    print(f"  Over every route it recovers {all_hit} of {all_n}, {all_hit / all_n:.0%}.")
    print("  Neither number is wrong. Which one gets reported is decided entirely by the")
    print("  split, and a method that memorises is the one most rewarded by choosing badly.")
    print()

    print("THE FAMILIES FAIL FOR DIFFERENT REASONS")
    absent = routes["precedent_set"]["classes_absent"]
    print(f"  The precedent set contains no {', '.join(absent)} reaction.")
    for name in families:
        missed = sorted(
            key
            for key, row in results[name].items()
            if not row["recovered"] and row["transformation_class"] in absent
        )
        print(f"    {name:<11} misses {len(missed)} route(s) of that class: {missed or 'none'}")
    print("  Retrieval misses them because those molecules are not in its table.")
    print("  Templates miss them because no template was extracted for a class the")
    print("  dataset never contained. Hand-written rules cover the class because")
    print("  someone chose to write it. Same score column, three different causes.")
    print()

    multi = sorted(key for key, row in results["rule"].items() if row["proposals"] > 1)
    print("RECOVERING A ROUTE IS NOT BEING RIGHT")
    print(f"  On {len(multi)} product(s) the rule family proposes more than one")
    print(f"  disconnection: {multi}. Recovery means the recorded route was among the")
    print("  proposals, not that the method selected it or preferred it.")
    print()


def show_feasibility(routes: dict) -> None:
    print("WHAT NO SCORE ABOVE ESTABLISHES")
    print(f"  laboratory feasibility: {routes['laboratory_feasibility']}")
    print(f"  {routes['why_feasibility_is_not_assessed']}")
    print()
    print("  This is the same boundary the generation gate records when it calls its")
    print("  structural filters a proxy. A disconnection that recovers the recorded")
    print("  route can still need a reagent nobody sells, a protecting group nobody")
    print("  added, or conditions that destroy the rest of the molecule.")
    print()


def check(routes: dict, methods: dict) -> list[str]:
    """Recompute every relationship from the committed files. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    members = set(routes["precedent_set"]["members"])
    unseen = {row["id"] for row in routes["routes"]} - members
    families = runnable_families(methods)

    record_result(
        all(
            Chem.MolFromSmiles(row["product"]) is not None
            and all(Chem.MolFromSmiles(r) is not None for r in row["recorded_reactants"])
            for row in routes["routes"]
        ),
        f"every product and recorded reactant in the {len(routes['routes'])} routes parses",
    )
    if failures:
        print("  ....  a structure does not parse, so no family is run against the set")
        return failures

    results = {name: run_family(routes, methods, name) for name in families}

    record_result(
        len(methods["families"]) == 4,
        f"the comparison declares all four disconnection families: {sorted(methods['families'])}",
    )
    record_result(
        len(families) == 3 and methods["families"]["learned"]["runs_here"] is False,
        f"three families run and the learned family is declared without being run: {families}",
    )
    record_result(
        bool(methods["families"]["learned"].get("why_not_run")),
        "the family that does not run states why, so the boundary is not silent",
    )
    record_result(
        routes["laboratory_feasibility"] == "not_assessed",
        "the route set records laboratory feasibility as not assessed",
    )
    rule_hits, rule_total = score(results["rule"])
    record_result(
        rule_hits == rule_total,
        f"the hand-written rules recover every recorded route: {rule_hits} of {rule_total}",
    )
    retrieval_seen = score(results["retrieval"], members)
    retrieval_unseen = score(results["retrieval"], unseen)
    record_result(
        retrieval_seen[0] == retrieval_seen[1] and retrieval_unseen[0] == 0,
        f"retrieval recovers {retrieval_seen[0]}/{retrieval_seen[1]} inside the precedent set"
        f" and {retrieval_unseen[0]}/{retrieval_unseen[1]} outside it",
    )
    record_result(
        score(results["retrieval"])[0] < rule_hits,
        "retrieval scores perfectly on its own table and below the rules overall,"
        " so the split decides its headline",
    )

    absent = set(routes["precedent_set"]["classes_absent"])
    template_absent = [
        key
        for key, row in results["template"].items()
        if row["transformation_class"] in absent and row["recovered"]
    ]
    record_result(
        not template_absent,
        f"templates recover nothing in a class the precedent set never contained: {absent}",
    )
    rule_absent = [
        key
        for key, row in results["rule"].items()
        if row["transformation_class"] in absent and row["recovered"]
    ]
    record_result(
        len(rule_absent) > 0,
        f"hand-written rules do cover that class, so the two families differ in cause:"
        f" {sorted(rule_absent)}",
    )
    record_result(
        set(methods["families"]["template"]["transforms"])
        == set(routes["precedent_set"]["classes_present"]),
        "the template family carries exactly the classes present in the precedent set",
    )
    actual_classes = {
        row["transformation_class"] for row in routes["routes"] if row["id"] in members
    }
    record_result(
        actual_classes == set(routes["precedent_set"]["classes_present"])
        and not (actual_classes & set(routes["precedent_set"]["classes_absent"])),
        "the precedent set's declared classes match the classes its members actually carry:"
        f" {sorted(actual_classes)}",
    )

    multi = [key for key, row in results["rule"].items() if row["proposals"] > 1]
    record_result(
        len(multi) > 0,
        f"at least one product admits more than one rule disconnection: {sorted(multi)}",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="compare", choices=["compare", "check"])
    action = parser.parse_args().action
    routes, methods = load()

    print(f"Routes {ROUTES.relative_to(ROOT)} ({len(routes['routes'])} constructed)")
    print(f"Methods {METHODS.relative_to(ROOT)}")
    print()
    if action == "compare":
        show_comparison(routes, methods)
        show_feasibility(routes)
        print("Run 'check' to recompute these counts from the committed files.")
        return

    print("DISCONNECTION CHECKS")
    failures = check(routes, methods)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies how the families differ and where the")
    print("comparison stops. It establishes nothing about any route being makeable.")


if __name__ == "__main__":
    main()
