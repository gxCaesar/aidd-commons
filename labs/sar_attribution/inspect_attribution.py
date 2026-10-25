"""Explain a well-fitted model whose true cause is known, and watch the explanation miss it.

Model explanations are routinely read as statements about which atoms cause
activity. This lab makes that reading checkable. The labels come from a rule
declared in the committed dataset, so the cause is known rather than inferred,
and a second substructure is correlated with it by construction. The model fits,
the explanation is computed, and both can be compared against the truth.

    python labs/sar_attribution/inspect_attribution.py show
    python labs/sar_attribution/inspect_attribution.py check

Reads one committed JSON file. RDKit supplies fingerprints with bit provenance
and NumPy solves the ridge system. No activity value here is real and no molecule
is a design proposal.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DATASET = LAB / "dataset.json"
BITS = 1024
RADIUS = 2
PENALTY = 1.0


def load() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def featurise(smiles: str) -> tuple[Chem.Mol, np.ndarray, dict]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"unparsable structure in the committed dataset: {smiles}")
    info: dict = {}
    vector = AllChem.GetMorganFingerprintAsBitVect(mol, RADIUS, nBits=BITS, bitInfo=info)
    return mol, np.array(vector, dtype=float), info


def label(data: dict, mol: Chem.Mol) -> int:
    """The generating rule, applied. This is the only source of truth in the lab."""
    pattern = Chem.MolFromSmarts(data["true_rule"]["smarts"])
    return int(mol.HasSubstructMatch(pattern))


def carries_confounder(data: dict, mol: Chem.Mol) -> bool:
    return mol.HasSubstructMatch(Chem.MolFromSmarts(data["confounder"]["smarts"]))


def fit(data: dict) -> tuple[np.ndarray, float]:
    rows = [featurise(row["smiles"]) for row in data["training"]]
    features = np.array([vector for _, vector, _ in rows])
    truth = np.array([label(data, mol) for mol, _, _ in rows], dtype=float)
    centre = truth.mean()
    weights = np.linalg.solve(
        features.T @ features + PENALTY * np.eye(BITS), features.T @ (truth - centre)
    )
    return weights, float(centre)


def predict(weights: np.ndarray, centre: float, smiles: str) -> float:
    _, vector, _ = featurise(smiles)
    return float(vector @ weights + centre)


def atom_credit(weights: np.ndarray, smiles: str) -> tuple[Chem.Mol, np.ndarray]:
    """Split each active bit's weight across the atoms of the environment that set it."""
    mol, vector, info = featurise(smiles)
    credit = np.zeros(mol.GetNumAtoms())
    for bit, environments in info.items():
        if vector[bit] == 0:
            continue
        share = weights[bit] / len(environments)
        for centre_atom, radius in environments:
            bonds = Chem.FindAtomEnvironmentOfRadiusN(mol, radius, centre_atom) if radius else []
            atoms = {centre_atom}
            for bond_index in bonds:
                bond = mol.GetBondWithIdx(bond_index)
                atoms.add(bond.GetBeginAtomIdx())
                atoms.add(bond.GetEndAtomIdx())
            for atom_index in atoms:
                credit[atom_index] += share / len(atoms)
    return mol, credit


def credit_split(data: dict, weights: np.ndarray, smiles: str) -> dict:
    """How much credit lands on the cause, on the confounder, and elsewhere."""
    mol, credit = atom_credit(weights, smiles)
    cause = set(sum(mol.GetSubstructMatches(Chem.MolFromSmarts(data["true_rule"]["smarts"])), ()))
    proxy = set(sum(mol.GetSubstructMatches(Chem.MolFromSmarts(data["confounder"]["smarts"])), ()))
    rest = [i for i in range(mol.GetNumAtoms()) if i not in cause | proxy]
    return {
        "cause_atoms": sorted(cause),
        "proxy_atoms": sorted(proxy),
        "cause": float(credit[sorted(cause)].sum()) if cause else 0.0,
        "proxy": float(credit[sorted(proxy)].sum()) if proxy else 0.0,
        "rest": float(credit[rest].sum()) if rest else 0.0,
        "total": float(credit.sum()),
    }


