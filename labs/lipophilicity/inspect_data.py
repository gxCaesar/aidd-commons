"""Inspect a local MoleculeNet lipophilicity CSV; never filter, split, fit, or write."""

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from rdkit import Chem, rdBase
from rdkit.Chem.Scaffolds import MurckoScaffold


def inspect(source: Path) -> dict:
    ids = set()
    structures = defaultdict(list)
    scaffolds = Counter()
    targets = []
    multicomponent_rows = 0
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["CMPD_CHEMBLID", "exp", "smiles"]:
            raise ValueError("Expected columns CMPD_CHEMBLID,exp,smiles in that order")
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None or not value.strip() for value in row.values()):
                raise ValueError(f"Line {line}: missing value or unexpected column")
            compound_id = row["CMPD_CHEMBLID"].strip()
            if compound_id in ids:
                raise ValueError(f"Line {line}: repeated compound ID {compound_id}")
            target = float(row["exp"])
            if not math.isfinite(target):
                raise ValueError(f"Line {line}: target must be finite")
            molecule = Chem.MolFromSmiles(row["smiles"])
            if molecule is None or molecule.GetNumAtoms() == 0:
                raise ValueError(f"Line {line}: invalid or empty molecule")
            structure = Chem.MolToSmiles(molecule, isomericSmiles=True)
            scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=molecule, includeChirality=False)
            ids.add(compound_id)
            targets.append(target)
            structures[structure].append(target)
            scaffolds[scaffold] += 1
            multicomponent_rows += len(Chem.GetMolFrags(molecule)) > 1
    if not targets:
        raise ValueError("Input contains no data rows")
    return {
        "rows": len(targets),
        "unique_ids": len(ids),
        "unique_canonical_isomeric_smiles": len(structures),
        "repeated_structure_groups": sum(len(values) > 1 for values in structures.values()),
        "repeated_structure_extra_rows": len(targets) - len(structures),
        "structure_groups_with_different_labels": sum(
            len(set(values)) > 1 for values in structures.values()
        ),
        "nonempty_scaffold_groups": sum(bool(scaffold) for scaffold in scaffolds),
        "largest_nonempty_scaffold_rows": max(
            (count for scaffold, count in scaffolds.items() if scaffold), default=0
        ),
        "acyclic_rows": scaffolds[""],
        "multicomponent_rows": multicomponent_rows,
        "target_range": [min(targets), max(targets)],
        "rdkit_version": rdBase.rdkitVersion,
        "scope": "Read-only intake; no rows excluded, no split assigned, no model fitted",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="Locally downloaded Lipophilicity.csv")
    args = parser.parse_args()
    try:
        report = inspect(args.csv)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"Data intake failed: {error}\n")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
