# Uncertainty-acquisition protocol: a new arm, not a rerun

This is the versioned, human-readable specification for
`chembl37-egfr-pool-budget-uncertainty-v1`, issued 2026-09-11. It adds one new
acquisition policy under the same real partition, budget and scoring rules the
completed `chembl37-egfr-pool-budget-v1` campaign already used. It reads no file
that campaign wrote and writes to no file it wrote; its own output lives under
`labs/pool_budget/uncertainty-results/`, and `labs/pool_budget/uncertainty-summary.json`
is the sanitized aggregate committed for the public release, in the same relation
to that directory as `real-summary.json` has to `results/`.

Status is deliberately bounded:

- The completed campaign's `results/` directory, its `real-summary.json` and its
  frozen `pool_budget_campaign.py` (which defines `build_plan`, MaxMin and the
  five random-seed policies) are unmodified and untouched by any code path here.
- This protocol's own engine ran once, under its own one-time guard, in the
  author workspace. Reproducing it in a fresh, separately authorized workspace
  is a reproduction, not a next action here.

## What it inherits unchanged

The same frozen T05 source contract (parent rule, structure, endpoint, median
aggregation and filters), the same 10/70/20 whole-group partition rule and tie
order, the same four-round budget of `floor(pool / 20)` parents per round, the
same 2,048-bit radius-2 Morgan representation, the same top-decile target
definition and recovery-AUC formula, and the same fixed
`Ridge(alpha=1.0, fit_intercept=True, solver="lsqr", tol=1e-8, max_iter=10000)`
model used for the per-checkpoint evaluation fit. None of these is redefined,
retuned, or reselected here.

It does not reuse `build_plan`, which is specific to MaxMin and the five random
seeds. This protocol derives its own library and partition from the same public
utility functions (`build_morgan_matrix`, `scaffold_group_key`, `group_partition`,
`budget_checkpoints`), and its own runner cross-checks on every invocation that
this agrees exactly with what `prepare_campaign` derives from the same dataset.

## The new policy: ensemble-variance uncertainty

Declared before running, not fitted to an observed outcome. At each of the four
rounds:

1. Take the current training rows: the initial parents, plus every parent this
   run has acquired in an earlier round.
2. Split those rows into 5 contiguous folds by stable sort order. No random
   state is used anywhere in this policy.
3. Fit one fixed Ridge model (the same hyperparameters as above) per fold, on
   the other four folds.
4. Predict every remaining pool parent with all five fold models, and rank
   candidates by the variance (`ddof=1`) of those predictions across folds. Ties
   go to the smallest global row index.
5. Acquire that round's fixed batch (`floor(original pool / 20)` parents) from
   the top of that ranking, then repeat.

Unlike MaxMin, this selector is **not label-blind**: rounds 2 through 4 use the
labels of parents this same run has already acquired. It never reads a pool
label before this run has acquired it, and it never reads an evaluation-partition
label at all before every round's picks are finalized. `AcquiredLabelLedger` in
`pool_budget_uncertainty.py` enforces this at runtime, not only in this
description.

**This is a ranking signal, not a checked calibrated interval.** Ensemble
variance across five folds is used only to order acquisition candidates. Nothing
here checks whether that variance is a calibrated predictive interval, for
example by interval-coverage on held-out labels, and the lesson states that
boundary explicitly.

## Observed result

Computed on 2026-09-11 on an Apple arm64 machine with Python 3.11.15, NumPy
2.4.6, RDKit 2025.9.6 and scikit-learn 1.9.0, against the same cached T05 source
records the completed campaign used. Recovery AUC, alongside the completed
campaign's own six policies for the same partition and budget:

| Assay        | Uncertainty | MaxMin | Best of 5 random seeds | Worst of 5 random seeds |
| ------------ | ----------: | -----: | ---------------------: | -----------------------: |
| CHEMBL5736995 (primary)    | 0.1133 | 0.0508 | 0.1016 | 0.0762 |
| CHEMBL3705421 (separate)   | 0.1635 | 0.0000 | 0.1058 | 0.0096 |

Uncertainty led every existing policy on both assays, by this one deterministic
run. This is a single retrospective replay under one fold count and one ensemble
size; it is not a sweep, and a different fold count was not tried and compared.

## Failure contract

Same discipline as the sibling real protocol: apply the inherited source
normalization and filters first; a missing, invalid or nonfinite required ID,
structure, scaffold key, fingerprint, target, prediction or metric input is a
contract failure with no repair, no imputation and no substitution.
