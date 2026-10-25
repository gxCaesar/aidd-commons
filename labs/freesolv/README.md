# FreeSolv v0.52 honest baselines

This lab runs a frozen, deliberately small baseline protocol for experimental hydration free energy.
It does not make a SOTA claim.

## Data and provenance

- Pinned data: `https://raw.githubusercontent.com/MobleyLab/FreeSolv/v0.52/database.txt`
- Release DOI: `10.5281/zenodo.1161245`
- Target: the fourth semicolon-delimited field, experimental hydration free energy in kcal/mol.
- Entity key: RDKit canonical isomeric SMILES, retaining the original `mobley_*` ID in split files.

The v0.52 release metadata does not declare licence terms. Current repository README and branch licence files are not version-bound evidence for v0.52 and are not used here to claim a historical-release licence. The dataset is downloaded to a local cache rather than included in this repository.

## Frozen protocol

- Global seed `20260904`; 80/10/10 random and Bemis-Murcko scaffold splits.
- The scaffold split is primary. Ring-free molecules use a singleton `acyclic:<canonical_smiles>` grouping key.
- Models: train mean; chirality-aware RDKit Morgan fingerprints (radius 2, 2,048 bits) plus Ridge (`alpha=1.0`) and Random Forest (500 trees, `max_features='sqrt'`, `min_samples_leaf=1`, `n_jobs=1`).
- Models fit on training molecules only. Validation supplies MAE/RMSE and the finite-sample, split-conformal 90% radii for Ridge and Random Forest.
- Test predictions are not made during `pretest`. The explicit final command is guarded so it cannot be re-run from the same output directory.

## Reproduce

From the repository root, use the project-local uv cache:

```sh
env UV_CACHE_DIR=.cache/uv uv run python labs/freesolv/run_lab.py download
env UV_CACHE_DIR=.cache/uv uv run python labs/freesolv/run_lab.py pretest
```

Inspect `labs/freesolv/results/pretest.json` and the files under `labs/freesolv/results/splits/` before the single final evaluation. After the pre-test audit, run exactly once:

```sh
env UV_CACHE_DIR=.cache/uv uv run python labs/freesolv/run_lab.py evaluate-test
```

The output directory contains `pretest.json`, CSV split membership files, and, after the one final command, `metrics.json`. `metrics.json` reports validation-calibrated test interval coverage and mean width in addition to MAE/RMSE. Marginal conformal coverage is not conditional calibration.

## Read the frozen result

`reviewed-results.json` is the aggregate-only public summary derived from the
frozen `metrics.json` artifact. It omits sample membership, fit traces,
commands, and run-state fields. `freesolv_honest_baselines.ipynb` reads that
reviewed summary and prints the scaffold-primary result before the random-split
contrast. It does not fit models, change the split files, or invoke another
test evaluation.

`environment.txt` records the exact public reference runtime observed for this
lab. It complements the pinned direct dependencies in `pyproject.toml`: `uv`
resolves those project constraints for the commands above.

## Limitations

The random split is only an easier contrast. Scaffold grouping is an RDKit representation choice, and ring-free molecules cannot share a Bemis-Murcko scaffold by this protocol. The fixed features and untuned baseline models are teaching controls, not evidence of an optimal predictive model. Results should not be generalized beyond this pinned dataset and frozen split procedure.
