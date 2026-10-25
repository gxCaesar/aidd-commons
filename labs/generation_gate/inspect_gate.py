"""Freeze a design objective before generation, then screen candidates against it.

Two decisions are usually collapsed into one sentence about a generative run.
The first is what the objective was, declared before any candidate existed. The
second is which of six checks a candidate survived, each with its own
denominator. A single "percent valid" number reports neither.

    python labs/generation_gate/inspect_gate.py objective
    python labs/generation_gate/inspect_gate.py screen
    python labs/generation_gate/inspect_gate.py check

This lab reads three committed files: a frozen objective, a constructed candidate
set, and the FreeSolv split table used as the declared reference. It runs no
generative model, makes no network request, downloads nothing, and proposes
nothing for synthesis or measurement. RDKit is required because the gates are
computed from structures; nothing else outside the standard library is used.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
OBJECTIVE = LAB / "objective.json"
CANDIDATES = LAB / "candidates.json"

# The gates in the order they are applied. Each one's denominator is the previous
# one's survivors, which is the whole reason a single percentage is unreadable.
GATE_ORDER = (
    "validity",
    "uniqueness",
    "novelty",
    "desired-property",
    "prohibited-motif",
    "synthesis-limit",
)
PROPERTY_FUNCTIONS = {
    "heavy_atom_count": lambda mol: float(mol.GetNumHeavyAtoms()),
    "molecular_weight": Descriptors.MolWt,
    "crippen_logp": Crippen.MolLogP,
    "rotatable_bond_count": lambda mol: float(rdMolDescriptors.CalcNumRotatableBonds(mol)),
}


def load() -> tuple[dict, dict, dict[str, str]]:
    objective = json.loads(OBJECTIVE.read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    reference_path = ROOT / objective["target_context"]["reference_set"]
    if not reference_path.is_file():
        raise SystemExit(f"missing declared reference set: {reference_path}")
    with reference_path.open(encoding="utf-8") as stream:
        reference = {
            Chem.CanonSmiles(row["canonical_smiles"]): row["split"]
            for row in csv.DictReader(stream)
        }
    return objective, candidates, reference


def property_failures(objective: dict, mol: Chem.Mol) -> list[str]:
    failures = []
    for spec in objective["desired_properties"]:
        value = PROPERTY_FUNCTIONS[spec["name"]](mol)
        bound = spec["bound"]
        if value < bound["minimum"] or value > bound["maximum"]:
            failures.append(
                f"{spec['name']}={value:.4g} outside [{bound['minimum']}, {bound['maximum']}]"
            )
    return failures


def motif_failures(objective: dict, mol: Chem.Mol) -> list[str]:
    return [
        motif["name"]
        for motif in objective["prohibited_motifs"]
        if mol.HasSubstructMatch(Chem.MolFromSmarts(motif["smarts"]))
    ]


def synthesis_failures(objective: dict, mol: Chem.Mol) -> list[str]:
    limits = objective["synthesis_limits"]
    failures = []
    rings = rdMolDescriptors.CalcNumRings(mol)
    if rings > limits["maximum_ring_count"]:
        failures.append(f"ring_count={rings} above {limits['maximum_ring_count']}")
    centres = len(
        Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    )
    if centres > limits["maximum_stereocentre_count"]:
        failures.append(f"stereocentres={centres} above {limits['maximum_stereocentre_count']}")
    prohibited = sorted(
        {atom.GetSymbol() for atom in mol.GetAtoms()} & set(limits["prohibited_elements"])
    )
    if prohibited:
        failures.append(f"prohibited elements {prohibited}")
    return failures


def screen(objective: dict, candidates: dict, reference: dict[str, str]) -> dict:
    """Apply the gates in order. Each gate's denominator is the previous survivors."""
    rows = []
    seen: dict[str, str] = {}
    for entry in candidates["candidates"]:
        row = {"id": entry["id"], "smiles": entry["smiles"], "label": entry["constructed_for"]}
        mol = Chem.MolFromSmiles(entry["smiles"])
        if mol is None:
            row.update({"gate": "validity", "reason": "does not parse as a molecule"})
            rows.append(row)
            continue
        canonical = Chem.MolToSmiles(mol)
        row["canonical"] = canonical
        if canonical in seen:
            row.update({"gate": "uniqueness", "reason": f"same molecule as {seen[canonical]}"})
            rows.append(row)
            continue
        seen[canonical] = entry["id"]
        if canonical in reference:
            split = reference[canonical]
            row.update(
                {
                    "gate": "novelty",
                    "reason": f"present in the declared reference set, {split} split",
                    "reference_split": split,
                }
            )
            rows.append(row)
            continue
        failures = property_failures(objective, mol)
        if failures:
            row.update({"gate": "desired-property", "reason": "; ".join(failures)})
            rows.append(row)
            continue
        motifs = motif_failures(objective, mol)
        if motifs:
            row.update({"gate": "prohibited-motif", "reason": f"contains {', '.join(motifs)}"})
            rows.append(row)
            continue
        limits = synthesis_failures(objective, mol)
        if limits:
            row.update({"gate": "synthesis-limit", "reason": "; ".join(limits)})
            rows.append(row)
            continue
        row.update({"gate": None, "reason": "survived every declared gate"})
        rows.append(row)

    funnel, entering = [], list(rows)
    for gate in GATE_ORDER:
        stopped = [row for row in entering if row["gate"] == gate]
        funnel.append(
            {
                "gate": gate,
                "entered": len(entering),
                "stopped": len(stopped),
                "survived": len(entering) - len(stopped),
                "ids": [row["id"] for row in stopped],
            }
        )
        entering = [row for row in entering if row["gate"] != gate]
    return {"rows": rows, "funnel": funnel, "survivors": entering}


