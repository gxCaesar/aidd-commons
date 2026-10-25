"""Small teaching functions embedded verbatim into the standalone notebooks.

Importing this module never downloads data, fits models, or writes outputs.
"""

import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from inspect_data import inspect
from rdkit import Chem
from rdkit.Chem import Descriptors, rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def load_frame(path):
    """Validate without filtering, then add label-free structure and scaffold keys."""
    intake = inspect(Path(path))
    if intake["repeated_structure_groups"]:
        raise ValueError("Repeated structure: resolve the entity contract before modelling")
    frame = pd.read_csv(path)
    molecules = [Chem.MolFromSmiles(smiles) for smiles in frame["smiles"]]
    frame["canonical"] = [Chem.MolToSmiles(mol, isomericSmiles=True) for mol in molecules]
    frame["scaffold"] = [
        MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False) for mol in molecules
    ]
    return frame


def validate_split(frame, splits):
    """Check complete assignment and compound/structure/scaffold separation."""
    if set(splits) != {"train", "validation", "test"}:
        raise ValueError("Expected train, validation, test")
    if any(len(indices) == 0 for indices in splits.values()):
        raise ValueError("Every split must contain rows; this grouping is not scorable")
    assigned = np.concatenate(list(splits.values()))
    if sorted(assigned.tolist()) != list(range(len(frame))):
        raise ValueError("Rows must appear exactly once across splits")
    for key in ["CMPD_CHEMBLID", "canonical", "scaffold"]:
        seen = set()
        for indices in splits.values():
            keys = set(frame.iloc[indices][key])
            if seen & keys:
                raise ValueError(f"Cross-split {key} overlap")
            seen.update(keys)


def scaffold_split(frame):
    """DeepChem 2.8.0 group-size/first-index ordering, requested 80/10/10.

    Empty scaffolds form one group. No target value participates in assignment.
    The algorithm follows the cited splitter; RDKit version still affects keys.
    """
    groups = defaultdict(list)
    for index, key in enumerate(frame["scaffold"]):
        groups[key].append(index)
    ordered = sorted(groups.values(), key=lambda group: (len(group), group[0]), reverse=True)
    splits = {"train": [], "validation": [], "test": []}
    for group in ordered:
        if len(splits["train"]) + len(group) <= 0.8 * len(frame):
            splits["train"].extend(group)
        elif len(splits["train"]) + len(splits["validation"]) + len(group) <= 0.9 * len(frame):
            splits["validation"].extend(group)
        else:
            splits["test"].extend(group)
    splits = {name: np.asarray(indices, dtype=int) for name, indices in splits.items()}
    validate_split(frame, splits)
    return splits


def molecular_features(smiles):
    """Eight interpretable descriptors and nonchiral radius-2 Morgan bit vectors."""
    molecules = [Chem.MolFromSmiles(value) for value in smiles]
    if not molecules or any(mol is None or mol.GetNumAtoms() == 0 for mol in molecules):
        raise ValueError("Features require valid nonempty molecules")
    names = [
        "MolWt",
        "MolLogP",
        "TPSA",
        "NumHDonors",
        "NumHAcceptors",
        "RingCount",
        "NumRotatableBonds",
        "FractionCSP3",
    ]
    descriptors = np.asarray(
        [[getattr(Descriptors, name)(mol) for name in names] for mol in molecules], dtype=float
    )
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=2,
        fpSize=2048,
        includeChirality=False,
    )
    fingerprints = [generator.GetFingerprint(mol) for mol in molecules]
    bits = np.asarray([np.asarray(fp) for fp in fingerprints], dtype=float)
    if not np.isfinite(descriptors).all() or not np.isfinite(bits).all():
        raise ValueError("Non-finite feature: no silent imputation or exclusion")
    return descriptors, bits, fingerprints


def score(y, prediction):
    """RMSE and MAE in logD units; reject accidental array broadcasting."""
    y, prediction = np.asarray(y, dtype=float), np.asarray(prediction, dtype=float)
    if y.ndim != 1 or prediction.shape != y.shape or not len(y):
        raise ValueError("Expected equally sized, nonempty one-dimensional arrays")
    if not np.isfinite(y).all() or not np.isfinite(prediction).all():
        raise ValueError("Labels and predictions must be finite")
    error = prediction - y
    return {"rmse": float(np.sqrt(np.mean(error**2))), "mae": float(np.mean(np.abs(error)))}


def fit_candidates(x_train, y_train, x_validation, y_validation, center):
    """Train-only scaling/fitting; validation-only alpha choice. No test argument."""
    candidates, rows = [], []
    for alpha in [0.1, 1.0, 10.0, 100.0]:
        model = make_pipeline(
            StandardScaler(with_mean=center),
            Ridge(alpha=alpha, solver="lsqr", tol=1e-6, max_iter=10000, fit_intercept=True),
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            model.fit(x_train, y_train)
        if np.any(np.asarray(model.named_steps["ridge"].n_iter_) >= 10000):
            raise RuntimeError("Ridge reached max_iter; report convergence failure")
        metrics = score(y_validation, model.predict(x_validation))
        rows.append({"alpha": alpha, "validation_rmse": metrics["rmse"]})
        candidates.append(model)
    selected = min(range(len(rows)), key=lambda i: (rows[i]["validation_rmse"], -rows[i]["alpha"]))
    return candidates[selected], pd.DataFrame(rows)


def paired_interval(y, left, right, groups):
    """Fixed-model RMSE(left)-RMSE(right), paired whole-scaffold bootstrap.

    Uniformly sample G groups G times with replacement, retain all their rows,
    and recompute molecule-weighted RMSE differences. Not a prediction interval
    or a claim of independent assay replication; no multiplicity adjustment.
    """
    difference = score(y, left)["rmse"] - score(y, right)["rmse"]
    groups = np.asarray(groups)
    if groups.ndim != 1 or len(groups) != len(y) or pd.isna(groups).any():
        raise ValueError("One nonmissing scaffold key is required per prediction")
    keys, inverse = np.unique(groups, return_inverse=True)
    result = {
        "difference": difference,
        "ci95": None,
        "groups": len(keys),
        "rows": len(y),
        "resamples": 0,
    }
    if len(keys) < 2:
        return result
    counts = np.bincount(inverse)
    left_sse = np.bincount(inverse, weights=(np.asarray(left) - np.asarray(y)) ** 2)
    right_sse = np.bincount(inverse, weights=(np.asarray(right) - np.asarray(y)) ** 2)
    rng = np.random.default_rng(20260909)
    differences = []
    for _ in range(2000):
        draw = rng.integers(0, len(keys), size=len(keys))
        n = counts[draw].sum()
        differences.append(np.sqrt(left_sse[draw].sum() / n) - np.sqrt(right_sse[draw].sum() / n))
    result["ci95"] = np.percentile(differences, [2.5, 97.5]).tolist()
    result["resamples"] = 2000
    return result
