# Real ChEMBL pool-budget campaign protocol

This is the versioned, human-readable real-campaign specification for
`chembl37-egfr-pool-budget-v1`, issued 2026-09-08. It is a retrospective
teaching protocol. Its scientific rules are unchanged; the execution status and
aggregate readout are noted separately below. No assay rows, labels,
predictions, or acquisition lists are included.

Status is deliberately bounded:

- The real execution engine is implemented.
- The authorized real campaign completed once under this protocol.
- The existing synthetic pool-budget program is separate and remains a
  simulator rather than a real-data replay.

The engine is exposed separately from `run_lab.py` through
`labs/pool_budget/run_real_campaign.py`. Its `validate-protocol` command is
data-free. The guarded `evaluate-locked --confirm-locked-evaluation` command
already executed in the author workspace. It is a reproduction command only in
a fresh, separately authorized workspace; it is not a next action in the
completed workspace.

A fresh confirmed invocation uses the inherited loader for both assays, with
the frozen T05 filters, parent-count, and scaffold checks; it has neither a
downloader nor a custom output directory. It first claims
`labs/pool_budget/results/locked-evaluation.started.json`, then writes local
`locked-details.json` and `locked-metrics.json`. A failure remains fail-closed:
the author-workspace marker is retained and the campaign is not rerun. These local
artifacts are not automatically published and do not replace `demo-summary.json`.

The sanitized aggregate is [`real-summary.json`](real-summary.json). In the
completed campaign, MaxMin recovery AUC was 0.05078125 in primary
`CHEMBL5736995` and 0 in separate `CHEMBL3705421`, below all five fixed random
policy instances in both assay replays. The separate pool had 130 parents in a
single scaffold group, so its scaffold-diversity fraction is uninformative.
This negative outcome is descriptive retrospective teaching evidence, not a
reason to retune the frozen protocol.

## Frozen source contract

Use [the frozen T05 protocol](../chembl_egfr/protocol.json) as the authority
for parent records and labels. In particular, retain its parent rule
(`molecule_chembl_id` equals `parent_molecule_chembl_id`), its RDKit canonical
isomeric-SMILES parent structure, IC50 endpoint, `pchembl_value` target, median
parent aggregation, and its listed label filters. This amendment does not
change or supplement that source query.

Run two assay replays independently:

- Primary: `CHEMBL5736995`, with the T05 frozen expected count of 902 parents.
- Separate-assay replay: `CHEMBL3705421`, with the T05 frozen expected count of
  170 parents.

Do not pool records or train across assays. Source labels are public, so the
held-out boundary is procedural. A separate ingestion/scoring component may
parse raw measurements to enforce the inherited filters, but keeps labels out
of selectors and predictors. Predictors receive only initial and acquired labels;
the evaluation scorer cannot access evaluation labels until prediction locking.
T05 development exposure exists for the
primary assay. Accordingly, this exercise is neither independent corroboration
of T05 nor label-unseen discovery; it is retrospective teaching only.
T15 exposed labels shared with T05 before T05 evaluation. The separate T05 and
T11 evaluations have since completed without retuning. No T05 retuning may use the exposure while claiming an
untouched locked evaluation.

## Frozen partition

For each assay, require unique `parent_molecule_chembl_id` values and stably
sort parents lexically by that ID to establish one global row index. Retain the
order emitted by each policy when taking acquisition prefixes. Use the existing chirality-aware
`aidd_commons.chembl_egfr.splits.scaffold_group_key`; an acyclic parent is a
canonical isomeric-SMILES singleton group. Do not replace or reimplement this
key.

Group all parents by that key, sort groups by descending size and then ascending
key, and allocate complete groups only. The real target capacities are
`0.10 * N` for `initial`, `0.70 * N` for `pool`, and `0.20 * N` for
`evaluation`. For each group, assign it to the partition with the largest
remaining real capacity (target capacity minus assigned parent count). Exact
ties go to `initial`, then `pool`, then `evaluation`.