def memorization_split(result: dict) -> dict[str, list[str]]:
    """Novelty failures are not one fact. Which reference split they came from matters."""
    grouped: dict[str, list[str]] = {}
    for row in result["rows"]:
        if row["gate"] == "novelty":
            grouped.setdefault(row["reference_split"], []).append(row["id"])
    return {split: sorted(ids) for split, ids in sorted(grouped.items())}


def selected_batch(objective: dict, result: dict) -> list[str]:
    """Apply the frozen selection rule, then the frozen abstention rule."""
    survivors = sorted(
        result["survivors"],
        key=lambda row: (Chem.MolFromSmiles(row["canonical"]).GetNumHeavyAtoms(), row["canonical"]),
    )
    size = objective["experimental_decision"]["batch_size"]
    return [row["id"] for row in survivors[:size]]


def show_objective(objective: dict) -> None:
    """What was frozen, and what each part had to carry to be checkable."""
    print(f"FROZEN DESIGN OBJECTIVE {objective['objective_id']} ({objective['frozen_on']})")
    context = objective["target_context"]
    print(f"  target context: {context['chemical_space']}")
    print(
        f"    reference set {context['reference_set']} ({context['reference_set_size']} molecules)"
    )
    print(f"    not part of this objective: {context['what_this_context_is_not']}")
    print(f"  desired properties ({len(objective['desired_properties'])})")
    for spec in objective["desired_properties"]:
        bound = spec["bound"]
        print(
            f"    {spec['name']:<22} [{bound['minimum']}, {bound['maximum']}]"
            f"  via {spec['computed_by']}"
        )
    print(f"  prohibited motifs ({len(objective['prohibited_motifs'])})")
    for motif in objective["prohibited_motifs"]:
        print(f"    {motif['name']:<22} {motif['smarts']}")
    limits = objective["synthesis_limits"]
    print("  synthesis limits")
    print(
        f"    rings <= {limits['maximum_ring_count']},"
        f" stereocentres <= {limits['maximum_stereocentre_count']}"
    )
    print(f"    prohibited elements {limits['prohibited_elements']}")
    print(f"    route feasibility: {limits['route_feasibility']}")
    decision = objective["experimental_decision"]
    print("  experimental decision")
    print(f"    question: {decision['question']}")
    print(f"    batch size {decision['batch_size']} into {decision['assay']}")
    print(f"    selection: {decision['selection_rule']}")
    print(f"    abstention: {decision['abstention_rule']}")
    print()
    print("  Each part carries the field that makes it checkable. A property without a")
    print("  bound is a wish, a motif without a SMARTS cannot be applied, and an")
    print("  objective without a decision cannot say what a passing candidate is for.")
    print()


