# LINCS L1000 cross-cell-line perturbation-context lab

This lab compares real transcriptional signatures for the same real small-molecule compound,
measured by the LINCS L1000 assay in two different real cell lines, MCF7 and PC3, at a fixed
timepoint and dose. It is a descriptive read of already-published measurements: no model is
fitted, no split is drawn, and no train/test evaluation happens anywhere in this lab.

## Frozen contract

The protocol version is `lincs-l1000-perturbation-context-v1`, in [`protocol.json`](protocol.json).
All data traces to one real GEO series, [GSE70138](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE70138)
("L1000 Connectivity Map perturbational profiles ... LINCS PHASE II"), using only its 2017-03-06
files. This same series also ships a 2015-dated Level 2 release under simplified column labels
(for example `A375-trt_cp-5`) that do not join to the current metadata at all; that was checked
directly and rejected before this lab was built. The full 12,328-gene Level 4 (Z-score) and Level 5
(aggregated signature) releases for this series are 14 GB and 5.4 GB respectively, well outside
this project's CPU-first scale, so this protocol instead computes its own vehicle-control-relative
differential signature directly from the 978-landmark-gene Level 2 data (directly measured, never
an inferred value), a real, transparent, much smaller alternative to downloading either.

Entities are one real compound (`pert_id`) in one of the two fixed cell lines, at `pert_time=24.0h`
and `pert_dose=10.0µM`. Its final value is the median, across replicate wells, of each replicate's
own Level 2 profile minus the median profile of every vehicle-control well on that replicate's
exact same plate; an instance whose plate has no vehicle control is excluded, never paired with a
control from a different plate. A compound whose catalog entry has no RDKit-valid structure (a
literal `restricted` marker or a missing value) is excluded too.

## Setup

From the repository root:

```bash
uv sync --group dev
```

## Running

```bash
uv run python labs/l1000_perturbation_context/run_lab.py download
uv run python labs/l1000_perturbation_context/inspect_l1000_perturbation_context.py show
uv run python labs/l1000_perturbation_context/inspect_l1000_perturbation_context.py check
uv run python labs/l1000_perturbation_context/export_summary.py
```

`download` fetches and caches five official GEO files (about 640 MiB total) to
`.cache/l1000_perturbation_context/` (git-ignored). It re-validates every file's size against the
frozen protocol on every run, so a cache written under an older admission rule is re-checked rather
than silently trusted. `show` reports the admission audit for both cell lines, the real matched
cross-cell-line Spearman-rho distribution, a deterministic mismatched-compound null background, a
Mann-Whitney rank-sum test between them, and named divergent examples. `check` recomputes the
structural invariants and exits non-zero on failure. `export_summary.py` writes the small,
committed [`summary.json`](summary.json): counts, audits, the two distribution summaries, the
rank-sum test and three named examples each way; no raw expression vectors or bulk compound lists.

## What this does not show

This protocol reads only two real cell lines, one dose and one timepoint out of the several
thousand this same GEO series also contains, and only the 978 directly measured landmark genes,
never the inferred ones. It makes no claim that a cross-cell-line signature correlation predicts
any clinical or in vivo outcome. See `protocol.json`'s `excluded_by_design` for the complete,
machine-readable list.

## Results (computed 2026-09-12, GEO series GSE70138, files dated 2017-03-06)

| Cell line | Input compound-treatment rows | Admitted compounds |
| --- | ---: | ---: |
| MCF7 | 37,495 | 1,725 |
| PC3 | 34,112 | 1,724 |

1,721 compounds are shared between both cell lines. Computed once on raw Level 2 values with no
baseline correction, matched compound pairs showed a median Spearman rho of 0.79 against a
mismatched-pair null median of 0.70: both cell lines' raw profiles share enough baseline structure
that even mismatched compounds correlate strongly, a real finding this lab keeps as a worked
warning against skipping baseline correction. After vehicle-control subtraction, the real,
compound-matched median Spearman rho is 0.175 (mean 0.183, 79.5% of compounds positive), against a
deterministic mismatched-pair null median of 0.034 (mean 0.044, 60.3% positive), a difference a
two-sided Mann-Whitney U test finds significant at p = 7.9 × 10⁻⁸². About one-fifth of real
compounds show a negative cross-cell-line correlation even after baseline correction: cell-line
context measurably changes, and for a real minority of compounds reverses, the direction of a
compound's transcriptional response.