def analogue_rows(data: dict, weights: np.ndarray, centre: float) -> list[dict]:
    rows = []
    threshold = data["threshold"]["value"]
    for member in data["analogues"]["members"]:
        mol, _, _ = featurise(member["smiles"])
        prediction = predict(weights, centre, member["smiles"])
        rows.append(
            {
                "id": member["id"],
                "smiles": member["smiles"],
                "breaks": member["breaks"],
                "truth": label(data, mol),
                "confounder": carries_confounder(data, mol),
                "prediction": prediction,
                "call": int(prediction >= threshold),
            }
        )
    return rows


def show(data: dict, weights: np.ndarray, centre: float) -> None:
    rule, proxy = data["true_rule"], data["confounder"]
    print(f"THE RULE THAT GENERATED THE LABELS  {rule['name']}")
    print(f"  {rule['statement']}")
    print(f"  confounder {proxy['name']} with causal role {proxy['causal_role']}")
    print(f"  {proxy['statement']}")
    print()

    errors = [
        abs(predict(weights, centre, row["smiles"]) - label(data, featurise(row["smiles"])[0]))
        for row in data["training"]
    ]
    print("THE MODEL FITS")
    print(f"  largest training error over {len(errors)} molecules: {max(errors):.4f}")
    print("  A model this well fitted is exactly the case where an explanation feels safe.")
    print()

    print("WHERE THE EXPLANATION PUTS THE CREDIT")
    print(f"  {'molecule':<26} {'cause':>9} {'confounder':>12} {'elsewhere':>11}")
    wins = 0
    for row in data["training"]:
        split = credit_split(data, weights, row["smiles"])
        if split["cause"] == 0.0 and split["proxy"] == 0.0:
            continue
        if split["proxy"] > split["cause"]:
            wins += 1
        print(
            f"  {row['smiles']:<26} {split['cause']:>+9.4f}"
            f" {split['proxy']:>+12.4f} {split['rest']:>+11.4f}"
        )
    actives = [r for r in data["training"] if label(data, featurise(r["smiles"])[0])]
    print()
    print(
        f"  The confounder outscores the true cause on {wins} of {len(actives)} active molecules."
    )
    print("  It has no causal role at all. It won because it appears in an identical")
    print(f"  environment every time: {proxy['why_it_wins']}")
    print()


def show_analogues(data: dict, rows: list[dict]) -> None:
    threshold = data["threshold"]["value"]
    print(f"THE ANALOGUES THAT TEST THE HYPOTHESIS  threshold {threshold}, declared before fitting")
    print(f"  {'id':<5} {'molecule':<24} {'cause':>6} {'proxy':>6} {'predicted':>10} {'call':>5}")
    for row in rows:
        print(
            f"  {row['id']:<5} {row['smiles']:<24} {row['truth']:>6}"
            f" {int(row['confounder']):>6} {row['prediction']:>+10.4f} {row['call']:>5}"
        )
    print()

    broken = {row["id"]: row for row in rows if row["id"] in {"a01", "a02"}}
    without_cause, without_proxy = broken["a01"], broken["a02"]
    print("THE RANKING IS INVERTED")
    print(
        f"  {without_cause['id']} has no cause at all and scores"
        f" {without_cause['prediction']:+.4f}."
    )
    print(
        f"  {without_proxy['id']} is genuinely active and scores"
        f" {without_proxy['prediction']:+.4f}."
    )
    gap = abs(without_cause["prediction"] - without_proxy["prediction"])
    print(f"  The model separates two molecules of opposite true activity by {gap:.4f},")
    print("  and it puts them in the wrong order. On this pair the explanation's")
    print("  hypothesis and the generating rule disagree, and the rule is the one that")
    print("  made the labels.")
    print()
    wrong = [row["id"] for row in rows if row["call"] != row["truth"]]
    print(f"  Called wrongly at the declared threshold: {wrong or 'none'}")
    print()


def show_limits() -> None:
    print("WHAT THIS DOES AND DOES NOT LICENSE")
    print("  It licenses a hypothesis. An explanation says which features the model")
    print("  used, and that is a fact about the model. Turning it into a claim about")
    print("  which atoms cause activity needs an analogue that breaks the correlation,")
    print("  which is an experiment rather than a re-reading of the same fit.")
    print("  It does not license a causal atom effect. Here the confounder carried the")
    print("  larger share of credit while having no causal role whatsoever, and that")
    print("  was visible only because the generating rule was known.")
    print("  On real activity data the rule is not known, so the check performed here")
    print("  is unavailable and the analogue is the only route left.")
    print()