def show_screen(objective: dict, result: dict) -> None:
    """The funnel, the one number it replaces, and the two things it cannot say."""
    funnel = result["funnel"]
    total = funnel[0]["entered"]
    print(f"GATE FUNNEL OVER {total} CONSTRUCTED CANDIDATES")
    print(f"  {'gate':<18} {'entered':>8} {'stopped':>8} {'survived':>9}   stopped ids")
    for step in funnel:
        ids = ", ".join(step["ids"]) or "-"
        print(
            f"  {step['gate']:<18} {step['entered']:>8} {step['stopped']:>8}"
            f" {step['survived']:>9}   {ids}"
        )
    survivors = [row["id"] for row in result["survivors"]]
    print(f"  survivors: {survivors}")
    print()

    valid = total - funnel[0]["stopped"]
    print("THE ONE NUMBER AND WHAT IT HIDES")
    print(f"  Reported as a single figure, this run is {valid}/{total} valid.")
    print(f"  Candidates that survived every declared gate: {len(survivors)}/{total}.")
    print("  The two numbers differ because each gate has its own denominator, and")
    print("  every gate after the first is applied only to what reached it.")
    print()

    print("NOVELTY IS NOT ONE FACT")
    grouped = memorization_split(result)
    for split, ids in grouped.items():
        print(f"  present in the {split} split: {ids}")
    not_novel = sum(len(ids) for ids in grouped.values())
    train = grouped.get("train", [])
    held_out = [row for split, ids in grouped.items() if split != "train" for row in ids]
    print(f"  Against the whole reference set, {not_novel} candidates are not novel.")
    print(f"  Against the training split alone, {len(train)} are memorized: {train}")
    print(f"  The remaining {len(held_out)} are in held-out splits: {held_out}")
    print("  A novelty rate quoted without naming its reference set is unreadable, and")
    print("  memorization is the same gate applied to a different set, not a second gate.")
    print()

    print("WHAT THE SYNTHESIS GATE DID NOT ESTABLISH")
    print(f"  route feasibility: {objective['synthesis_limits']['route_feasibility']}")
    print(f"  {objective['synthesis_limits']['what_these_limits_are']}")
    print()

    batch = selected_batch(objective, result)
    decision = objective["experimental_decision"]
    print("THE DECISION THE OBJECTIVE DECLARED")
    print(f"  {decision['question']}")
    print(f"  frozen selection rule applied: {batch}")
    if len(batch) < decision["batch_size"]:
        print(f"  shortfall recorded: {len(batch)} of {decision['batch_size']}, no gate relaxed")
    print(f"  {decision['what_a_pass_does_not_mean']}")
    print()


