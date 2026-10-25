# AZ intrinsic-clearance assay-system lab

This lab compares real, measured intrinsic clearance across three named ChEMBL 37 assays for
every parent molecule with an admitted record in more than one of them. It is a descriptive read
of already-published measurements: no model is fitted, no split is drawn, and no train/test
evaluation happens anywhere in this lab.

Its scope is deliberately narrow. It covers intrinsic clearance only, one of the several
PK-exposure measures the comparison audit's taxonomy names for this topic (absorption,
distribution, clearance, bioavailability). Two other candidate sources for the remaining measures
were checked on 2026-09-12 and rejected: see [`docs/ROADMAP_V0.2.md`](../../docs/ROADMAP_V0.2.md).

## Frozen contract

The protocol version is `chembl37-az-clearance-system-v1`, in [`protocol.json`](protocol.json).
All records trace to one real, citable ChEMBL dataset deposition,
[document `CHEMBL3301361`](https://www.ebi.ac.uk/chembl/explore/document/CHEMBL3301361)
("Experimental in vitro DMPK and physicochemical data on a set of publicly disclosed compounds",
AstraZeneca, Mark Wenlock and Nicholas Tomkinson, 2016; `doc_type: DATASET`, not a proxy for a
paywalled journal article). It names three assays this lab admits by ID: human liver microsomes
(`CHEMBL3301370`), rat hepatocytes (`CHEMBL3301371`), and human hepatocytes (`CHEMBL3301372`).

The admission rule adapts, rather than copies, the one this project's `chembl_egfr` and
`cyp_assay_system` labs already use: this endpoint's real data reports an exact intrinsic-clearance
value with an *empty* `standard_relation` field, and uses `<`/`>` only for a reading outside the
assay's own quantifiable range (for example, the microsome assay's own description states
"&lt;3 to &gt;150 microL/min/mg"). A record is admitted only when its relation field is empty,
`standard_flag=1`, `potential_duplicate=0`, it carries no data validity comment, its molecule is its
own parent, its structure is RDKit-valid, and its two independently reported value fields
(`value` and `standard_value`) agree. Repeated admitted activities for one parent under one assay
are aggregated by their median.

## Setup

From the repository root:

```bash
uv sync --group dev
```

## Running

```bash
uv run python labs/az_clearance_system/run_lab.py download
uv run python labs/az_clearance_system/inspect_az_clearance_system.py show
uv run python labs/az_clearance_system/inspect_az_clearance_system.py check
uv run python labs/az_clearance_system/export_summary.py
```

`download` fetches and caches the live ChEMBL status endpoint and all three named assays' full
activity pages to `.cache/az_clearance_system/` (git-ignored). It re-validates the release fields
on every run, so a cache written under an older admission rule is re-checked rather than silently
trusted. `show` reports the admission audit for each assay, all three pairwise overlaps (each
holding one of species or matrix fixed where possible), both correlation summaries per pair, and
named divergent examples. `check` recomputes the structural invariants and exits non-zero on
failure. `export_summary.py` writes the small, committed [`summary.json`](summary.json): counts,
audits, the three pairwise correlation summaries and three named examples each way per pair, with
no raw activity rows or bulk compound lists.

## What this does not show

This protocol reads only in vitro intrinsic-clearance records from one document. It says nothing
about absorption, volume of distribution or oral bioavailability, and it makes no causal or
human-dose claim: an in vitro clearance disagreement between two assay systems is not a
prospective interaction or dosing statement. See `protocol.json`'s `excluded_by_design` for the
complete, machine-readable list.

## Results (computed 2026-09-12, live ChEMBL 37, release 2026-05-01)

| Assay | Species | Matrix | Admitted parents |
| --- | --- | --- | ---: |
| `CHEMBL3301370` | Human | Microsome | 743 |
| `CHEMBL3301371` | Rat | Hepatocyte | 592 |
| `CHEMBL3301372` | Human | Hepatocyte | 288 |

| Comparison | What varies | Overlap | Spearman rho |
| --- | --- | ---: | ---: |
| Human hepatocytes vs. rat hepatocytes | species, matrix fixed | 106 | 0.4732 |
| Human liver microsomes vs. human hepatocytes | matrix, species fixed | 96 | 0.4864 |
| Human liver microsomes vs. rat hepatocytes | both differ | 359 | 0.3868 |

All three observed Spearman coefficients are positive and below perfect rank agreement.
They describe the ordering of shared parent molecules across the assays. A correlation
coefficient is not a fraction of predictive value retained. This descriptive lab fits no
predictive model and does not estimate a loss of predictive performance or a causal effect
of species or matrix.

Only the hepatocyte-vs-hepatocyte pair reports clearance on the same physical basis, so its
paired values support literal fold-change comparisons. The microsome-involving pairs use
protein-normalized and cell-normalized measurements. Their printed log ratios are arithmetic
comparisons of the reported numbers. Both their magnitude and sign depend on the numerical
units, so they do not establish a physical fold change or which system has greater clearance.
The original example labels and numerical outputs remain in `summary.json`.

Statistical interpretation clarified on 2026-10-25. Definitions:
[SciPy Spearman rank correlation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html)
and [Pearson correlation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html).