The realized group-constrained counts must be reported as realized; do not
invent rounded counts. Refuse the assay if a partition is empty or if the
original pool has fewer than 20 parents. Never repair these failures by
breaking, moving, or relaxing scaffold groups. Every policy uses exactly the
same initial, pool, and evaluation partitions.

## Acquisition policies and budget

Let `P` be the original pool parent count and `q = floor(P / 20)`. The original
20% budget is a nominal target clarified by this floor rounding. Use four
batches, with checkpoints at `0, q, 2q, 3q, 4q` acquired parents. Report the
actual fraction `4q / P`; it must not be silently described as exactly 20%.

Each selected parent costs one attempt. This protocol makes no assertion about
synthesis, assay success, or acquisition failure.

Random uses `numpy.default_rng` with exactly seeds `0, 1, 2, 3, 4`. For each
seed, make one no-replacement permutation of the original pool and acquire its
first `4q` parents. The five seeds are fixed policy instances, not independent
assays and not samples for confidence intervals or significance testing.

MaxMin uses the frozen T05 Morgan representation: 2,048 binary bits, radius 2,
chirality, bond types, and ring membership enabled, with count simulation disabled.
Tanimoto distance is one minus the bit-set intersection divided by the union;
two empty bit vectors have distance zero. At every sequential pick,
maximize a candidate's minimum Tanimoto distance to all initial parents and all
previous acquisitions, including earlier picks in the same batch. Exact ties
use the smallest sorted global parent index. The selector is label-blind.

Selections are always without replacement. Do not add, remove, rank, or shop
seeds after observing an outcome.

## Targets, recovery, and diversity

Define targets in the original pool only: exclude initial and evaluation
parents. Select exactly `ceil(P / 10)` target parents by descending pChEMBL;
resolve equal pChEMBL values with the stable lexical parent-ID order.

At each checkpoint, recovery is acquired target parents divided by the fixed
target count. Report recovery AUC as the trapezoidal integral over the declared
acquired-count checkpoints divided by the final acquired count (`4q`). Report
scaffold diversity as unique acquired scaffold groups divided by the original
pool scaffold-group count.

## Fixed per-round prediction assessment

For each policy instance, use the same frozen T05 Morgan representation,
converted to float64 without scaling. Fit Ridge with `alpha=1.0`,
`fit_intercept=True`, `solver="lsqr"`, `tol=1e-8`, and `max_iter=10000`. There
is no tuning, scaling, cross-assay fitting, or evaluation-partition fitting.

Use Python 3.11 and the repository's exact NumPy, RDKit, and scikit-learn pins in
`pyproject.toml`. Record runtime versions with future results. At each fit, order
training rows by the stable global parent index, and keep evaluation predictions
in that same stable index order.

At checkpoint zero, fit on initial parents only and lock the full evaluation
prediction vector. At later checkpoints, fit on initial plus all acquired
parents through that checkpoint only, then lock the evaluation prediction
vector. Finalize every label-blind acquisition order and every prediction vector
before the isolated scorer accesses any evaluation label. Raw-record parsing
for the inherited source filters is separate from this scoring boundary. Only then score per-checkpoint
MAE on the fixed evaluation partition. Evaluation outcomes may not change any
policy, seed, split, feature setting, alpha, batch, or future prediction.

The `alpha=1.0` setting was already informed by T05 development and is retained
as a declared selection snapshot. It is not independently selected or validated
by T15. Do not report confidence intervals, p values, seed-as-sample inference,
or any prospective biological claim.

The real-engine tests use artificial fixtures to exercise this fixed Ridge path.
They do not change the synthetic simulator's no-predictive-model scope.

## Failure contract

Apply the inherited source normalization and filters first. Any remaining
missing, invalid, or nonfinite required ID, structure, scaffold key,
fingerprint, target, prediction, or metric input is a contract failure. Do not
add exclusions, impute targets, repair invalid values, or substitute values.
No additional author-workspace campaign result may be produced by deleting the
marker, rerunning the command, or changing this declared specification.