def check(data: dict) -> list[str]:
    """Recompute every relationship from the committed dataset. Returns failures."""
    failures: list[str] = []

    def record_result(passed: bool, message: str) -> None:
        print(f"  {'PASS' if passed else 'FAIL'}  {message}")
        if not passed:
            failures.append(message)

    record_result(
        data["threshold"]["declared_before_fitting"] is True
        and data["model"]["declared_before_fitting"] is True,
        "the threshold and the model were declared before fitting",
    )
    record_result(
        data["confounder"]["causal_role"] == "none",
        "the dataset states that the confounder has no causal role",
    )
    molecules = [(row["id"], featurise(row["smiles"])[0]) for row in data["training"]]
    labels = {key: label(data, mol) for key, mol in molecules}
    proxies = {key: carries_confounder(data, mol) for key, mol in molecules}
    record_result(
        all(labels[key] == int(proxies[key]) for key, _ in molecules),
        "cause and confounder are perfectly correlated across the training set,"
        " which is what makes them indistinguishable from it",
    )
    record_result(
        0 < sum(labels.values()) < len(labels),
        f"the training set carries both classes: {sum(labels.values())} active of {len(labels)}",
    )

    weights, centre = fit(data)
    errors = [
        abs(predict(weights, centre, row["smiles"]) - labels[row["id"]]) for row in data["training"]
    ]
    record_result(
        max(errors) < 0.1,
        f"the model fits the training set, largest error {max(errors):.4f}",
    )

    actives = [row for row in data["training"] if labels[row["id"]] == 1]
    splits = {row["id"]: credit_split(data, weights, row["smiles"]) for row in actives}
    proxy_wins = [key for key, split in splits.items() if split["proxy"] > split["cause"]]
    record_result(
        len(proxy_wins) > len(actives) / 2,
        f"the confounder outscores the true cause on {len(proxy_wins)} of {len(actives)}"
        " active molecules, despite having no causal role",
    )
    record_result(
        all(split["proxy"] > 0 for split in splits.values()),
        "every active molecule assigns positive credit to atoms that cause nothing",
    )

    rows = {row["id"]: row for row in analogue_rows(data, weights, centre)}
    record_result(
        set(rows) == {"a01", "a02", "a03", "a04"},
        f"the analogue set carries both broken pairs and both controls: {sorted(rows)}",
    )
    record_result(
        rows["a01"]["truth"] == 0 and rows["a01"]["confounder"] is True,
        "a01 carries the confounder and is inactive under the generating rule",
    )
    record_result(
        rows["a02"]["truth"] == 1 and rows["a02"]["confounder"] is False,
        "a02 lacks the confounder and is active under the generating rule",
    )
    record_result(
        rows["a01"]["prediction"] > rows["a02"]["prediction"],
        f"the model ranks them backwards: {rows['a01']['prediction']:.4f} for the inactive"
        f" against {rows['a02']['prediction']:.4f} for the active",
    )
    gap = abs(rows["a01"]["prediction"] - rows["a02"]["prediction"])
    record_result(
        gap < 0.1,
        f"it separates two molecules of opposite true activity by only {gap:.4f}",
    )
    record_result(
        rows["a02"]["call"] != rows["a02"]["truth"],
        "the genuinely active analogue is called inactive at the declared threshold",
    )
    record_result(
        rows["a03"]["truth"] == 1 and rows["a04"]["truth"] == 0,
        "the two controls carry the labels the generating rule gives them",
    )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="show", choices=["show", "check"])
    action = parser.parse_args().action
    data = load()

    print(f"Dataset {DATASET.relative_to(ROOT)}")
    print(f"{len(data['training'])} constructed training molecules, labels from the declared rule")
    print()
    if action == "show":
        weights, centre = fit(data)
        show(data, weights, centre)
        show_analogues(data, analogue_rows(data, weights, centre))
        show_limits()
        print("Run 'check' to recompute these numbers from the committed dataset.")
        return

    print("ATTRIBUTION CHECKS")
    failures = check(data)
    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)
    print("All checks passed. This verifies that an explanation of a well-fitted model")
    print("pointed away from the only cause, on a set where the cause is known.")


if __name__ == "__main__":
    main()
