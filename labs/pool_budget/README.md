# Pool-budget teaching simulator and real-campaign boundary

Run from the repository root:

```bash
uv sync --group dev
uv run python labs/pool_budget/run_lab.py
uv run pytest labs/tests/test_pool_budget.py -q
```

The CLI above remains synthetic-only: it prints deterministic aggregate JSON to
stdout, needs no download, real-data mode, or GPU, and fits no predictive model.
`demo-summary.json` is its expected output with the pinned NumPy and RDKit
versions in `pyproject.toml`.

The 60 authored graphs combine alkyl chains of lengths 1–10 with six suffixes:
O, N, F, C(=O)O, c1ccccc1, and C1CCCCC1. Scores are deliberately artificial:
`((row_index * 17) % 61) / 10`. They are not measurements or medicinal predictions.
Whole scaffold groups are allocated toward 10/70/20% initial/pool/reserve
targets. The resulting counts are 6/42/12. Four batches of two acquire eight
pool molecules. MaxMin uses no labels; only the scorer sees artificial scores.

The top-decile target contains exactly five pool entries. Recovery is scored
at 0/2/4/6/8 acquisitions; normalized trapezoidal AUC is 0.100 for MaxMin and
0.125, 0.250, 0.000, 0.000, 0.100 for random seeds 0–4. These are instructional
outputs, not an empirical comparison of medicinal performance. The reserve
is not scored and no surrogate is fitted.

The synthetic protocol is separate from the completed retrospective ChEMBL
campaign. No assay data or compound-level measurement files are distributed by
this simulator.

The separate real engine is specified in `real-protocol.json` and
[REAL_PROTOCOL.md](REAL_PROTOCOL.md). Its tests use artificial fixtures,
including the fixed Morgan Ridge path; this does not turn
the synthetic `run_lab.py` simulator into a predictive-model exercise.

The data-free contract check remains:

```bash
uv run python labs/pool_budget/run_real_campaign.py validate-protocol
```

## Completed retrospective campaign

The real campaign completed once under `chembl37-egfr-pool-budget-v1`. Its
sanitized public aggregate is
[`real-summary.json`](real-summary.json), separate from the unchanged synthetic
[`demo-summary.json`](demo-summary.json). No result below is a prospective
discovery, synthesis, assay-success claim, or independent corroboration of T05.

| Assay                    | Initial / pool / evaluation parents | Initial / pool / evaluation groups | q / final acquired | Actual final pool fraction (rounded) |
| ------------------------ | ----------------------------------- | ---------------------------------- | ------------------ | ------------------------------------ |
| Primary `CHEMBL5736995`  | 90 / 631 / 181                      | 62 / 97 / 79                       | 31 / 124           | 19.65%                               |
| Separate `CHEMBL3705421` | 12 / 130 / 28                       | 10 / 1 / 12                        | 6 / 24             | 18.46%                               |

MaxMin recovery AUC was 0.05078125 for the primary assay and 0 for the
separate assay. Both are below every one of the five fixed random policy
instances in their respective assays. The separate pool contains 130 parents in
one scaffold group, so its scaffold-diversity fraction is uninformative. This
negative result is preserved rather than retuned away.

T15 exposed labels shared with T05 before T05 evaluation. The separate T05 and
T11 evaluations have since completed without retuning. No T05 retuning may use
this exposure while claiming an untouched
locked evaluation, and T15 is not independent T05 corroboration.

The guarded command has already executed in the author workspace. It is shown
only for reproduction in a fresh, separately authorized workspace, not as a
next action here:

```bash
uv run python labs/pool_budget/run_real_campaign.py evaluate-locked --confirm-locked-evaluation
```

The author-workspace marker remains in place; do not delete it or repeat the campaign.
In a fresh authorized workspace, the command first creates
`labs/pool_budget/results/locked-evaluation.started.json`, then writes local
`locked-details.json` and `locked-metrics.json`. Failure is fail-closed: the
marker is not removed for retry. Those local artifacts are not automatically
published and never replace `demo-summary.json`.

To export already completed aggregate results without rerunning the campaign:

```bash
uv run python labs/pool_budget/export_summary.py
```

This command reads existing `locked-metrics.json` only. The public summary
retains every policy and checkpoint but excludes compound identities, labels,
predictions, acquisition lists, and local execution records. The public release
already includes that summary; readers do not need local execution artifacts
to inspect its aggregate results.

Software: Apache-2.0. Original lesson content: CC BY 4.0. Third-party dependency
terms remain with their respective projects.