def check(objective: dict, candidates: dict, reference: dict[str, str]) -> list[str]:
    """Recompute what must hold across the objective and the screen. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    required = (
        "target_context",
        "desired_properties",
        "prohibited_motifs",
        "synthesis_limits",
        "experimental_decision",
    )
    missing = [part for part in required if not objective.get(part)]
    record_result(not missing, f"the objective declares all five required parts, missing {missing}")
    record_result(
        objective.get("declared_before_generation") is True and bool(objective.get("frozen_on")),
        "the objective records that it was frozen before generation, and when",
    )
    unbounded = [
        spec["name"]
        for spec in objective["desired_properties"]
        if "minimum" not in spec.get("bound", {}) or "maximum" not in spec.get("bound", {})
    ]
    record_result(
        not unbounded, f"every desired property carries a two-sided bound, unbounded {unbounded}"
    )
    unapplicable = [
        motif["name"]
        for motif in objective["prohibited_motifs"]
        if Chem.MolFromSmarts(motif["smarts"]) is None
    ]
    record_result(
        not unapplicable,
        f"every prohibited motif compiles to an applicable pattern, broken {unapplicable}",
    )
    decision = objective.get("experimental_decision") or {}
    record_result(
        all(decision.get(field) for field in ("question", "batch_size", "assay", "selection_rule")),
        "the objective names the experimental decision, its assay, batch size and selection rule",
    )
    record_result(
        bool(decision.get("abstention_rule")),
        "the objective declares what to do when too few candidates survive",
    )
    record_result(
        (objective.get("synthesis_limits") or {}).get("route_feasibility") == "not_assessed",
        "the objective records route feasibility as not assessed rather than implying it",
    )

    if failures:
        print("  ....  the objective is not checkable, so the screen is not run against it")
        return failures

    result = screen(objective, candidates, reference)
    total = len(candidates["candidates"])
    record_result(
        len(reference) == objective["target_context"]["reference_set_size"],
        f"the declared reference set size matches the file: {len(reference)} molecules",
    )
    train = [split for split in reference.values() if split == "train"]
    record_result(
        len(train) == objective["target_context"]["training_split_size"],
        f"the declared training split size matches the file: {len(train)} molecules",
    )

    mislabelled = [row["id"] for row in result["rows"] if (row["gate"] or "none") != row["label"]]
    record_result(
        not mislabelled,
        "every candidate is stopped by the gate its teaching label names,"
        f" mismatched {mislabelled}",
    )
    valid = total - result["funnel"][0]["stopped"]
    survivors = len(result["survivors"])
    record_result(
        valid > survivors,
        f"the single validity figure ({valid}/{total})"
        f" overstates the survivors ({survivors}/{total})",
    )
    record_result(
        all(
            step["entered"] == result["funnel"][index - 1]["survived"]
            for index, step in enumerate(result["funnel"])
            if index
        ),
        "each gate's denominator is the previous gate's survivors, so no yield is quoted flat",
    )

    expected = {
        entry["id"]: entry["expected_reference_split"]
        for entry in candidates["candidates"]
        if "expected_reference_split" in entry
    }
    observed = {
        row["id"]: row.get("reference_split") for row in result["rows"] if row["gate"] == "novelty"
    }
    record_result(
        expected == observed,
        "each non-novel candidate came from the reference split its label names:"
        f" {sorted(expected)}",
    )

    grouped = memorization_split(result)
    record_result(
        len(grouped) >= 2,
        f"novelty failures come from more than one reference split: {sorted(grouped)}",
    )
    record_result(
        len(grouped.get("train", [])) < sum(len(ids) for ids in grouped.values()),
        "memorization against the training split is a strict subset of non-novelty",
    )

    batch = selected_batch(objective, result)
    record_result(
        len(batch) == min(decision["batch_size"], survivors),
        f"the frozen selection rule fills the batch from survivors only: {batch}",
    )
    record_result(
        set(batch) <= {row["id"] for row in result["survivors"]},
        "no candidate stopped by a gate reaches the batch",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", nargs="?", default="objective", choices=["objective", "screen", "check"]
    )
    action = parser.parse_args().action
    objective, candidates, reference = load()

    print(f"Objective {OBJECTIVE.relative_to(ROOT)}")
    print(
        f"Candidates {CANDIDATES.relative_to(ROOT)} ({len(candidates['candidates'])} constructed)"
    )
    print()
    if action == "objective":
        show_objective(objective)
        print("Run 'screen' to apply it, or 'check' to recompute every relationship.")
        return
    if action == "screen":
        show_screen(objective, screen(objective, candidates, reference))
        print("Run 'check' to recompute these counts from the committed files.")
        return

    print("GATE CHECKS")
    failures = check(objective, candidates, reference)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies that the objective is checkable and that the")
    print("screen applied it as frozen. It establishes nothing about any candidate.")


if __name__ == "__main__":
    main()
